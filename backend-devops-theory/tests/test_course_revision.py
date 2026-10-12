"""Regressions from observed course failures, not a claim of fresh hosted/cloud acceptance."""
import argparse
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import ssl
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "assets/labs"))
sys.path.insert(0, str(ROOT / "assets/examples"))
import lab
from catalog import CASES, files
from numeric_contract import quantity_from_json

spec = importlib.util.spec_from_file_location("tls_fixture", ROOT / "assets/network-lab/fixture.py")
tls = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tls)


class CourseRevision(unittest.TestCase):
    def test_raw_integer_forms_agree_without_coercing_other_types(self):
        for raw in ["1", "1.0", "1e0", "10e-1"]:
            self.assertEqual(quantity_from_json(raw), 1)
        for raw in ["true", '"1"', "1.5", "-1", "0", "null", "[]", "{}", "NaN", "Infinity"]:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                quantity_from_json(raw)

    def test_precision_is_checked_before_float_rounding_and_int_expansion(self):
        self.assertEqual(json.loads("1.0000000000000001"), 1.0)  # the misleading oracle
        for raw in ["1.0000000000000001", "1e-10000", "1e10000", "1000.0000000000000001"]:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                quantity_from_json(raw)
        self.assertEqual(quantity_from_json("1000.0"), 1000)
        self.assertEqual(quantity_from_json("2000", maximum=2000), 2000)

    def test_catalogue_matches_every_named_boundary(self):
        rows = re.findall(r"^\| (\d{2}/\d+) \| (.*)$", (ROOT / "references/part-boundaries.md").read_text(), re.M)
        checked = set()
        for part, body in rows:
            for case, (topic, _, _) in CASES.items():
                if re.search(r"\b" + re.escape(case) + r"\b", body):
                    self.assertEqual(topic, part, case)
                    checked.add(case)
        self.assertIn("T24", checked)

    def test_l02a_preserves_absolute_executable_and_rejects_unknown_before_unit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = lab.prepare(Path(directory) / "lab", "L02a")
            self.assertEqual(lab.interpreter(root, sys.executable), sys.executable)
            self.assertEqual(lab.interpreter(root, "current"), sys.executable)
            self.assertEqual(lab.interpreter(root, "pythno"), str(root / "work/pythno"))
            (root / "work/config.json").write_text('{"python":"python-misspelled"}')
            with patch.object(lab, "command") as call, patch.object(lab, "must") as must:
                with self.assertRaisesRegex(ValueError, "expected current"):
                    lab.systemd(root, lab.load(root)[1], argparse.Namespace())
                call.assert_not_called()
                must.assert_not_called()
            not_executable = root / "not-python"
            not_executable.write_text("x")
            not_executable.chmod(0o600)
            with self.assertRaises(ValueError):
                lab.interpreter(root, str(not_executable))

    def test_existing_l02a_without_new_help_file_still_loads_and_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = lab.prepare(Path(directory) / "lab", "L02a")
            (root / "work/CONFIG.md").unlink()
            root, state = lab.load(root)
            with patch.object(lab, "execute", return_value=(True, {"scope": "format-only"})), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(lab.check(root, state, argparse.Namespace()), 0)

    def test_t24_assignment_is_issued_in_first_part(self):
        with tempfile.TemporaryDirectory() as directory:
            root = lab.prepare(Path(directory) / "lab", "T24")
            self.assertTrue((root / "ASSIGNMENT.md").read_text().startswith("# T24 — 24/1\n"))

    def test_zero_changed_cannot_hide_restart_or_wrong_config(self):
        negative = json.loads(files("A25", masked_restart=True)["playbook.json"])
        self.assertIs(negative[0]["tasks"][-1]["changed_when"], False)
        self.assertNotIn("changed_when", json.loads(files("A25")["playbook.json"])[0]["tasks"][-1])
        runs = [{"exit": 0, "stdout": f"localhost: changed={n}"} for n in [1, 0, 1, 0]]
        snapshots = [{"pid": p, "config_sha": h} for p, h in [(10, "a"), (10, "a"), (20, "b"), (20, "b")]]
        self.assertTrue(lab.ansible_idempotent(runs, snapshots))
        restarted = [dict(x) for x in snapshots]
        restarted[1]["pid"] = 11
        self.assertFalse(lab.ansible_idempotent(runs, restarted))
        wrong_config = [dict(x) for x in snapshots]
        wrong_config[2]["config_sha"] = "a"
        self.assertFalse(lab.ansible_idempotent(runs, wrong_config))
        self.assertFalse(lab.ansible_idempotent(runs[:2], snapshots[:2]))


@unittest.skipUnless(importlib.util.find_spec("cryptography"), "optional TLS fixture requires cryptography")
class TLSFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="of-tls-test-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "endpoint"
        self.passport = tls.prepare(self.path)

    def start(self):
        errors = []
        def run():
            try:
                tls.serve(self.path)
            except Exception as exc:
                errors.append(exc)
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        def cleanup():
            # Even a failed early assertion must wait for its own startup and stop it.
            for _ in range(100):
                if not thread.is_alive():
                    break
                try:
                    tls.stop(self.path)
                    break
                except (OSError, ValueError):
                    time.sleep(0.02)
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
        self.addCleanup(cleanup)
        for _ in range(100):
            if errors:
                raise errors[0]
            try:
                tls.live(self.path)
                return thread
            except (OSError, ValueError):
                time.sleep(0.02)
        self.fail("owned fixture did not become ready")

    def test_real_tls_five_outcomes_and_authenticated_stop(self):
        thread = self.start()
        report = tls.check(self.path)
        self.assertTrue(report["passed"], report)
        self.assertEqual(len(report["checks"]), 5)
        ready = json.loads((self.path / "ready.json").read_text())
        url = f'http://127.0.0.1:{ready["ports"]["control"]}/stop'
        self.assertEqual(tls.request(url, headers={"X-Fixture-Control": "wrong"}, data=b"")[0], 403)
        self.assertTrue(thread.is_alive())
        self.assertTrue(tls.stop(self.path)["stopped"])
        thread.join(timeout=3)
        self.assertFalse(thread.is_alive())
        with self.assertRaises(OSError):
            tls.request(url)
        self.assertFalse((self.path / "ready.json").exists())

    def test_new_generation_rejects_stale_ready_and_preserves_old_directory(self):
        (self.path / "ready.json").write_text('{"stale":true}')
        # Deterministic reproduction before serve gets any CPU: no timing-dependent success.
        with self.assertRaisesRegex(ValueError, "stale or malformed"):
            tls.live(self.path)
        self.start()
        ready = (self.path / "ready.json").read_text()
        fake = json.loads(ready)
        fake["instance"] = "another-instance"
        (self.path / "ready.json").write_text(json.dumps(fake))
        try:
            with self.assertRaisesRegex(ValueError, "stale"):
                tls.live(self.path)
        finally:
            (self.path / "ready.json").write_text(ready)
        with self.assertRaises(ValueError):
            tls.prepare(self.path)
        second = tls.prepare(Path(self.temp.name) / "second")
        self.assertNotEqual(second["ca_sha256"], self.passport["ca_sha256"])
        self.assertEqual(os.stat(self.path).st_mode & 0o777, 0o700)
        for name in ["valid.key", "expired.key", "control.key"]:
            self.assertEqual(os.stat(self.path / name).st_mode & 0o777, 0o600)

    def test_expired_generation_is_not_served_after_pause(self):
        state = json.loads((self.path / "owner.json").read_text())
        state["certificates"]["valid"]["not_after"] = "2000-01-01T00:00:00+00:00"
        (self.path / "owner.json").write_text(json.dumps(state))
        with self.assertRaisesRegex(ValueError, "expired"):
            tls.serve(self.path)
        self.assertFalse((self.path / "ready.json").exists())


if __name__ == "__main__":
    unittest.main()
