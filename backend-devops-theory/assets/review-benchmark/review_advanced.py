#!/usr/bin/env python3
"""Harder review inputs with separate development/control splits and defect coverage."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from advanced_corpus import VERSION, cases_for, verify
from assessment import answer_digest, assessment_template
from benchmark import RUBRIC, case_files, export_cases, score_cases


def version_for(split):
    cases_for(split)
    return VERSION + ":" + split


def fingerprint(split):
    cases, version = cases_for(split), version_for(split)
    files = {"REVIEW.md": RUBRIC + f"\nРедакция набора: {version}. Работ: {len(cases)}.\n"}
    for case in cases:
        files.update({case["id"] + "/" + k: v for k, v in case_files(case).items()})
    return answer_digest({"version": version, "sha256": {
        k: hashlib.sha256(v.encode()).hexdigest() for k, v in files.items()}})


def template(answer, split):
    score(answer, split)
    result = assessment_template(answer, version_for(split))
    result["defect_coverage"] = [
        {"case_id": case["id"], "defect_id": defect["id"], "criterion": defect["criterion"],
         "result": "pending", "finding_indices": [], "evidence": ""}
        for case in cases_for(split) for defect in case["defects"]]
    return result


def score(answer, split, assessment=None):
    version = version_for(split)
    if (not isinstance(answer, dict) or answer.get("benchmark_version") != version
            or answer.get("input_sha256") != fingerprint(split)):
        raise ValueError("answer must match frozen advanced version/split/inputs")
    result = score_cases(answer, cases_for(split), version, assessment)
    expected = {(c["id"], d["id"]): d["criterion"] for c in cases_for(split) for d in c["defects"]}
    counts = dict.fromkeys(("pending", "found", "missed", "unverified"), 0)
    rows = [] if assessment is None else assessment.get("defect_coverage", [])
    seen = set()
    reviews = {r["case_id"]: r for r in answer["reviews"]}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("invalid defect coverage row")
        key = (row.get("case_id"), row.get("defect_id"))
        if key not in expected or key in seen or row.get("criterion") != expected[key]:
            raise ValueError("wrong/duplicate defect criterion")
        seen.add(key)
        state, indices, evidence = row.get("result"), row.get("finding_indices"), row.get("evidence")
        if (state not in counts or not isinstance(indices, list)
                or len(set(indices)) != len(indices)
                or any(type(i) is not int or i < 0 or i >= len(reviews.get(key[0], {}).get("findings", [])) for i in indices)):
            raise ValueError("invalid defect status/finding indices")
        if state == "pending":
            if evidence != "" or indices:
                raise ValueError("pending defect must be empty")
        elif not isinstance(evidence, str) or not evidence.strip():
            raise ValueError("defect assessment requires evidence")
        if (state == "found" and not indices) or (state in ("missed", "unverified") and indices):
            raise ValueError("found defects require finding indices; missed/unverified must not have them")
        counts[state] += 1
    if assessment is not None and seen != set(expected):
        raise ValueError("all defect coverage rows required")
    if assessment is None:
        counts["pending"] = len(expected)
    result["defect_coverage"] = {"counts": counts, "total": len(expected), "rows": rows,
                                 "source": "external_semantic_assessment", "automatically_verified": False}
    result["split"] = split
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("validate", "export", "score", "assessment-template"))
    parser.add_argument("path", type=Path, nargs="?")
    parser.add_argument("--split", choices=("development", "control"), default="development")
    parser.add_argument("--assessment", type=Path)
    args = parser.parse_args()
    try:
        if args.assessment and args.action != "score":
            parser.error("--assessment only for score")
        if args.action == "validate":
            result = {c["id"]: verify(c) for c in cases_for(args.split)}
            status = 0 if all(all(r.values()) for r in result.values()) else 1
        else:
            if args.path is None:
                parser.error("path required")
            status = 0
            if args.action == "export":
                export_cases(args.path, cases_for(args.split), version_for(args.split))
                result = {"input_sha256": fingerprint(args.split), "version": version_for(args.split)}
            else:
                answer = json.loads(args.path.read_text())
                result = template(answer, args.split) if args.action == "assessment-template" else score(
                    answer, args.split, json.loads(args.assessment.read_text()) if args.assessment else None)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return status
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"Invalid advanced review: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
