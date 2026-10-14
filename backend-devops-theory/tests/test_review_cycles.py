"""Synthetic evaluator regressions, not observed model or human review quality."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "assets/review-benchmark"))
from assessment import answer_digest, assessment_template
from cycle_corpus import CYCLES, VERSION, observe, validate
import review_cycles


ISSUE_HISTORY = {
    "RC01": [
        [("scope", "C1", "open"), ("payload", "C2", "open")],
        [("scope", "C1", "closed"), ("payload", "C2", "open")],
        [("scope", "C1", "closed"), ("payload", "C2", "closed")],
    ],
    "RC02": [
        [("admin", "C3", "open")],
        [("admin", "C3", "closed"), ("leak", "C2", "open")],
        [("admin", "C3", "closed"), ("leak", "C2", "closed")],
    ],
    "RC03": [
        [("R1", "C1", "withdrawn")],
        [("R1", "C1", "withdrawn"), ("limit", "C1", "open")],
        [("R1", "C1", "withdrawn"), ("limit", "C1", "closed")],
    ],
}


def synthetic_transcript(identity):
    """Known-answer test data; must never be published as a real dialogue."""
    transcript = {"benchmark_version": VERSION, "cycle_id": identity,
                  "reviewer": {"name": "Synthetic evaluator test", "date": "2026-10-13", "kind": "self_review"},
                  "turns": []}
    for number, step in enumerate(CYCLES[identity]["steps"], 1):
        transcript["turns"].append({"turn": number, "prompt": step["prompt"],
            "input_sha256": review_cycles.input_hashes(identity, number),
            "previous_sha256": answer_digest(transcript["turns"][-1]) if transcript["turns"] else None,
            "response": "Synthetic response to test the evaluator. No teacher dialogue was performed.",
            "review": {"criteria": deepcopy(step["expected"]), "verdict": step["verdict"],
                       "issues": [{"id": key, "criterion": criterion, "status": status,
                                   "reason": "Synthetic reason, not a semantic assessment"}
                                  for key, criterion, status in ISSUE_HISTORY[identity][number - 1]],
                       "next_step": "Synthetic next step"},
            "snapshot": {"PROGRESS.md": f"Synthetic state after turn {number}", "NOTES.md": "Synthetic observations"}})
    return transcript


def relink(transcript):
    """Model a different, internally consistent response history for negative tests."""
    previous = None
    for turn in transcript["turns"]:
        turn["previous_sha256"] = previous
        previous = answer_digest(turn)


class ReviewCycles(unittest.TestCase):
    def test_executable_submissions_cover_partial_fix_regression_and_objection(self):
        actual = validate()
        self.assertEqual(sum(len(rows) for rows in actual.values()), 9)
        self.assertTrue(all(row["matches"] for rows in actual.values() for row in rows))
        self.assertEqual([row["observed"] for row in actual["RC01"]], [
            {"C1": "error", "C2": "error"}, {"C1": "confirmed", "C2": "error"},
            {"C1": "confirmed", "C2": "confirmed"}])
        self.assertEqual([row["observed"]["C2"] for row in actual["RC02"]], ["confirmed", "error", "confirmed"])
        self.assertEqual([row["observed"]["C1"] for row in actual["RC03"]], ["confirmed", "error", "confirmed"])

    def test_bad_mutants_are_detected_by_behavior(self):
        actual = observe("RC02", 'def can_read(actor, order):\n    return True\n')
        self.assertEqual(actual["C2"], "error")
        actual = observe("RC03", 'def quantity(value):\n    return value\n')
        self.assertEqual(actual["C1"], "error")

    def test_export_reveals_only_current_submission_and_hashes_all_files(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "turn1"
            review_cycles.export(path, "RC01")
            self.assertEqual((path / "submission.py").read_text(), CYCLES["RC01"]["steps"][0]["code"])
            files = {p.name for p in path.iterdir()}
            self.assertEqual(files, {"REVIEW.md", "assignment.md", "submission.py", "prompt.txt",
                                     "initial-history.json", "history.json", "answer-template.json", "manifest.json"})
            manifest = json.loads((path / "manifest.json").read_text())
            self.assertEqual(set(manifest["sha256"]), files - {"manifest.json"})
            for name, digest in manifest["sha256"].items():
                self.assertEqual(hashlib.sha256((path / name).read_bytes()).hexdigest(), digest)
            template = json.loads((path / "answer-template.json").read_text())
            self.assertEqual(len(template["turns"]), 1)
            self.assertEqual(template["turns"][0]["review"]["issues"], [])
            with self.assertRaises(ValueError):
                review_cycles.export(path, "RC02")

    def test_next_export_requires_recorded_prefix_and_keeps_wrong_reviews(self):
        history = synthetic_transcript("RC01")
        history["turns"] = history["turns"][:1]
        history["turns"][0]["review"]["verdict"] = "accepted"  # Wrong verdict must not reveal a grading hint or block turn 2.
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "turn2"
            review_cycles.export(path, "RC01", 2, history)
            template = json.loads((path / "answer-template.json").read_text())
            self.assertEqual(template["turns"][:-1], history["turns"])
            self.assertEqual(template["turns"][-1]["previous_sha256"], answer_digest(history["turns"][0]))
            with self.assertRaises(ValueError):
                review_cycles.export(Path(temp) / "skipped", "RC01", 3, history)
            with self.assertRaises(ValueError):
                review_cycles.export(Path(temp) / "wrong-case", "RC02", 2, history)
            self.assertFalse((Path(temp) / "skipped").exists())

    def test_matching_state_never_claims_verified_explanations(self):
        for identity in CYCLES:
            with self.subTest(cycle=identity):
                result = review_cycles.score(synthetic_transcript(identity))
                self.assertTrue(result["structured_cycle_matches"])
                self.assertEqual(result["matched_turns"], 3)
                self.assertEqual(result["explanation_assessment"]["assessed"], 0)
                self.assertTrue(result["semantic_assessment_required"])
                self.assertTrue(all(not row["explanation_verified"] for row in result["rows"]))

    def test_partial_fix_cannot_close_remaining_issue_or_accept(self):
        transcript = synthetic_transcript("RC01")
        review = transcript["turns"][1]["review"]
        review["verdict"] = "accepted"
        review["criteria"]["C2"] = "confirmed"
        review["issues"][1]["status"] = "closed"
        relink(transcript)
        result = review_cycles.score(transcript)
        self.assertFalse(result["structured_cycle_matches"])
        self.assertEqual(result["premature_acceptances"], [2])
        self.assertFalse(result["rows"][1]["issue_states_match"])

    def test_regression_must_be_found_even_when_original_issue_is_fixed(self):
        transcript = synthetic_transcript("RC02")
        review = transcript["turns"][1]["review"]
        review["criteria"]["C2"] = "confirmed"
        review["issues"] = review["issues"][:1]
        review["verdict"] = "accepted"
        relink(transcript)
        result = review_cycles.score(transcript)
        self.assertEqual(result["missed_regressions"], [{"turn": 2, "criterion": "C2"}])
        self.assertFalse(result["structured_cycle_matches"])

    def test_issue_ids_survive_across_turns_and_cannot_be_reused(self):
        transcript = synthetic_transcript("RC01")
        transcript["turns"][1]["review"]["issues"][1]["id"] = "renamed-payload"
        relink(transcript)
        result = review_cycles.score(transcript)
        self.assertIn({"turn": 2, "issue_id": "payload"}, result["lost_issue_ids"])
        transcript = synthetic_transcript("RC02")
        transcript["turns"][1]["review"]["issues"][1]["id"] = "admin"
        transcript["turns"][1]["review"]["issues"] = transcript["turns"][1]["review"]["issues"][1:]
        relink(transcript)
        result = review_cycles.score(transcript)
        self.assertEqual(result["rows"][1]["reused_issue_ids"], ["admin"])

    def test_wrong_review_is_withdrawn_not_closed_as_a_student_fix(self):
        transcript = synthetic_transcript("RC03")
        transcript["turns"][0]["review"]["issues"][0]["status"] = "closed"
        relink(transcript)
        self.assertFalse(review_cycles.score(transcript)["rows"][0]["issue_states_match"])
        transcript = synthetic_transcript("RC03")
        issues = transcript["turns"][2]["review"]["issues"]
        issues[0]["status"], issues[1]["status"] = issues[1]["status"], issues[0]["status"]
        result = review_cycles.score(transcript)
        self.assertTrue(result["rows"][2]["issue_states_match"])
        self.assertEqual(result["rows"][2]["altered_withdrawals"], ["R1"])
        self.assertFalse(result["structured_cycle_matches"])

    def test_complete_fix_is_accepted_without_new_requirements(self):
        transcript = synthetic_transcript("RC01")
        transcript["turns"][-1]["review"]["verdict"] = "needs_changes"
        self.assertFalse(review_cycles.score(transcript)["rows"][-1]["verdict_matches"])
        transcript["turns"][-1]["review"]["criteria"]["C3"] = "unverified"
        with self.assertRaisesRegex(ValueError, "original assignment"):
            review_cycles.score(transcript)

    def test_partial_transcript_cannot_be_a_complete_cycle(self):
        transcript = synthetic_transcript("RC03")
        transcript["turns"] = transcript["turns"][:1]
        result = review_cycles.score(transcript)
        self.assertFalse(result["transcript_complete"])
        self.assertFalse(result["structured_cycle_matches"])
        self.assertEqual(result["matched_turns"], 1)
        self.assertEqual(len(result["explanation_assessment"]["pending"]), 3)

    def test_transcript_binds_prompts_submissions_and_prior_snapshots(self):
        for mutation in ("input", "prompt", "response", "snapshot", "order", "duplicate", "version"):
            with self.subTest(mutation=mutation):
                transcript = synthetic_transcript("RC01")
                first = transcript["turns"][0]
                if mutation == "input":
                    first["input_sha256"]["submission.py"] = "0" * 64
                elif mutation == "prompt":
                    first["prompt"] = "A different assignment"
                elif mutation == "response":
                    first["response"] += " Edited later"
                elif mutation == "snapshot":
                    first["snapshot"]["PROGRESS.md"] += " Edited later"
                elif mutation == "order":
                    transcript["turns"].reverse()
                elif mutation == "duplicate":
                    transcript["turns"][1] = deepcopy(first)
                else:
                    transcript["benchmark_version"] = "wrong"
                with self.assertRaises(ValueError):
                    review_cycles.check(transcript)

    def test_malformed_snapshots_issue_ids_and_criteria_are_rejected(self):
        for mutation in ("blank-response", "blank-snapshot", "wrong-snapshot", "duplicate-id", "missing-criterion"):
            with self.subTest(mutation=mutation):
                transcript = synthetic_transcript("RC01")
                entry = transcript["turns"][-1]
                if mutation == "blank-response":
                    entry["response"] = " "
                elif mutation == "blank-snapshot":
                    entry["snapshot"]["NOTES.md"] = ""
                elif mutation == "wrong-snapshot":
                    entry["snapshot"] = {"PROGRESS.md": "x"}
                elif mutation == "duplicate-id":
                    entry["review"]["issues"].append(deepcopy(entry["review"]["issues"][0]))
                else:
                    del entry["review"]["criteria"]["C2"]
                with self.assertRaises(ValueError):
                    review_cycles.check(transcript)

    def test_external_assessment_is_bound_to_entire_cycle_and_tracks_coverage(self):
        transcript = synthetic_transcript("RC03")
        assessment = assessment_template(review_cycles.assessment_answer(transcript), VERSION)
        assessment["assessor"] = {"name": "Synthetic arithmetic test", "kind": "self_review"}
        row = assessment["reviews"][0]
        row["status"] = "assessed"
        row["ratings"] = dict.fromkeys(row["ratings"], 0)
        row["notes"] = dict.fromkeys(row["notes"], "Synthetic note; no semantic assessment")
        result = review_cycles.score(transcript, assessment)
        self.assertTrue(result["structured_cycle_matches"])
        self.assertEqual(result["explanation_assessment"]["assessed"], 1)
        self.assertEqual(result["explanation_assessment"]["pending"], ["RC03:02", "RC03:03"])
        self.assertEqual(result["explanation_assessment"]["mean_scores"]["accuracy"], 0)
        transcript["turns"][-1]["response"] += " changed"
        with self.assertRaisesRegex(ValueError, "different answer"):
            review_cycles.score(transcript, assessment)


if __name__ == "__main__":
    unittest.main()
