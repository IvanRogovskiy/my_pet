#!/usr/bin/env python3
"""Isolated control set and comparison of actual, provenance-bearing answers."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from assessment import answer_digest, assessment_template
from benchmark import RUBRIC, case_files, export_cases, score_cases
from holdout_corpus import CASES, VERSION, verify


def input_fingerprint():
    files = {"REVIEW.md": RUBRIC + f"\nРедакция набора: {VERSION}. Работ: {len(CASES)}.\n"}
    for case in CASES:
        files.update({case["id"] + "/" + name: text for name, text in case_files(case).items()})
    return answer_digest({"version": VERSION, "sha256": {
        name: hashlib.sha256(text.encode()).hexdigest() for name, text in files.items()}})


def score(answer, assessment=None):
    if not isinstance(answer, dict) or answer.get("benchmark_version") != VERSION:
        raise ValueError("explicit holdout benchmark_version required")
    return score_cases(answer, CASES, VERSION, assessment)


def provenance(answer):
    run = answer.get("run")
    if not isinstance(run, dict):
        raise ValueError("comparison requires run provenance")
    for key in ("name", "date", "tools"):
        if not isinstance(run.get(key), str) or not run[key].strip():
            raise ValueError("run requires " + key)
    if run.get("kind") not in ("human", "model", "self_review") or type(run.get("key_seen")) is not bool:
        raise ValueError("run requires kind and explicit key_seen boolean")
    if run["key_seen"] and run["kind"] != "self_review":
        raise ValueError("key-aware reviewer must declare self_review")
    if not isinstance(run.get("source_sha256"), str) or not re.fullmatch("[0-9a-f]{64}", run["source_sha256"]):
        raise ValueError("source_sha256 must hash the frozen teacher instruction manifest")
    if run.get("input_sha256") != input_fingerprint():
        raise ValueError("run belongs to different control inputs")
    return run


def compare(baseline, candidate, baseline_assessment=None, candidate_assessment=None):
    runs = [provenance(answer) for answer in (baseline, candidate)]
    scores = [score(baseline, baseline_assessment), score(candidate, candidate_assessment)]
    if any(s["missing"] or s["format_errors"] for s in scores):
        raise ValueError("comparison requires both complete, structurally valid answers")
    metrics = ("rubric_matches", "code_defect_tp", "code_defect_fp", "code_defect_fn")
    return {"benchmark_version": VERSION, "cases": len(CASES),
            "runs": dict(zip(("baseline", "candidate"), runs)),
            "scores": dict(zip(("baseline", "candidate"), scores)),
            "delta_candidate_minus_baseline": {k: scores[1][k] - scores[0][k] for k in metrics},
            "answer_sha256": {"baseline": answer_digest(baseline), "candidate": answer_digest(candidate)},
            "semantic_assessment_required": True,
            "limitation": "Provenance is declared, not independently attested. One comparison does not establish teaching effectiveness. Preserve each run; do not select only the best."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("validate", "export", "score", "assessment-template", "compare"))
    parser.add_argument("path", type=Path, nargs="?")
    parser.add_argument("candidate", type=Path, nargs="?")
    parser.add_argument("--assessment", type=Path)
    parser.add_argument("--candidate-assessment", type=Path)
    args = parser.parse_args()
    try:
        if args.assessment and args.action not in ("score", "compare"):
            parser.error("--assessment only for score/compare")
        if args.candidate_assessment and args.action != "compare":
            parser.error("--candidate-assessment only for compare")
        if args.candidate and args.action != "compare":
            parser.error("candidate only for compare")
        if args.action == "validate":
            result = {c["id"]: verify(c) for c in CASES}
            print(json.dumps(result, indent=2))
            return 0 if all(result.values()) else 1
        if args.path is None:
            parser.error("path required")
        if args.action == "export":
            export_cases(args.path, CASES, VERSION)
            result = {"path": str(args.path), "input_sha256": input_fingerprint(), "version": VERSION}
        else:
            answer = json.loads(args.path.read_text())
            assessment = json.loads(args.assessment.read_text()) if args.assessment else None
            if args.action == "compare":
                if args.candidate is None:
                    parser.error("candidate required")
                other = json.loads(args.candidate_assessment.read_text()) if args.candidate_assessment else None
                result = compare(answer, json.loads(args.candidate.read_text()), assessment, other)
            elif args.action == "assessment-template":
                score(answer)
                result = assessment_template(answer, VERSION)
            else:
                result = score(answer, assessment)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(f"Invalid input: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
