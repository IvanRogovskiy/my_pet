import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1] / "assets/review-benchmark"))
import benchmark
from corpus import CASES, verify_case


class ReviewBenchmark(unittest.TestCase):
    def answer(self):
        return {"reviews":[{"case_id":c["id"],"classification":c["classes"][0],"verdict":c["verdict"],
                           "criteria":{"C1":c["criterion"]},"next_step":"Synthetic grader test, not a review",
                           "findings":[{"criterion":"C1","file":"submission.py","line":1,
                                        "explanation":"test fixture","repro":"test fixture","direction":"test fixture"}]
                           if c["classes"][0] in ("code_defect","test_defect") else []} for c in CASES]}

    def test_all_fixtures_demonstrate_authored_behavior(self):
        for case in CASES:
            with self.subTest(case=case["id"]):
                self.assertTrue(verify_case(case))

    def test_export_has_no_oracle_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)/"blind"
            benchmark.export(target)
            self.assertEqual(len(list(target.glob("RV*/submission.py"))),12)
            self.assertFalse((target / "corpus.py").exists())
            manifest = json.loads((target / "manifest.json").read_text())
            self.assertNotIn("classes",json.dumps(manifest))
            with self.assertRaises(ValueError):
                benchmark.export(target)

    def test_perfect_labels_are_not_claimed_semantic_review(self):
        result = benchmark.score(self.answer())
        self.assertEqual(result["rubric_matches"],12)
        self.assertEqual(result["code_defect_precision"],1)
        self.assertEqual(result["code_defect_recall"],1)
        self.assertTrue(result["human_review_required"])
        self.assertTrue(all(not row["explanation_verified"] for row in result["rows"]))

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
        self.assertEqual(result["rubric_matches"],11)
        self.assertIn("RV01",result["format_errors"])


if __name__ == '__main__':
    unittest.main()
