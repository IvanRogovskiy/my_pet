import argparse
import contextlib
import io
import json
import os
import sqlite3
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ASSETS = Path(__file__).resolve().parents[1] / "assets"
sys.path.insert(0, str(ASSETS / "labs"))
import lab
import infrastructure
from catalog import CASES, files


class Labs(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="of-lab-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.options = argparse.Namespace(image=None, postgres_image=None, context=None,
                                          terraform="terraform", ansible="ansible-playbook", helm="helm")

    def create(self, case):
        path = self.base / case
        lab.prepare(path, case)
        return lab.load(path)

    def result(self, root, state):
        with contextlib.redirect_stdout(io.StringIO()):
            return lab.check(root, state, self.options)

    def test_all_cases_prepare_without_runtime_and_reset_preserves_data(self):
        for case in CASES:
            with self.subTest(case=case):
                root, state = self.create(case)
                (root / "data/keep.txt").write_text("original data")
                (root / "evidence/keep.json").write_text('{"old":true}')
                first = next(iter(files(case)))
                (root / "work" / first).write_text("student edit")
                (root / "work/notes.txt").write_text("student notes")
                lab.restore(root, state)
                self.assertEqual((root / "data/keep.txt").read_text(), "original data")
                self.assertEqual((root / "evidence/keep.json").read_text(), '{"old":true}')
                self.assertEqual((root / "work/notes.txt").read_text(), "student notes")
                self.assertEqual((root / "work" / first).read_text(), files(case)[first])

    def test_prepare_never_adopts_existing_directory(self):
        path = self.base / "existing"
        path.mkdir()
        with self.assertRaises(ValueError):
            lab.prepare(path, "B29")

    def test_prepare_refuses_protected_directory_before_writing(self):
        path = self.base / ".git" / "lab"
        with self.assertRaises(ValueError):
            lab.prepare(path, "B29")
        self.assertFalse(path.exists())

    def test_concurrent_cli_reset_is_refused(self):
        root, _ = self.create("B29")
        file = root / "work/replay.py"
        file.write_text("saved student work")
        with lab.exclusive(root):
            result = subprocess.run([sys.executable, str(ASSETS / "labs/lab.py"), "reset", str(root)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("another check/reset", result.stderr)
        self.assertEqual(file.read_text(), "saved student work")

    def test_symlink_cannot_redirect_reset(self):
        root, state = self.create("B29")
        outside = self.base / "outside.py"
        outside.write_text("keep")
        file = root / "work/replay.py"
        file.unlink()
        file.symlink_to(outside)
        with self.assertRaises(ValueError):
            lab.restore(root, state)
        self.assertEqual(outside.read_text(), "keep")

    def test_directory_symlink_cannot_redirect_reset(self):
        root, state = self.create("B29")
        (root / "work").rename(root / "old-work")
        outside = self.base / "outside"
        outside.mkdir()
        (root / "work").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            lab.load(root)
        self.assertEqual(list(outside.iterdir()), [])

    def test_hardlink_cannot_redirect_reset(self):
        root, state = self.create("B29")
        outside = self.base / "outside.py"
        outside.write_text("keep")
        target = root / "work/replay.py"
        target.unlink()
        os.link(outside, target)
        with self.assertRaises(ValueError):
            lab.restore(root, state)
        self.assertEqual(outside.read_text(), "keep")

    def test_moved_workspace_rejected(self):
        root, _ = self.create("B29")
        moved = self.base / "moved"
        root.rename(moved)
        with self.assertRaises(ValueError):
            lab.load(moved)

    def test_projection_bad_fixed_reset(self):
        root, state = self.create("B29")
        self.assertEqual(self.result(root, state), 1)
        lab.restore(root, state, True)
        self.assertEqual(self.result(root, state), 0)
        lab.restore(root, state)
        self.assertEqual(self.result(root, state), 1)
        reports = list((root / "evidence").glob("*.json"))
        self.assertEqual(len(reports), 3)
        for report in reports:
            self.assertIn("replay.py", json.loads(report.read_text())["source_sha256"])

    def test_dag_bad_fixed_and_valid_stage_based_alternative(self):
        root, state = self.create("C12")
        self.assertEqual(self.result(root, state), 1)
        lab.restore(root, state, True)
        self.assertEqual(self.result(root, state), 0)
        graph = json.loads((root / "work/pipeline.json").read_text())
        del graph["marker"]["needs"]
        (root / "work/pipeline.json").write_text(json.dumps(graph))
        self.assertEqual(self.result(root, state), 0)

    def test_optional_gate_not_accepted(self):
        root, state = self.create("C12")
        lab.restore(root, state, True)
        graph = json.loads((root / "work/pipeline.json").read_text())
        graph["gate"]["allow_failure"] = True
        (root / "work/pipeline.json").write_text(json.dumps(graph))
        self.assertEqual(self.result(root, state), 1)

    def test_unsupported_ci_rules_are_not_claimed_verified(self):
        root, state = self.create("C12")
        lab.restore(root, state, True)
        graph = json.loads((root / "work/pipeline.json").read_text())
        graph["gate"]["rules"] = [{"when": "never"}]
        (root / "work/pipeline.json").write_text(json.dumps(graph))
        self.assertEqual(self.result(root, state), 2)

    def test_loopback_bad_fixed_and_cleanup(self):
        root, state = self.create("L02b")
        self.assertEqual(self.result(root, state), 1)
        lab.restore(root, state, True)
        self.assertEqual(self.result(root, state), 0)
        report = json.loads(sorted((root / "evidence").glob("*.json"))[-1].read_text())
        self.assertIsNone(lab.http(report["detail"]["target_port"]))
        self.assertIsNone(lab.http(report["detail"]["occupied_port"]))

    @unittest.skipUnless(sys.platform == "linux" and os.geteuid() != 0, "requires unprivileged Linux UID")
    def test_permissions_can_be_rechecked_after_read_only_fixture(self):
        root, state = self.create("L02c")
        self.assertEqual(self.result(root, state), 1)
        lab.restore(root, state, True)
        self.assertEqual(self.result(root, state), 0)
        lab.restore(root, state)
        self.assertEqual(self.result(root, state), 1)

    def test_missing_runtime_is_exit_two_with_evidence(self):
        root, state = self.create("T24")
        self.options.terraform = str(self.base / "absent-terraform")
        self.assertEqual(self.result(root, state), 2)
        report = json.loads(next((root / "evidence").glob("*.json")).read_text())
        self.assertEqual(report["status"], "unverified")

    def test_postgres_fixture_does_not_repair_deleted_marker(self):
        root, state = self.create("K27")
        cluster = Mock()
        cluster.call.return_value = {"exit": 0}
        infrastructure.postgres_fixture(cluster, root)
        cluster.call.reset_mock()
        # The database may have lost its row; a second check must only observe it.
        infrastructure.postgres_fixture(cluster, root)
        cluster.call.assert_not_called()
        lab.restore(root, state)
        infrastructure.postgres_fixture(cluster, root)
        cluster.call.assert_not_called()

    def test_failed_fixture_seed_is_not_recorded(self):
        root, _ = self.create("K27")
        cluster = Mock()
        cluster.call.return_value = {"exit": 1}
        with self.assertRaises(lab.Unavailable):
            infrastructure.postgres_fixture(cluster, root)
        self.assertFalse((root / "data/postgres-seeded.json").exists())

    def test_service_convergence_retried_and_persistent_failure_retained(self):
        cluster = Mock()
        cluster.call.side_effect = [{"exit": 2}, {"exit": 0}]
        with patch.object(infrastructure.time, "sleep"):
            result = infrastructure.wait_cluster_command(cluster, ["probe"])
        self.assertEqual(result["exit"], 0)
        self.assertEqual(cluster.call.call_count, 2)
        cluster.call.side_effect = None
        cluster.call.return_value = {"exit": 2}
        self.assertEqual(infrastructure.wait_cluster_command(cluster, ["probe"], seconds=0)["exit"], 2)

    def test_release_fixture_writes_only_on_post(self):
        root, state = self.create("R26")
        with sqlite3.connect(root / "data/orders.sqlite") as db:
            db.execute("CREATE TABLE orders(id INTEGER PRIMARY KEY,amount INTEGER)")
            db.execute("INSERT INTO orders VALUES(1,250)")
        number = lab.port()
        env = {"COURSE_DATA_DIR":str(root / "data"),"COURSE_BIND":"127.0.0.1","COURSE_PORT":str(number)}
        with patch.dict(os.environ,env), lab.server(root,number,"app.py"):
            first = lab.wait_http(number)
            self.assertEqual(first["rows"], [[1,250]])
            self.assertIsNone(lab.http(number,"/write"))
            self.assertEqual(lab.http(number)["rows"], [[1,250]])
            self.assertEqual(lab.http(number,"/orders",method="POST")["rows"], [[1,250],[2,100]])

    def test_disk_preflight_precedes_docker(self):
        root, state = self.create("D10")
        with patch.object(infrastructure.shutil, "disk_usage", return_value=argparse.Namespace(free=100)), patch.object(infrastructure, "command") as call:
            with self.assertRaises(lab.Unavailable):
                infrastructure.run_infrastructure(root, state, self.options)
            call.assert_not_called()

    def test_container_cleanup_refuses_wrong_owner(self):
        with patch.object(infrastructure, "command", return_value={"exit": 0,"stdout":"another-owner","stderr":""}), patch.object(infrastructure, "must") as mutation:
            with self.assertRaises(lab.Unavailable):
                infrastructure.owned_remove_container("oflab-example", "expected")
            mutation.assert_not_called()

    def test_remote_cluster_refused_before_creation(self):
        root, state = self.create("H28")
        self.options.context = "kind-misnamed-remote"
        with patch.object(infrastructure, "disk_preflight"), patch.object(infrastructure, "must", return_value={"stdout":"https://remote.example:6443"}) as calls:
            with self.assertRaises(lab.Unavailable):
                infrastructure.Cluster(root, state, self.options)
            self.assertEqual(calls.call_count, 1)

    def test_cli_infrastructure_unavailable_has_json_and_exit_two(self):
        root, _ = self.create("D10")
        result = subprocess.run([sys.executable, str(ASSETS / "labs/lab.py"), "check", str(root)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "unverified")


if __name__ == '__main__':
    unittest.main()
