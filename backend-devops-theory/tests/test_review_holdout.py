"""Control-set checks use synthetic answers, not model performance evidence."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "assets/review-benchmark"))
import benchmark
import review_holdout as holdout
from assessment import assessment_template
from holdout_corpus import CASES, VERSION, verify


def synthetic_answer():
    return {"benchmark_version": VERSION,
            "run": {"name": "Synthetic scorer test", "date": "2026-10-14", "kind": "self_review", "key_seen": True,
                    "tools": "No actual reviewer", "source_sha256": "a" * 64, "input_sha256": holdout.input_fingerprint()},
            "reviews": [{"case_id": c["id"], "classification": c["classes"][0], "verdict": c["verdict"],
                         "criteria": {"C1": c["criterion"]}, "next_step": "Synthetic scorer fixture",
                         "findings": [{"criterion": "C1", "file": "submission.py", "line": 1,
                                       "explanation": "Synthetic", "repro": "Synthetic", "direction": "Synthetic"}]
                         if c["classes"][0] in ("code_defect", "test_defect") else []} for c in CASES]}


class ReviewHoldout(unittest.TestCase):
    def test_all_authored_counterexamples_and_valid_alternatives(self):
        self.assertEqual(len(CASES), 12)
        for case in CASES:
            with self.subTest(case=case["id"]):
                self.assertTrue(verify(case))

    def test_repaired_cases_no_longer_match_bad_counterexamples(self):
        for first, second in ((0, 1), (2, 3), (4, 5), (6, 7)):
            case = deepcopy(CASES[first])
            case["code"] = CASES[second]["code"]
            with self.subTest(case=case["id"]):
                if case["id"] == "HC05":
                    with self.assertRaises(ValueError):
                        verify(case)
                else:
                    self.assertFalse(verify(case))

    def test_export_exact_allowlist_and_fingerprint(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "control"
            benchmark.export_cases(path, CASES, VERSION)
            manifest = json.loads((path / "manifest.json").read_text())
            self.assertEqual(holdout.answer_digest(manifest), holdout.input_fingerprint())
            expected = {"REVIEW.md", "manifest.json"} | {c["id"] + "/" + name for c in CASES for name in benchmark.case_files(c)}
            self.assertEqual({p.relative_to(path).as_posix() for p in path.rglob("*") if p.is_file()}, expected)
            for name, value in manifest["sha256"].items():
                self.assertEqual(hashlib.sha256((path / name).read_bytes()).hexdigest(), value)
            with self.assertRaises(ValueError):
                benchmark.export_cases(path, CASES, VERSION)

    def test_control_and_training_answers_cannot_be_mixed(self):
        answer = synthetic_answer()
        with self.assertRaises(ValueError):
            benchmark.score(answer)
        answer["benchmark_version"] = "2026-10-12.1"
        with self.assertRaises(ValueError):
            holdout.score(answer)

    def test_regression_compare_reports_lost_defect_false_alarm_and_rejection(self):
        baseline, candidate = synthetic_answer(), synthetic_answer()
        candidate["run"]["source_sha256"] = "b" * 64
        candidate["reviews"][0].update(classification="valid", verdict="accepted", criteria={"C1": "confirmed"})
        candidate["reviews"][1].update(classification="code_defect", verdict="needs_changes", criteria={"C1": "error"})
        report = holdout.compare(baseline, candidate)
        self.assertEqual(report["delta_candidate_minus_baseline"], {"rubric_matches": -2, "code_defect_tp": -1, "code_defect_fp": 1, "code_defect_fn": 1})
        self.assertEqual(report["scores"]["candidate"]["missed_code_defects"], ["HC01"])
        self.assertEqual(report["scores"]["candidate"]["incorrect_rejections"], ["HC02"])
        self.assertTrue(report["semantic_assessment_required"])

    def test_comparison_requires_full_inputs_and_honest_key_provenance(self):
        for mutation in ("missing", "input", "source", "key", "run"):
            candidate = synthetic_answer()
            if mutation == "missing":
                candidate["reviews"].pop()
            elif mutation == "input":
                candidate["run"]["input_sha256"] = "0" * 64
            elif mutation == "source":
                candidate["run"]["source_sha256"] = "unknown"
            elif mutation == "key":
                candidate["run"]["kind"] = "model"
            else:
                candidate.pop("run")
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                holdout.compare(synthetic_answer(), candidate)

    def test_explanation_failure_remains_visible_with_perfect_labels(self):
        answer = synthetic_answer()
        assessment = assessment_template(answer, VERSION)
        assessment["assessor"] = {"name": "Synthetic test", "kind": "self_review"}
        for row in assessment["reviews"]:
            row["status"] = "assessed"
            row["ratings"] = dict.fromkeys(row["ratings"], 0)
            row["notes"] = dict.fromkeys(row["notes"], "Synthetic adverse judgment")
        result = holdout.compare(answer, answer, None, assessment)
        self.assertEqual(result["scores"]["candidate"]["rubric_matches"], 12)
        self.assertEqual(result["scores"]["candidate"]["explanation_assessment"]["mean_scores"]["guidance"], 0)
        self.assertEqual(result["scores"]["baseline"]["explanation_assessment"]["assessed"], 0)


if __name__ == "__main__":
    unittest.main()
