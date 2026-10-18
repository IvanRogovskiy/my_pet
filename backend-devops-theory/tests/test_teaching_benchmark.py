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
from teaching_cases import CASES, VERSION, LEGACY_VERSION, PREVIOUS_VERSION, RECOVERY_VERSION, cases_for


def synthetic_record(path):
    manifest, case = teaching.bundle(path)
    identity = manifest["case_id"]
    result = {"benchmark_version": manifest["version"], "case_id": identity,
              "input_sha256": teaching.digest(manifest), "prompt": case["prompt"],
              "response": "Synthetic validator fixture; not a teacher response.",
              "execution": "Synthetic fixture, no teacher session run.",
              "session": {"id": "synthetic-" + identity, "name": "Unit test", "date": "2026-10-14",
                          "kind": "self_review", "fresh_context": True, "history_messages": 0}}
    if case["suite"] == "resume":
        result["recovered"] = dict(deepcopy(case["expected"]), next_step="Synthetic next step")
        if manifest["version"] != LEGACY_VERSION:
            result["recovered"]["practice_note"] = "Synthetic explanation, separate from status"
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
        self.assertEqual(len(CASES), 16)
        for identity, case in CASES.items():
            path, record = self.export(identity)
            manifest, _ = teaching.bundle(path)
            self.assertEqual(set(manifest["sha256"]), set(case["files"]) | {"TASK.md", "prompt.txt", "response.schema.json", "response.example.json"} |
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
        for identity in (key for key, case in CASES.items() if case["suite"] == "resume"):
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
        self.assertEqual(report["missing"], [f"RS{i:02}" for i in range(1, 8)])
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

    def test_explicit_schema_rejects_list_execution_and_conflated_practice(self):
        path, record = self.export("RS01")
        for mutate in ("execution", "practice", "missing_note", "extra_field"):
            changed = deepcopy(record)
            if mutate == "execution":
                changed["execution"] = ["static_only"]
            elif mutate == "practice":
                changed["recovered"]["practice"] += "; работа начата"
            elif mutate == "missing_note":
                del changed["recovered"]["practice_note"]
            else:
                changed["unexpected"] = True
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                teaching.check(path, changed)
        record["recovered"]["practice_note"] = "Первая попытка ещё не сдана; это пояснение, а не новый статус."
        self.assertTrue(all(teaching.check(path, record)["structured_state_matches"].values()))

    def test_legacy_records_and_rubric_are_not_reinterpreted(self):
        old = self.root / "legacy"
        teaching.export(old, "HS02", LEGACY_VERSION)
        record = synthetic_record(old)
        self.assertTrue(teaching.check(old, record)["record_complete"])
        self.assertNotIn("response.schema.json", teaching.bundle(old)[0]["sha256"])
        rubric = teaching.assessment_template(old, record)
        self.assertEqual(rubric["criteria"][2]["criterion"], "Одно диагностическое действие: ученик строит расписание.")
        new, current = self.export("HS02")
        self.assertNotEqual(rubric["criteria"][2]["criterion"], teaching.assessment_template(new, current)["criteria"][2]["criterion"])
        record["execution"] = ["Original malformed journal"]
        with self.assertRaises(ValueError):
            teaching.check(old, record)
        self.assertEqual(teaching.assessment_template(old, record)["benchmark_version"], LEGACY_VERSION)

    def test_rehashed_schema_cannot_weaken_published_contract(self):
        path, record = self.export()
        target = path / "response.schema.json"
        schema = json.loads(target.read_text())
        del schema["properties"]["execution"]["type"]
        target.write_text(json.dumps(schema))
        manifest = json.loads((path / "manifest.json").read_text())
        manifest["sha256"][target.name] = teaching.hashlib.sha256(target.read_bytes()).hexdigest()
        (path / "manifest.json").write_text(json.dumps(manifest))
        record["input_sha256"] = teaching.digest(manifest)
        with self.assertRaisesRegex(ValueError, "schema differs"):
            teaching.check(path, record)

    def test_new_example_is_explicit_shape_not_a_passing_answer(self):
        path, _ = self.export("RS03")
        example = json.loads((path / "response.example.json").read_text())
        teaching.validate_schema(example, json.loads((path / "response.schema.json").read_text()))
        with self.assertRaisesRegex(ValueError, "issued inputs"):
            teaching.check(path, example)

    def test_resume_run_cannot_mix_versions(self):
        entries = []
        for identity, version in (("RS01", LEGACY_VERSION), ("RS02", VERSION)):
            path = self.root / identity
            teaching.export(path, identity, version)
            answer = self.root / (identity + ".json")
            answer.write_text(json.dumps(synthetic_record(path)))
            entries.append({"bundle": identity, "answer": answer.name})
        index = self.root / "index.json"
        index.write_text(json.dumps({"runs": entries}))
        with self.assertRaisesRegex(ValueError, "mix benchmark versions"):
            teaching.check_resume_run(index)

    def test_previous_run_still_requires_only_its_original_three_cases(self):
        for version in (LEGACY_VERSION, PREVIOUS_VERSION):
            base = self.root / version
            entries = []
            for identity in ("RS01", "RS02", "RS03"):
                path = base / identity
                teaching.export(path, identity, version)
                answer = base / (identity + ".json")
                answer.write_text(json.dumps(synthetic_record(path)))
                entries.append({"bundle": identity, "answer": answer.name})
            index = base / "index.json"
            index.write_text(json.dumps({"runs": entries}))
            self.assertTrue(teaching.check_resume_run(index)["structured_state_matches"])
            self.assertEqual(len(cases_for(version)), 12)

    def test_unknown_is_not_closed_or_withdrawn_and_does_not_rewrite_old_schema(self):
        path, record = self.export("RS06")
        self.assertTrue(all(teaching.check(path, record)["structured_state_matches"].values()))
        for claimed in ("closed", "withdrawn", "open"):
            changed = deepcopy(record)
            changed["recovered"]["issues"]["R2"] = claimed
            self.assertFalse(teaching.check(path, changed)["structured_state_matches"]["issues"])
        old = self.root / "previous"
        teaching.export(old, "RS03", PREVIOUS_VERSION)
        before = synthetic_record(old)
        before["recovered"]["issues"]["R2"] = "unknown"
        with self.assertRaises(ValueError):
            teaching.check(old, before)

    def test_recovery_failures_cannot_be_hidden_by_fabricated_acceptance(self):
        for identity in ("RS04", "RS05", "RS06", "RS07"):
            path, record = self.export(identity)
            record["recovered"]["practice"] = "критерии выполнены"
            self.assertFalse(teaching.check(path, record)["structured_state_matches"]["practice"])
        self.assertNotIn("submission.py", CASES["RS04"]["files"])
        self.assertIn("learning/review-02.md", CASES["RS05"]["files"])

    def test_part_code_contract_is_explicit_without_reinterpreting_first_recovery_run(self):
        path, record = self.export("RS07")
        record["recovered"]["part"] = "09/1 — модульные тесты"
        with self.assertRaisesRegex(ValueError, "part"):
            teaching.check(path, record)
        old = self.root / "first-recovery"
        teaching.export(old, "RS07", RECOVERY_VERSION)
        first = synthetic_record(old)
        first["recovered"]["part"] = "09/1 — модульные тесты"
        report = teaching.check(old, first)
        self.assertTrue(report["record_complete"])
        self.assertFalse(report["structured_state_matches"]["part"])


if __name__ == "__main__":
    unittest.main()
