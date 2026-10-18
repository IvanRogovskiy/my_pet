#!/usr/bin/env python3
"""Recheck frozen records and bindings; do not regenerate answers or ratings."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "evaluators/teaching"))
import teaching
sys.path.insert(0, str(ROOT / "evaluators/review"))
import review_advanced
import calibration


def read(path):
    return json.loads(path.read_text())


def check_files(directory):
    manifest = read(directory / "manifest.json")
    for name, expected in manifest["sha256"].items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected:
            raise ValueError("changed issued input: " + name)
    return manifest


def main():
    protocol = read(ROOT / "protocol.json")
    sessions, recovery = set(), []
    def one(directory, registration):
        answer = read(directory / "output/answer.json")
        manifest, _ = teaching.bundle(directory / "input")
        if teaching.digest(manifest) != registration["input_sha256"]:
            raise ValueError("recovery differs from preregistration")
        identity = answer["session"]["id"]
        if identity != registration["expected_session"] or identity in sessions:
            raise ValueError("wrong/reused recovery context")
        sessions.add(identity)
        result = teaching.check(directory / "input", answer)
        assessed = teaching.assess(directory / "input", answer, read(directory / "semantic-assessment.json"))
        return {"case": answer["case_id"], "version": answer["benchmark_version"],
                "session": identity, "record_complete": result["record_complete"],
                "state_matches": result["structured_state_matches"], "semantic_counts": assessed["counts"],
                "assessor": assessed["assessor"]}
    for registration in protocol["recovery"]:
        recovery.append(one(ROOT / "recovery" / registration["case"], registration))
    correction = one(ROOT / "recovery-correction/RS07", read(ROOT / "correction-protocol.json"))
    answer = read(ROOT / "advanced/output/answer.json")
    manifest = check_files(ROOT / "advanced/input")
    if (review_advanced.answer_digest(manifest) != protocol["advanced"]["input_sha256"]
            or answer["run"]["session_id"] != "/root/advanced_review"):
        raise ValueError("advanced input/session changed")
    advanced = review_advanced.score(answer, "development", read(ROOT / "advanced/semantic-assessment.json"))
    if review_advanced.fingerprint("control") != protocol["advanced"]["reserved_fingerprint"]:
        raise ValueError("reserved control inputs changed")
    raw = (ROOT / "calibration/input/bundle.json").read_bytes()
    mapping = read(ROOT / "calibration/mapping.json")
    # Verify anonymity's author-side mapping against untouched historical data.
    for row in mapping["rows"]:
        entry = row["source"]
        original = read(ROOT / entry["answer"])
        old_assessment = read(ROOT / entry["assessment"])
        review = next(r for r in original["reviews"] if r["case_id"] == entry["case_id"])
        old = next(r for r in old_assessment["reviews"] if r["case_id"] == entry["case_id"])
        if (calibration.answer_digest(original) != row["answer_sha256"]
                or calibration.answer_digest(old_assessment) != row["assessment_sha256"]
                or calibration.answer_digest(review) != row["review_sha256"]
                or row["previous"]["ratings"] != old["ratings"]
                or row["previous"]["notes"] != old["notes"]):
            raise ValueError("calibration source changed")
    ratings = read(ROOT / "calibration/second-ratings.json")
    if ratings["assessor"]["session_id"] != protocol["calibration"]["session"]:
        raise ValueError("calibration context changed")
    calibrated = calibration.compare(json.loads(raw), mapping, ratings, raw)
    backend = read(ROOT / "backend/audit.json")
    if set(backend) != {"B07", "B08R", "B08I", "B17"} or any(v != [1, 0, 1] for v in backend.values()):
        raise ValueError("runtime audit results changed")
    for case, expected in backend.items():
        probes = [read(path) for path in sorted((ROOT / "backend" / case).glob("*.json"))]
        if [probe["exit"] for probe in probes] != expected:
            raise ValueError("backend summary differs from individual probes")
        for probe in probes:
            criteria = probe["criteria"]
            if (probe["case"] != case or not criteria
                    or any(type(value) is not bool for value in criteria.values())
                    or probe["passed"] is not all(criteria.values())
                    or probe["exit"] != (0 if probe["passed"] else 1)):
                raise ValueError("backend criteria/result mismatch")
    result = {"recovery_first_attempts": recovery, "separate_contract_correction": correction,
              "advanced": {k: advanced[k] for k in ("cases", "rubric_matches", "format_errors", "missing",
                  "code_defect_tp", "code_defect_fp", "code_defect_fn", "incorrect_rejections", "defect_coverage", "explanation_assessment")},
              "calibration": {k: calibrated[k] for k in ("reviews", "ratings", "exact_agreement", "by_dimension",
                  "disagreements", "rating_hash_kind", "rating_record_sha256")},
              "backend_exits": backend,
              "limitations": "No human learning measured. Semantic judgments are external model assessments; checking hashes does not establish their truth."}
    saved = ROOT / "results.json"
    if saved.exists() and read(saved) != result:
        raise ValueError("recomputed results differ from frozen report")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
