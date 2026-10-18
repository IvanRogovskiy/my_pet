#!/usr/bin/env python3
"""Blind second ratings of frozen reviews; compare without replacing old scores."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from assessment import DIMENSIONS, answer_digest, summarize_assessment


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def export(spec_path, destination):
    if destination.exists() or destination.is_symlink():
        raise ValueError("export requires a new directory")
    spec = read(spec_path)
    selected = spec["selection"]
    if not selected:
        raise ValueError("nonempty preregistered selection required")
    items, mapping, seen = [], [], set()
    for number, entry in enumerate(selected, 1):
        paths = {k: (spec_path.parent / entry[k]).resolve() for k in ("answer", "assessment", "inputs")}
        answer = read(paths["answer"])
        old = read(paths["assessment"])
        identity = entry["case_id"]
        source = (str(paths["answer"]), identity)
        if source in seen:
            raise ValueError("duplicate source review")
        seen.add(source)
        summary = summarize_assessment(old, answer, answer["benchmark_version"],
                                       {r["case_id"] for r in answer["reviews"]})
        original = next(r for r in answer["reviews"] if r["case_id"] == identity)
        previous = next(r for r in summary["rows"] if r["case_id"] == identity)
        alias = f"P{number:02}"
        # No original IDs, model/profile names, source hashes or previous scores.
        def anonymous(text):
            text = text.replace(identity, alias)
            return re.sub(r"\b(?:RV|HC)\d{2}\b", "[other-case]", text)
        files = {}
        for path in sorted(paths["inputs"].rglob("*")):
            if path.is_symlink():
                raise ValueError("symlink input")
            if path.is_file() and "__pycache__" not in path.parts:
                files[path.relative_to(paths["inputs"]).as_posix()] = anonymous(path.read_text())
        review = json.loads(anonymous(json.dumps(original, ensure_ascii=False)))
        review["case_id"] = alias
        items.append({"id": alias, "files": files, "review": review,
                      "execution": anonymous(answer.get("execution", "Execution not recorded"))})
        mapping.append({"id": alias, "case_id": identity, "source": entry,
                        "answer_sha256": answer_digest(answer),
                        "assessment_sha256": answer_digest(old),
                        "review_sha256": answer_digest(original), "previous": previous})
    rubric = Path(__file__).with_name("ASSESSMENT.md").read_text()
    rubric = rubric.split("## Примеры разграничения")[0]
    rubric = rubric.replace("и авторское основание", "без авторского ключа и прежних оценок")
    payload = {"version": "calibration-2026-10-17.1", "rubric": rubric, "items": items}
    destination.mkdir(parents=True)
    (destination / "input").mkdir()
    write(destination / "input/bundle.json", payload)
    template = {"bundle_sha256": answer_digest(payload),
                "assessor": {"name": "", "kind": "model", "session_id": "", "fresh_context": True},
                "reviews": [{"id": row["id"], "ratings": dict.fromkeys(DIMENSIONS),
                             "notes": dict.fromkeys(DIMENSIONS, "")} for row in items]}
    write(destination / "input/ratings.example.json", template)
    (destination / "input/TASK.md").write_text(
        "# Независимая повторная оценка\n\n"
        "Читай только эту выдачу. Прежние оценки и названия профилей не предоставлены. "
        "Оцени каждый отзыв по четырём шкалам bundle.json с отдельным основанием. "
        "Сохрани первую запись, не меняя входы. ratings.example.json показывает форму.\n\n"
        "bundle_sha256 — SHA256 канонического JSON bundle.json: json.dumps(value, "
        "ensure_ascii=False, sort_keys=True, separators=(',', ':')). Это не хеш сырых байтов. "
        "session_id — реальный ID нового контекста; неизвестную версию модели не выдумывай.\n")
    write(destination / "mapping.json", {"bundle_sha256": answer_digest(payload), "rows": mapping})
    return {"reviews": len(items), "bundle_sha256": answer_digest(payload)}


def compare(payload, mapping, ratings, raw_bundle=None):
    fingerprint = answer_digest(payload)
    binding = "canonical_json"
    recorded = ratings.get("bundle_sha256")
    if recorded != fingerprint and raw_bundle is not None:
        # Accept byte-level binding only to the same exact payload. No rewriting
        # of the first rating record or trust in a caller-supplied hash string.
        if json.loads(raw_bundle) != payload or hashlib.sha256(raw_bundle).hexdigest() != recorded:
            raise ValueError("byte binding differs from issued inputs")
        binding = "file_bytes"
    elif recorded != fingerprint:
        raise ValueError("ratings bound to different inputs")
    if mapping.get("bundle_sha256") != fingerprint:
        raise ValueError("ratings/mapping bound to different inputs")
    actor = ratings.get("assessor", {})
    if (actor.get("kind") not in ("human", "model") or actor.get("fresh_context") is not True
            or any(not isinstance(actor.get(k), str) or not actor[k].strip() for k in ("name", "session_id"))):
        raise ValueError("independent assessor provenance required")
    expected = {item["id"] for item in payload["items"]}
    if not expected or len(expected) != len(payload["items"]):
        raise ValueError("nonempty unique input items required")
    prior = {row["id"]: row["previous"] for row in mapping["rows"]}
    if set(prior) != expected or len(prior) != len(mapping["rows"]):
        raise ValueError("mapping coverage mismatch")
    rows, seen = [], set()
    for review in ratings.get("reviews", []):
        identity = review.get("id")
        if identity not in expected or identity in seen:
            raise ValueError("unknown/duplicate review")
        seen.add(identity)
        scores, notes = review.get("ratings"), review.get("notes")
        if (not isinstance(scores, dict) or set(scores) != set(DIMENSIONS)
                or any(type(x) is not int or not 0 <= x <= 2 for x in scores.values())
                or not isinstance(notes, dict) or set(notes) != set(DIMENSIONS)
                or any(not isinstance(x, str) or not x.strip() for x in notes.values())):
            raise ValueError("all four integer ratings and evidence notes required")
        for dimension in DIMENSIONS:
            before = prior[identity]["ratings"][dimension]
            after = scores[dimension]
            rows.append({"id": identity, "dimension": dimension, "previous": before,
                         "second": after, "delta": after - before,
                         "previous_note": prior[identity]["notes"][dimension], "second_note": notes[dimension]})
    if seen != expected:
        raise ValueError("complete selected coverage required")
    return {"bundle_sha256": fingerprint, "rating_hash_kind": binding,
            "rating_record_sha256": answer_digest(ratings), "assessor": actor, "reviews": len(seen),
            "ratings": len(rows), "exact_agreement": sum(r["delta"] == 0 for r in rows),
            "by_dimension": {key: {
                "previous_mean": sum(r["previous"] for r in rows if r["dimension"] == key) / len(seen),
                "second_mean": sum(r["second"] for r in rows if r["dimension"] == key) / len(seen),
                "mean_absolute_difference": sum(abs(r["delta"]) for r in rows if r["dimension"] == key) / len(seen),
            } for key in DIMENSIONS},
            "disagreements": [r for r in rows if r["delta"]], "rows": rows,
            "limitation": "Second model judgment, not human truth; isolation is declared. Historical ratings unchanged."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    exp = sub.add_parser("export")
    exp.add_argument("spec", type=Path)
    exp.add_argument("destination", type=Path)
    comp = sub.add_parser("compare")
    comp.add_argument("directory", type=Path)
    comp.add_argument("ratings", type=Path)
    args = parser.parse_args()
    try:
        result = export(args.spec, args.destination) if args.action == "export" else compare(
            read(args.directory / "input/bundle.json"), read(args.directory / "mapping.json"), read(args.ratings),
            (args.directory / "input/bundle.json").read_bytes())
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError, StopIteration) as exc:
        print(f"Invalid calibration: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
