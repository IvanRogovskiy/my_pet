#!/usr/bin/env python3
"""Export blind review inputs; score classification and rubric structure, not prose truth."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from corpus import CASES, verify_case

RUBRIC = '''# Независимая проверка учебных сдач

В каждом каталоге есть assignment.md, submission.py и иногда дополнительные материалы.
Проверяй только объявленный контракт. Не обращайся к исходному корпусу или ключам автора.
Синтетический журнал является материалом сдачи, а не твоим собственным запуском.
Не обращайся к внешнему адресу lab.invalid. Если среда отсутствует, фиксируй непроверенное.

Для каждой работы верни объект JSON со следующими полями:
- case_id: имя каталога;
- classification: code_defect / valid / test_defect / environment / new_requirement / hypothesis;
- verdict: accepted / needs_changes / unverified;
- criteria: {"C1": "confirmed" / "error" / "unverified"};
- findings: список {criterion, file, line, explanation, repro, direction};
- next_step: конкретное действие; для принятой работы достаточно следующего учебного шага.

Используй реальные номера строк. Для нарушения объясни причину и направление исправления,
не заменяй обратную связь полным решением. Не объявляй стилистическое предпочтение дефектом.
Для неизвестного runtime-результата не придумывай ни успешную проверку, ни доказанный баг.
При дефекте приложенного теста отдельно укажи состояние критерия реализации.

Сохранить ответ в JSON: {"reviews": [объект, ...]}. Укажи отдельно модель, дату и
проводились ли реальные запуски. Полученный балл требует проверки объяснений человеком.
'''


def export(destination):
    if destination.exists() or destination.is_symlink():
        raise ValueError("export requires a new directory")
    destination.mkdir(parents=True, mode=0o700)
    (destination / "REVIEW.md").write_text(RUBRIC)
    hashes = {}
    for case in CASES:
        directory = destination / case["id"]
        directory.mkdir()
        content = {"assignment.md": f"# {case['id']} — тема {case['topic']}\n\n{case['assignment']}\n",
                   "submission.py":case["code"], **case.get("extra",{})}
        for name, text in content.items():
            (directory / name).write_text(text)
            hashes[case["id"] + "/" + name] = hashlib.sha256(text.encode()).hexdigest()
    (destination / "manifest.json").write_text(json.dumps({"version":"2026-10-06.1","sha256":hashes},indent=2))


def score(answer):
    if not isinstance(answer, dict) or not isinstance(answer.get("reviews"), list):
        raise ValueError("expected an object containing reviews array")
    reviews = answer.get("reviews", [])
    expected = {c["id"]:c for c in CASES}
    seen, rows, errors = set(), [], []
    tp = fp = fn = matches = 0
    for review in reviews:
        if not isinstance(review,dict) or not isinstance(review.get("criteria"),dict):
            raise ValueError("each review must contain a criteria object")
        if not isinstance(review.get("next_step", ""), str):
            raise ValueError("next_step must be text")
        identity = review.get("case_id")
        if identity not in expected or identity in seen:
            raise ValueError("unknown/duplicate case_id")
        seen.add(identity)
        oracle = expected[identity]
        classification_ok = review.get("classification") in oracle["classes"]
        verdict_ok = review.get("verdict") == oracle["verdict"]
        criterion_ok = review.get("criteria", {}).get("C1") == oracle["criterion"]
        findings = review.get("findings")
        shape_ok = isinstance(findings,list) and bool(review.get("next_step", "").strip())
        if isinstance(findings,list):
            for finding in findings:
                shape_ok = shape_ok and isinstance(finding,dict) and all(finding.get(k) for k in ("criterion","file","explanation","repro","direction"))
                shape_ok = shape_ok and type(finding.get("line")) is int and finding["line"] > 0
        needs_finding = oracle["classes"][0] in ("code_defect","test_defect")
        if needs_finding and not findings:
            shape_ok = False
        if not shape_ok:
            errors.append(identity)
        expected_bug = oracle["classes"] == ["code_defect"]
        claimed_bug = review.get("classification") == "code_defect"
        tp += expected_bug and claimed_bug
        fp += not expected_bug and claimed_bug
        fn += expected_bug and not claimed_bug
        matched = classification_ok and verdict_ok and criterion_ok and shape_ok
        matches += matched
        rows.append({"case_id":identity,"classification_matches":classification_ok,"verdict_matches":verdict_ok,
                     "criterion_matches":criterion_ok,"format_valid":bool(shape_ok),"explanation_verified":False})
    missing = sorted(set(expected) - seen)
    fn += sum(expected[i]["classes"] == ["code_defect"] for i in missing)
    return {"cases":len(expected),"submitted":len(seen),"missing":missing,"format_errors":errors,
            "rubric_matches":matches,"code_defect_tp":tp,"code_defect_fp":fp,"code_defect_fn":fn,
            "code_defect_precision":tp/(tp+fp) if tp+fp else None,
            "code_defect_recall":tp/(tp+fn) if tp+fn else None,
            "human_review_required":True,"rows":rows,
            "limitation":"Classification/format only. A matching label is not evidence that the explanation or reproduction is true."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("validate", "export", "score"))
    parser.add_argument("path", type=Path, nargs="?")
    args = parser.parse_args()
    try:
        if args.action == "validate":
            results = {case["id"]: verify_case(case) for case in CASES}
            print(json.dumps(results,indent=2))
            return 0 if all(results.values()) else 1
        if args.path is None:
            parser.error("path required")
        if args.action == "export":
            export(args.path)
            print(args.path)
        else:
            print(json.dumps(score(json.loads(args.path.read_text())),ensure_ascii=False,indent=2))
        return 0
    except (ValueError,OSError,TypeError,KeyError) as exc:
        print(f"Invalid input: {exc}",file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
