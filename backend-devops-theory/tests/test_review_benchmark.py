import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1] / "assets/review-benchmark"))
import benchmark
from assessment import DIMENSIONS, assessment_template
from corpus import CASES, LEGACY_VERSION, VERSION, cases_for, verify_case


class ReviewBenchmark(unittest.TestCase):
    def answer(self, version=VERSION):
        return {"reviews":[{"case_id":c["id"],"classification":c["classes"][0],"verdict":c["verdict"],
                           "criteria":{"C1":c["criterion"]},"next_step":"Synthetic grader test, not a review",
                           "findings":[{"criterion":"C1","file":"submission.py","line":1,
                                        "explanation":"test fixture","repro":"test fixture","direction":"test fixture"}]
                           if c["classes"][0] in ("code_defect","test_defect") else []} for c in cases_for(version)]}

    def test_all_fixtures_demonstrate_authored_behavior(self):
        for case in CASES:
            with self.subTest(case=case["id"]):
                self.assertTrue(verify_case(case))

    def test_export_has_no_oracle_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)/"blind"
            benchmark.export(target)
            self.assertEqual(len(list(target.glob("RV*/submission.py"))),20)
            for filename in ("corpus.py", "audit_cases.py", "assessment.py"):
                self.assertFalse((target / filename).exists())
            manifest = json.loads((target / "manifest.json").read_text())
            self.assertNotIn("classes",json.dumps(manifest))
            self.assertEqual(manifest["version"], VERSION)
            self.assertIn("REVIEW.md", manifest["sha256"])
            actual = {str(path.relative_to(target)): hashlib.sha256(path.read_bytes()).hexdigest()
                      for path in target.rglob("*") if path.is_file() and path.name != "manifest.json"}
            self.assertEqual(manifest["sha256"], actual)
            expected_files = {"REVIEW.md", "manifest.json"} | {
                case["id"] + "/" + name for case in CASES for name in benchmark.case_files(case)}
            self.assertEqual(set(actual) | {"manifest.json"}, expected_files)
            with self.assertRaises(ValueError):
                benchmark.export(target)

    def test_perfect_labels_are_not_claimed_semantic_review(self):
        result = benchmark.score(self.answer())
        self.assertEqual(result["rubric_matches"],20)
        self.assertEqual(result["code_defect_precision"],1)
        self.assertEqual(result["code_defect_recall"],1)
        self.assertTrue(result["human_review_required"])
        self.assertTrue(all(not row["explanation_verified"] for row in result["rows"]))
        self.assertEqual(result["explanation_assessment"]["assessed"], 0)
        self.assertEqual(result["explanation_assessment"]["mean_scores"]["guidance"], None)

    def test_false_positive_and_missing_bug_counted(self):
        answer = self.answer()
        answer["reviews"] = answer["reviews"][1:]
        answer["reviews"][3]["classification"] = "code_defect"  # Correct RV05 wrongly rejected.
        result = benchmark.score(answer)
        self.assertEqual(result["code_defect_fp"],1)
        self.assertEqual(result["code_defect_fn"],1)
        self.assertEqual(result["missing"],["RV01"])

    def test_duplicate_cannot_inflate_score(self):
        answer = self.answer()
        answer["reviews"].append(answer["reviews"][0])
        with self.assertRaises(ValueError):
            benchmark.score(answer)

    def test_malformed_answers_rejected(self):
        for answer in ([],{}, {"reviews":{}}, {"reviews":["wrong"]}, {"reviews":[{"criteria":[]}]}):
            with self.subTest(answer=answer), self.assertRaises(ValueError):
                benchmark.score(answer)

    def test_label_without_repro_card_does_not_get_full_match(self):
        answer = self.answer()
        answer["reviews"][0]["findings"] = []
        result = benchmark.score(answer)
        self.assertEqual(result["rubric_matches"],19)
        self.assertIn("RV01",result["format_errors"])

    def test_new_missed_defect_false_alarm_and_wrong_rejection(self):
        answer = self.answer()
        by_id = {review["case_id"]: review for review in answer["reviews"]}
        by_id["RV13"].update(classification="valid", verdict="accepted")
        by_id["RV16"].update(classification="code_defect", verdict="needs_changes")
        by_id["RV20"].update(classification="test_defect", verdict="needs_changes")
        answer["reviews"].remove(by_id["RV17"])
        result = benchmark.score(answer)
        self.assertEqual(result["code_defect_tp"], 5)
        self.assertEqual(result["code_defect_fp"], 1)
        self.assertEqual(result["code_defect_fn"], 2)
        self.assertEqual(result["false_code_defect_claims"], ["RV16"])
        self.assertEqual(result["missed_code_defects"], ["RV13", "RV17"])
        self.assertEqual(result["incorrect_rejections"], ["RV20"])

    def test_repaired_serial_harness_is_not_the_authored_counterexample(self):
        case = deepcopy(next(case for case in CASES if case["id"] == "RV15"))
        case["extra"]["test_submission.py"] = '''from concurrent.futures import ThreadPoolExecutor
def run_concurrent_test(attempt):
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(attempt), pool.submit(attempt)]
        return [future.result(timeout=2) for future in futures]
'''
        self.assertFalse(verify_case(case))  # Both submit calls now precede result, still no PG claim.

    def test_repaired_new_defects_do_not_satisfy_bad_probes(self):
        by_id = {case["id"]: case for case in CASES}
        for bad, good in (("RV13", "RV14"), ("RV17", "RV18"), ("RV19", "RV20")):
            with self.subTest(case=bad):
                case = deepcopy(by_id[bad])
                case["code"] = by_id[good]["code"]
                if bad == "RV17":
                    with self.assertRaises(ValueError):
                        verify_case(case)
                else:
                    self.assertFalse(verify_case(case))

    def test_stale_setup_probe_requires_failure_before_client(self):
        case = deepcopy(next(case for case in CASES if case["id"] == "RV16"))
        case["extra"]["ready.json"] = '{"id": "fresh"}'
        self.assertFalse(verify_case(case))

    def test_findings_must_point_to_existing_criterion_file_and_line(self):
        for replacement in ({"line": 999}, {"line": True}, {"file": "../oracle.py"},
                            {"file": "RV02/submission.py"}, {"file": "RV01/../submission.py"},
                            {"criterion": "C2"}, {"explanation": " "}):
            with self.subTest(replacement=replacement):
                answer = self.answer()
                answer["reviews"][0]["findings"][0].update(replacement)
                self.assertIn("RV01", benchmark.score(answer)["format_errors"])

    def test_case_relative_and_bundle_relative_paths_both_score(self):
        for version in (VERSION, LEGACY_VERSION):
            with self.subTest(version=version):
                answer = self.answer(version)
                for review in answer["reviews"]:
                    for finding in review["findings"]:
                        finding["file"] = review["case_id"] + "/" + finding["file"]
                result = benchmark.score(answer, version=version)
                self.assertEqual(result["format_errors"], [])
                self.assertEqual(result["rubric_matches"], len(cases_for(version)))

    def test_legacy_results_keep_their_original_denominator(self):
        answer = self.answer(LEGACY_VERSION)
        result = benchmark.score(answer, version=LEGACY_VERSION)
        self.assertEqual(result["cases"], 12)
        self.assertEqual(result["rubric_matches"], 12)
        self.assertEqual(result["code_defect_tp"], 4)
        self.assertEqual(result["missing"], [])
        answer["benchmark_version"] = LEGACY_VERSION
        with self.assertRaises(ValueError):
            benchmark.score(answer)

    def assessment(self, answer):
        result = assessment_template(answer, VERSION)
        result["assessor"] = {"name": "Synthetic scoring test", "kind": "self_review"}
        return result

    def rate(self, review, ratings):
        review["status"] = "assessed"
        review["ratings"] = dict(zip(DIMENSIONS, ratings))
        review["notes"] = {key: "Synthetic note for testing arithmetic, not semantic review"
                           for key in DIMENSIONS}

    def test_external_ratings_keep_partial_coverage_and_dimension_scores(self):
        answer = self.answer()
        assessment = self.assessment(answer)
        self.rate(assessment["reviews"][0], (2, 2, 1, 0))
        self.rate(assessment["reviews"][1], (0, 2, 1, 2))
        result = benchmark.score(answer, assessment)
        quality = result["explanation_assessment"]
        self.assertEqual(quality["assessed"], 2)
        self.assertEqual(len(quality["pending"]), 18)
        self.assertFalse(quality["complete"])
        self.assertEqual(quality["mean_scores"], dict(zip(DIMENSIONS, (1, 2, 1, 1))))
        self.assertTrue(all(not row["explanation_verified"] for row in result["rows"]))

    def test_label_match_does_not_override_low_explanation_ratings(self):
        answer = self.answer()
        assessment = self.assessment(answer)
        for review in assessment["reviews"]:
            self.rate(review, (0, 0, 0, 0))
        result = benchmark.score(answer, assessment)
        self.assertEqual(result["rubric_matches"], 20)
        self.assertTrue(result["explanation_assessment"]["complete"])
        self.assertEqual(result["explanation_assessment"]["mean_scores"], dict.fromkeys(DIMENSIONS, 0))

    def test_assessment_is_bound_to_answer_and_version(self):
        answer = self.answer()
        assessment = self.assessment(answer)
        for key, value in (("answer_sha256", "0" * 64), ("benchmark_version", LEGACY_VERSION)):
            changed = deepcopy(assessment)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                benchmark.score(answer, changed)
        answer["reviews"][0]["next_step"] = "Edited after assessment"
        with self.assertRaises(ValueError):
            benchmark.score(answer, assessment)

    def test_assessment_rejects_duplicate_unsubmitted_and_invalid_ratings(self):
        answer = self.answer()
        for mutation in ("duplicate", "unknown", "boolean", "out_of_range", "empty_note", "pending_rating", "assessor"):
            with self.subTest(mutation=mutation):
                assessment = self.assessment(answer)
                row = assessment["reviews"][0]
                self.rate(row, (2, 2, 2, 2))
                if mutation == "duplicate":
                    assessment["reviews"].append(deepcopy(row))
                elif mutation == "unknown":
                    row["case_id"] = "RV99"
                elif mutation == "boolean":
                    row["ratings"]["accuracy"] = True
                elif mutation == "out_of_range":
                    row["ratings"]["guidance"] = 3
                elif mutation == "empty_note":
                    row["notes"]["evidence"] = " "
                elif mutation == "pending_rating":
                    row["status"] = "pending"
                else:
                    assessment["assessor"]["name"] = ""
                with self.assertRaises(ValueError):
                    benchmark.score(answer, assessment)
        partial = deepcopy(answer)
        partial["reviews"] = partial["reviews"][:1]
        assessment = self.assessment(partial)
        extra = deepcopy(assessment["reviews"][0])
        extra["case_id"] = "RV02"
        assessment["reviews"].append(extra)
        with self.assertRaises(ValueError):
            benchmark.score(partial, assessment)


if __name__ == '__main__':
    unittest.main()
from copy import deepcopy
import hashlib
