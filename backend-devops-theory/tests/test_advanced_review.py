"""Counterexamples, coverage failures and blind rating integrity, not model scores."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "assets/review-benchmark"))
import calibration
import review_advanced as advanced


def synthetic_answer(split="development"):
    return {"benchmark_version": advanced.version_for(split), "input_sha256": advanced.fingerprint(split),
            "reviews": [{"case_id": c["id"], "classification": c["classes"][0], "verdict": c["verdict"],
                         "criteria": {"C1": c["criterion"]}, "next_step": "Synthetic scorer test, no teacher",
                         "findings": [{"criterion": "C1", "file": "submission.py", "line": 1,
                                       "explanation": "Synthetic", "repro": "Synthetic", "direction": "Synthetic"}]
                         if c["defects"] else []} for c in advanced.cases_for(split)]}


class AdvancedReview(unittest.TestCase):
    def test_all_counterexamples_and_valid_alternatives(self):
        for split in ("development", "control"):
            for case in advanced.cases_for(split):
                with self.subTest(case=case["id"]):
                    self.assertTrue(all(advanced.verify(case).values()))

    def test_partial_repairs_leave_second_independent_defect_visible(self):
        case = deepcopy(advanced.cases_for("development")[0])
        case["code"] = case["code"].replace('    if token in jobs:', '    token = (tenant, token)\n    if token in jobs:')
        self.assertEqual(advanced.verify(case), {"tenant": False, "nested_snapshot": True})
        case = deepcopy(advanced.cases_for("development")[0])
        case["code"] = 'from copy import deepcopy\n' + case["code"].replace('dict(payload)', 'deepcopy(payload)')
        self.assertEqual(advanced.verify(case), {"tenant": True, "nested_snapshot": False})

    def test_export_has_no_reserved_inputs_or_author_keys(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "issued"
            advanced.export_cases(root, advanced.cases_for("development"), advanced.version_for("development"))
            manifest = json.loads((root / "manifest.json").read_text())
            self.assertEqual(advanced.answer_digest(manifest), advanced.fingerprint("development"))
            self.assertFalse(any(name.startswith("AH") for name in manifest["sha256"]))
            texts = "\n".join(p.read_text() for p in root.rglob("*") if p.is_file())
            for c in advanced.cases_for("development"):
                self.assertNotIn(c["reason"], texts)
                for defect in c["defects"]:
                    self.assertNotIn(defect["criterion"], texts)

    def test_split_or_input_substitution_is_rejected(self):
        answer = synthetic_answer()
        with self.assertRaises(ValueError):
            advanced.score(answer, "control")
        answer["input_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            advanced.score(answer, "development")

    def test_perfect_labels_can_still_miss_a_second_defect(self):
        answer = synthetic_answer()
        ratings = advanced.template(answer, "development")
        ratings["assessor"] = {"name": "Synthetic evaluator test", "kind": "self_review"}
        row = ratings["defect_coverage"][0]
        row.update(result="found", finding_indices=[0], evidence="Synthetic evidence")
        ratings["defect_coverage"][1].update(result="missed", evidence="Synthetic missed alias")
        report = advanced.score(answer, "development", ratings)
        self.assertEqual(report["rubric_matches"], 8)
        self.assertEqual(report["defect_coverage"]["counts"]["missed"], 1)
        self.assertEqual(report["defect_coverage"]["counts"]["pending"], 4)
        row["finding_indices"] = [99]
        with self.assertRaises(ValueError):
            advanced.score(answer, "development", ratings)

    def test_missing_coverage_or_changed_answer_cannot_reuse_assessment(self):
        answer = synthetic_answer()
        ratings = advanced.template(answer, "development")
        ratings["assessor"] = {"name": "Synthetic", "kind": "self_review"}
        ratings["defect_coverage"].pop()
        with self.assertRaises(ValueError):
            advanced.score(answer, "development", ratings)
        answer["reviews"][0]["next_step"] = "Changed"
        with self.assertRaises(ValueError):
            advanced.score(answer, "development", ratings)


class Calibration(unittest.TestCase):
    def fixture(self):
        payload = {"version": "synthetic", "items": [{"id": "P01"}]}
        sha = calibration.answer_digest(payload)
        mapping = {"bundle_sha256": sha, "rows": [{"id": "P01", "previous": {
            "ratings": dict.fromkeys(calibration.DIMENSIONS, 2), "notes": dict.fromkeys(calibration.DIMENSIONS, "Earlier evidence")}}]}
        ratings = {"bundle_sha256": sha, "assessor": {"name": "Synthetic", "kind": "model", "session_id": "test-only", "fresh_context": True},
                   "reviews": [{"id": "P01", "ratings": dict.fromkeys(calibration.DIMENSIONS, 2),
                                "notes": dict.fromkeys(calibration.DIMENSIONS, "Synthetic later evidence")}]}
        return payload, mapping, ratings

    def test_disagreement_is_reported_without_overwriting_previous(self):
        payload, mapping, ratings = self.fixture()
        before = deepcopy(mapping)
        ratings["reviews"][0]["ratings"]["guidance"] = 0
        result = calibration.compare(payload, mapping, ratings)
        self.assertEqual(result["exact_agreement"], 3)
        self.assertEqual(result["disagreements"][0]["delta"], -2)
        self.assertEqual(mapping, before)

    def test_byte_binding_preserves_first_record_but_rejects_other_bytes(self):
        payload, mapping, ratings = self.fixture()
        raw = json.dumps(payload, indent=2).encode()
        ratings["bundle_sha256"] = hashlib.sha256(raw).hexdigest()
        first = deepcopy(ratings)
        self.assertEqual(calibration.compare(payload, mapping, ratings, raw)["rating_hash_kind"], "file_bytes")
        self.assertEqual(first, ratings)
        with self.assertRaises(ValueError):
            calibration.compare(payload, mapping, ratings, raw + b"\n")
        with self.assertRaises(ValueError):
            calibration.compare({"items": []}, mapping, ratings, raw)

    def test_malformed_incomplete_duplicate_and_unbound_ratings_fail(self):
        for mutation in ("empty", "duplicate", "bool", "note", "hash", "history"):
            payload, mapping, ratings = self.fixture()
            if mutation == "empty": ratings["reviews"] = []
            elif mutation == "duplicate": ratings["reviews"] *= 2
            elif mutation == "bool": ratings["reviews"][0]["ratings"]["accuracy"] = True
            elif mutation == "note": ratings["reviews"][0]["notes"]["accuracy"] = " "
            elif mutation == "hash": ratings["bundle_sha256"] = "0" * 64
            else: ratings["assessor"]["fresh_context"] = False
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                calibration.compare(payload, mapping, ratings)

    def test_export_removes_profile_and_prior_score_identifiers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            answer = synthetic_answer()
            answer["run"] = {"name": "SECRET-PROFILE", "source_sha256": "SECRET-SHA"}
            assessment = advanced.assessment_template(answer, answer["benchmark_version"])
            assessment["assessor"] = {"name": "SECRET-ASSESSOR", "kind": "model"}
            for row in assessment["reviews"]:
                row.update(status="assessed", ratings=dict.fromkeys(calibration.DIMENSIONS, 2),
                           notes=dict.fromkeys(calibration.DIMENSIONS, "SECRET-PRIOR-NOTE"))
            calibration.write(root / "answer.json", answer)
            calibration.write(root / "assessment.json", assessment)
            (root / "input").mkdir()
            (root / "input/assignment.md").write_text("AD01 assignment")
            calibration.write(root / "spec.json", {"selection": [{"answer": "answer.json", "assessment": "assessment.json", "inputs": "input", "case_id": "AD01"}]})
            calibration.export(root / "spec.json", root / "blind")
            text = (root / "blind/input/bundle.json").read_text()
            for secret in ("SECRET-PROFILE", "SECRET-SHA", "SECRET-ASSESSOR", "SECRET-PRIOR-NOTE", "AD01"):
                self.assertNotIn(secret, text)


if __name__ == "__main__":
    unittest.main()
