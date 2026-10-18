#!/usr/bin/env python3
"""Export blind review inputs; score classification and rubric structure, not prose truth."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from assessment import assessment_template, summarize_assessment
from corpus import LEGACY_VERSION, VERSION, cases_for, verify_case

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

Используй реальные номера строк и пути относительно каталога работы или корня выдачи
(submission.py либо RV01/submission.py). Для нарушения объясни причину и направление исправления,
не заменяй обратную связь полным решением. Не объявляй стилистическое предпочтение дефектом.
Для неизвестного runtime-результата не придумывай ни успешную проверку, ни доказанный баг.
При дефекте приложенного теста отдельно укажи состояние критерия реализации.

Сохранить ответ в JSON: {"reviews": [объект, ...]}. Укажи отдельно модель, дату и
проводились ли реальные запуски. Полученный балл требует проверки объяснений человеком.
'''


def case_files(case):
    return {"assignment.md": f"# {case['id']} — тема {case['topic']}\n\n{case['assignment']}\n",
            "submission.py": case["code"], **case.get("extra", {})}


def export(destination, version=VERSION):
    return export_cases(destination, cases_for(version), version)


def export_cases(destination, cases, version):
    """Export an explicit dataset without changing the historical RV bundles."""
    if destination.exists() or destination.is_symlink():
        raise ValueError("export requires a new directory")
    destination.mkdir(parents=True, mode=0o700)
    rubric = RUBRIC + f"\nРедакция набора: {version}. Работ: {len(cases)}.\n"
    (destination / "REVIEW.md").write_text(rubric)
    hashes = {"REVIEW.md": hashlib.sha256(rubric.encode()).hexdigest()}
    for case in cases:
        directory = destination / case["id"]
        directory.mkdir()
        content = case_files(case)
        for name, text in content.items():
            (directory / name).write_text(text)
            hashes[case["id"] + "/" + name] = hashlib.sha256(text.encode()).hexdigest()
    (destination / "manifest.json").write_text(json.dumps({"version":version,"sha256":hashes},indent=2))


def score(answer, assessment=None, version=VERSION):
    return score_cases(answer, cases_for(version), version, assessment)


def score_cases(answer, cases, version, assessment=None):
    """Shared grader; corpus selection remains explicit at each CLI boundary."""
    if not isinstance(answer, dict) or not isinstance(answer.get("reviews"), list):
        raise ValueError("expected an object containing reviews array")
    reviews = answer.get("reviews", [])
    if answer.get("benchmark_version", version) != version:
        raise ValueError("answer belongs to a different benchmark version")
    expected = {c["id"]:c for c in cases}
    seen, rows, errors = set(), [], []
    tp = fp = fn = matches = 0
    false_alarms, missed_bugs, false_rejections = [], [], []
    for review in reviews:
        if not isinstance(review,dict) or not isinstance(review.get("criteria"),dict):
            raise ValueError("each review must contain a criteria object")
        if not isinstance(review.get("next_step", ""), str):
            raise ValueError("next_step must be text")
        identity = review.get("case_id")
        if not isinstance(identity, str) or identity not in expected or identity in seen:
            raise ValueError("unknown/duplicate case_id")
        seen.add(identity)
        oracle = expected[identity]
        classification_ok = review.get("classification") in oracle["classes"]
        verdict_ok = review.get("verdict") == oracle["verdict"]
        criterion_ok = review.get("criteria", {}).get("C1") == oracle["criterion"]
        findings = review.get("findings")
        shape_ok = (isinstance(findings,list) and bool(review.get("next_step", "").strip())
                    and review.get("classification") in ("code_defect", "valid", "test_defect", "environment", "new_requirement", "hypothesis")
                    and review.get("verdict") in ("accepted", "needs_changes", "unverified")
                    and set(review["criteria"]) == {"C1"}
                    and review["criteria"].get("C1") in ("confirmed", "error", "unverified"))
        files = case_files(oracle)
        if isinstance(findings,list):
            for finding in findings:
                card_ok = isinstance(finding, dict) and all(
                    isinstance(finding.get(key), str) and finding[key].strip()
                    for key in ("criterion", "file", "explanation", "repro", "direction"))
                filename = finding["file"].removeprefix(identity + "/") if card_ok else ""
                card_ok = (card_ok and finding["criterion"] == "C1"
                           and filename in files and type(finding.get("line")) is int
                           and 0 < finding["line"] <= len(files[filename].splitlines()))
                shape_ok = shape_ok and card_ok
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
        if not expected_bug and claimed_bug:
            false_alarms.append(identity)
        if expected_bug and not claimed_bug:
            missed_bugs.append(identity)
        if oracle["verdict"] == "accepted" and (review.get("verdict") == "needs_changes"
                                                or review["criteria"].get("C1") == "error"):
            false_rejections.append(identity)
        matched = classification_ok and verdict_ok and criterion_ok and shape_ok
        matches += matched
        rows.append({"case_id":identity,"classification_matches":classification_ok,"verdict_matches":verdict_ok,
                     "criterion_matches":criterion_ok,"format_valid":bool(shape_ok),"explanation_verified":False})
    missing = sorted(set(expected) - seen)
    fn += sum(expected[i]["classes"] == ["code_defect"] for i in missing)
    missed_bugs += [identity for identity in missing if expected[identity]["classes"] == ["code_defect"]]
    explanation_assessment = summarize_assessment(assessment, answer, version, set(expected))
    return {"benchmark_version":version,"cases":len(expected),"submitted":len(seen),"missing":missing,"format_errors":errors,
            "rubric_matches":matches,"code_defect_tp":tp,"code_defect_fp":fp,"code_defect_fn":fn,
            "code_defect_precision":tp/(tp+fp) if tp+fp else None,
            "code_defect_recall":tp/(tp+fn) if tp+fn else None,
            "false_code_defect_claims":sorted(false_alarms),"missed_code_defects":sorted(missed_bugs),
            "incorrect_rejections":sorted(false_rejections),
            "explanation_assessment":explanation_assessment,
            "human_review_required":True,"rows":rows,
            "limitation":"Classification/format only. A matching label is not evidence that the explanation or reproduction is true."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("validate", "export", "score", "assessment-template"))
    parser.add_argument("path", type=Path, nargs="?")
    parser.add_argument("--version", choices=(VERSION, LEGACY_VERSION), default=VERSION)
    parser.add_argument("--assessment", type=Path, help="external explanation ratings for score")
    args = parser.parse_args()
    try:
        if args.assessment is not None and args.action != "score":
            parser.error("--assessment is only supported by score")
        if args.action == "validate":
            results = {case["id"]: verify_case(case) for case in cases_for(args.version)}
            print(json.dumps(results,indent=2))
            return 0 if all(results.values()) else 1
        if args.path is None:
            parser.error("path required")
        if args.action == "export":
            export(args.path, args.version)
            print(args.path)
        else:
            answer = json.loads(args.path.read_text())
            assessment = json.loads(args.assessment.read_text()) if args.assessment else None
            result = score(answer, assessment, args.version)
            if args.action == "assessment-template":
                result = assessment_template(answer, args.version)
            print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0
    except (ValueError,OSError,TypeError,KeyError) as exc:
        print(f"Invalid input: {exc}",file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
