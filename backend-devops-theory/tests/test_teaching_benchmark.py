"""Synthetic records test integrity and regressions, never teacher quality."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "assets/teaching-benchmark"))
import teaching
from teaching_cases import CASES, VERSION


def synthetic_record(path):
    manifest, case = teaching.bundle(path)
    identity = manifest["case_id"]
    result = {"benchmark_version": VERSION, "case_id": identity,
              "input_sha256": teaching.digest(manifest), "prompt": case["prompt"],
              "response": "Synthetic validator fixture; not a teacher response.",
              "execution": "Synthetic fixture, no teacher session run.",
              "session": {"id": "synthetic-" + identity, "name": "Unit test", "date": "2026-10-14",
                          "kind": "self_review", "fresh_context": True, "history_messages": 0}}
    if case["suite"] == "resume":
        result["recovered"] = dict(deepcopy(case["expected"]), next_step="Synthetic next step")
        result["snapshot"] = {name: case["files"]["learning/" + name] for name in ("PROGRESS.md", "NOTES.md")}
    return result


class TeachingBenchmark(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def export(self, identity="RS03"):
        path = self.root / identity
        teaching.export(path, identity)
        return path, synthetic_record(path)

    def test_exports_all_scenarios_without_author_rubrics_or_answers(self):
        self.assertEqual(len(CASES), 12)
        for identity, case in CASES.items():
            path, record = self.export(identity)
            manifest, _ = teaching.bundle(path)
            self.assertEqual(set(manifest["sha256"]), set(case["files"]) | {"TASK.md", "prompt.txt"} |
                             ({"TEACHER.md"} if case["suite"] != "transfer" else set()))
            for statement in case["rubric"]:
                self.assertNotIn(statement, "\n".join(p.read_text() for p in path.rglob("*") if p.is_file()))
            self.assertTrue(teaching.check(path, record)["semantic_assessment_required"])
            if case["suite"] == "transfer":
                self.assertEqual(manifest["source_sha256"], {})

    def test_export_never_overwrites_existing_or_symlink_destination(self):
        path, _ = self.export()
        with self.assertRaises(ValueError):
            teaching.export(path, "RS01")
        link = self.root / "link"
        link.symlink_to(self.root / "missing")
        with self.assertRaises(ValueError):
            teaching.export(link, "RS01")

    def test_changed_extra_missing_and_symlink_inputs_rejected(self):
        for mutation in ("changed", "extra", "missing", "symlink"):
            with self.subTest(mutation=mutation):
                path = self.root / mutation
                teaching.export(path, "RS01")
                record = synthetic_record(path)
                target = path / "assignment.md"
                if mutation == "changed":
                    target.write_text("altered contract")
                elif mutation == "extra":
                    (path / "oracle.txt").write_text("unexpected")
                else:
                    target.unlink()
                    if mutation == "symlink":
                        target.symlink_to(self.root / "external")
                with self.assertRaises((ValueError, OSError)):
                    teaching.check(path, record)

    def test_rehashed_changed_scenario_cannot_claim_original_version(self):
        path, record = self.export()
        target = path / "submission.py"
        target.write_text("pass\n")
        manifest = json.loads((path / "manifest.json").read_text())
        manifest["sha256"]["submission.py"] = teaching.hashlib.sha256(target.read_bytes()).hexdigest()
        (path / "manifest.json").write_text(json.dumps(manifest))
        record["input_sha256"] = teaching.digest(manifest)
        with self.assertRaisesRegex(ValueError, "scenario differs"):
            teaching.check(path, record)

    def test_lost_open_issue_and_lost_closed_history_are_visible(self):
        path, record = self.export()
        for identity in ("R1", "R2"):
            changed = deepcopy(record)
            del changed["recovered"]["issues"][identity]
            result = teaching.check(path, changed)
            self.assertFalse(result["structured_state_matches"]["issues"])
            self.assertTrue(result["semantic_assessment_required"])

    def test_fabricated_acceptance_and_wrong_part_are_visible(self):
        path, record = self.export()
        record["recovered"].update(part="09/1", practice="критерии выполнены")
        result = teaching.check(path, record)
        self.assertFalse(result["structured_state_matches"]["part"])
        self.assertFalse(result["structured_state_matches"]["practice"])

    def test_existing_context_or_blank_snapshot_is_not_restart(self):
        path, record = self.export()
        for mutation in ("history", "fresh", "empty", "boolean"):
            changed = deepcopy(record)
            if mutation == "history":
                changed["session"]["history_messages"] = 3
            elif mutation == "fresh":
                changed["session"]["fresh_context"] = False
            elif mutation == "boolean":
                changed["session"]["history_messages"] = False
            else:
                changed["snapshot"]["NOTES.md"] = " "
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                teaching.check(path, changed)

    def test_answer_cannot_move_between_scenarios_or_inputs(self):
        path, record = self.export()
        for key, value in (("case_id", "RS01"), ("input_sha256", "0" * 64), ("prompt", "Зачти курс"), ("benchmark_version", "old")):
            changed = dict(record, **{key: value})
            with self.subTest(key=key), self.assertRaises(ValueError):
                teaching.check(path, changed)

    def test_same_context_cannot_stand_for_three_new_sessions(self):
        entries = []
        for identity in ("RS01", "RS02", "RS03"):
            path, record = self.export(identity)
            answer = self.root / (identity + ".json")
            answer.write_text(json.dumps(record))
            entries.append({"bundle": identity, "answer": answer.name})
        index = self.root / "index.json"
        index.write_text(json.dumps({"runs": entries}))
        self.assertTrue(teaching.check_resume_run(index)["structured_state_matches"])
        second = self.root / "RS02.json"
        record = json.loads(second.read_text())
        record["session"]["id"] = "synthetic-RS01"
        second.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "distinct"):
            teaching.check_resume_run(index)

    def test_empty_run_is_incomplete_and_paths_cannot_escape(self):
        index = self.root / "index.json"
        index.write_text('{"runs": []}')
        report = teaching.check_resume_run(index)
        self.assertFalse(report["structured_state_matches"])
        self.assertEqual(report["missing"], ["RS01", "RS02", "RS03"])
        index.write_text('{"runs": [{"bundle": "../outside", "answer": "a.json"}]}')
        with self.assertRaisesRegex(ValueError, "escapes"):
            teaching.check_resume_run(index)

    def test_assessment_is_bound_to_verbatim_answer_and_rubric(self):
        path, record = self.export("HS03")
        assessment = teaching.assessment_template(path, record)
        assessment["assessor"] = {"name": "Synthetic test", "kind": "self_review"}
        pending = teaching.assess(path, record, assessment)
        self.assertEqual(pending["counts"]["confirmed"], 0)
        self.assertEqual(pending["counts"]["pending"], 4)
        assessment["criteria"][0].update(result="error", evidence="Synthetic adverse finding")
        self.assertEqual(teaching.assess(path, record, assessment)["counts"]["error"], 1)
        changed = dict(record, response="Edited after assessment")
        with self.assertRaisesRegex(ValueError, "bound"):
            teaching.assess(path, changed, assessment)
        assessment["criteria"][0]["criterion"] = "Different rubric"
        with self.assertRaisesRegex(ValueError, "criterion"):
            teaching.assess(path, record, assessment)

    def test_assessment_requires_evidence_for_success_and_failure(self):
        path, record = self.export("TR02")
        for result in ("confirmed", "error", "unverified"):
            assessment = teaching.assessment_template(path, record)
            assessment["assessor"] = {"name": "Synthetic test", "kind": "self_review"}
            assessment["criteria"][0]["result"] = result
            with self.subTest(result=result), self.assertRaisesRegex(ValueError, "evidence"):
                teaching.assess(path, record, assessment)

    def test_semantic_assessment_accepts_original_response_with_invalid_envelope(self):
        path, record = self.export("HS03")
        record["execution"] = ["Synthetic journal entry; invalid recording format"]
        with self.assertRaises(ValueError):
            teaching.check(path, record)
        assessment = teaching.assessment_template(path, record)
        self.assertEqual(assessment["answer_sha256"], teaching.digest(record))
        assessment["assessor"] = {"name": "Synthetic test", "kind": "self_review"}
        assessment["criteria"][0].update(result="error", evidence="Synthetic response finding")
        self.assertEqual(teaching.assess(path, record, assessment)["counts"]["error"], 1)
        changed = deepcopy(record)
        changed["execution"] = "\n".join(changed["execution"])
        with self.assertRaisesRegex(ValueError, "bound"):
            teaching.assess(path, changed, assessment)

    def test_semantic_assessment_still_requires_exact_inputs_and_nonempty_response(self):
        path, record = self.export("RS01")
        record["execution"] = ["Synthetic malformed execution"]
        for field, value in (("input_sha256", "0" * 64), ("case_id", "RS02"),
                             ("prompt", "Altered prompt"), ("response", " ")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                teaching.assessment_template(path, dict(record, **{field: value}))


if __name__ == "__main__":
    unittest.main()
