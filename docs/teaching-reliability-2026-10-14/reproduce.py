#!/usr/bin/env python3
"""Recompute recorded checks, never generate or repair teacher answers."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "evaluator"))
import teaching
sys.path.insert(0, str(ROOT / "review-evaluator"))
import benchmark
import review_holdout


def read(path):
    return json.loads(path.read_text())


def main():
    protocol = read(ROOT / "protocol.json")
    sessions, rows = set(), []
    for entry in protocol["repeat_exports"]:
        path = ROOT / "repeats" / entry["run_id"]
        answer = read(path / "output/answer.json")
        manifest, _ = teaching.bundle(path / "input")
        if teaching.digest(manifest) != entry["input_sha256"]:
            raise ValueError("issued inputs differ from preregistration")
        identity = answer.get("session", {}).get("id")
        if identity in sessions or identity != "/root/repeat_" + entry["run_id"]:
            raise ValueError("session identity mismatch or reused context")
        sessions.add(identity)
        try:
            result = teaching.check(path / "input", answer)
            format_ok = True
            state = result["structured_state_matches"]
            state_ok = all(state.values()) if state is not None else None
            error = None
        except ValueError as exc:
            format_ok, state_ok, error = False, None, str(exc)
        assessed = teaching.assess(path / "input", answer, read(path / "semantic-assessment.json"))
        rows.append({"run_id": entry["run_id"], "case": entry["case"],
                     "attempt": entry["attempt"], "format_valid": format_ok,
                     "state_matches": state_ok, "format_error": error,
                     "semantic_counts": assessed["counts"]})
    reviews = {}
    for label in ("rv20", "hc_baseline", "hc_candidate"):
        path = ROOT / "reviews" / label
        answer = read(path / "output/answer.json")
        manifest = read(path / "input/manifest.json")
        for name, expected in manifest["sha256"].items():
            if hashlib.sha256((path / "input" / name).read_bytes()).hexdigest() != expected:
                raise ValueError("review input changed")
        if answer["run"] != read(path / "run-metadata.json"):
            raise ValueError("review provenance changed")
        api = benchmark if label == "rv20" else review_holdout
        reviews[label] = api.score(answer, read(path / "semantic-assessment.json"))
    def answer(label):
        return read(ROOT / "reviews" / label / "output/answer.json")
    def assessment(label):
        return read(ROOT / "reviews" / label / "semantic-assessment.json")
    comparison = review_holdout.compare(answer("hc_baseline"), answer("hc_candidate"),
                                        assessment("hc_baseline"), assessment("hc_candidate"))
    result = {"repeats": rows, "reviews": reviews,
              "holdout_delta": comparison["delta_candidate_minus_baseline"],
              "semantic_verification": "external coordinator judgment, not established by this script"}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
