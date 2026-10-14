#!/usr/bin/env python3
"""Export isolated exercises; validate records and externally supplied assessments."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from teaching_cases import CASES, VERSION

ROOT = Path(__file__).resolve().parents[2]


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def teacher_profile():
    paths = ["SKILL.md", "references/learning-workspace.md", "references/practice-review.md"]
    texts = {name: (ROOT / name).read_text() for name in paths}
    # Generic instructions only. Exclude author benchmarks and worked examples.
    skill = texts["SKILL.md"]
    review = skill.split("## Проверить выполненную практику\n", 1)[1].split("\n## Учитывать уровень", 1)[0]
    review = review.split("\nПрименять [", 1)[0]
    workspace = texts[paths[1]].split("## HTML как дополнительный формат", 1)[0]
    practice = texts[paths[2]]
    hints = practice.split("## Диагностика затруднения и подсказки\n", 1)[1].split("\n## ", 1)[0]
    profile = "# Профиль преподавателя\n\n## Ревью\n" + review + "\n\n" + workspace + "\n\n## Подсказки\n" + hints
    return profile, {name: hashlib.sha256(text.encode()).hexdigest() for name, text in texts.items()}


def export(destination, identity):
    if identity not in CASES:
        raise ValueError("unknown case_id")
    if destination.exists() or destination.is_symlink():
        raise ValueError("export requires a new directory")
    case = CASES[identity]
    files = dict(case["files"], **{"prompt.txt": case["prompt"] + "\n"})
    sources = {}
    if case["suite"] != "transfer":
        files["TEACHER.md"], sources = teacher_profile()
    files["TASK.md"] = (
        f"# {identity}: {case['suite']}\n\n"
        "Используй только файлы этой выдачи. Не читай исходный репозиторий, авторские рубрики или прошлые ответы.\n"
        "Сохрани дословный ответ отдельно от выдачи. Не изменяй входные файлы.\n"
        "Запиши среду, выполненные команды и фактические результаты в execution; для чтения кода укажи static_only.\n"
        "Формат записи: benchmark_version, case_id, input_sha256 (хеш manifest.json в каноническом JSON),\n"
        "prompt (точный текст без добавленного завершающего перевода строки), response, execution (непустые строки),\n"
        "session: {id, name, date, kind: human/model/self_review, fresh_context: boolean, history_messages: integer}.\n"
        "Для resume нужен отдельный новый контекст, fresh_context=true, history_messages=0; прошлую переписку не передавать.\n"
        "Для resume дополнительно recovered: {part, practice, issues: {ID: open/closed/withdrawn}, next_step};\n"
        "snapshot: {PROGRESS.md: полный текст после ответа, NOTES.md: полный текст после ответа}.\n"
        "Для hints ответь как преподаватель по TEACHER.md; не выдавай решение без просьбы.\n"
        "Для transfer ответь как ученик, без подсказок; ответ агента обязательно обозначь симуляцией.\n"
        "Пути ссылок в TEACHER.md указывают на исходные материалы; отсутствующие здесь файлы не открывай.\n"
        "Никакие облачные/сетевые ресурсы не требуются. Новые агенты запускаются только по разрешению сессии.\n")
    manifest = {"version": VERSION, "case_id": identity, "suite": case["suite"],
                "source_sha256": sources,
                "sha256": {name: hashlib.sha256(text.encode()).hexdigest() for name, text in files.items()}}
    destination.mkdir(parents=True, mode=0o700)
    for name, content in files.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    (destination / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return {"path": str(destination), "input_sha256": digest(manifest), "case_id": identity}


def bundle(path):
    if path.is_symlink() or (path / "manifest.json").is_symlink():
        raise ValueError("symlink bundle unsupported")
    manifest = json.loads((path / "manifest.json").read_text())
    if not isinstance(manifest, dict) or manifest.get("version") != VERSION:
        raise ValueError("wrong bundle version")
    identity = manifest.get("case_id")
    if not isinstance(identity, str) or identity not in CASES:
        raise ValueError("unknown case_id")
    case = CASES[identity]
    expected = set(case["files"]) | {"prompt.txt", "TASK.md"}
    if case["suite"] != "transfer":
        expected.add("TEACHER.md")
    hashes = manifest.get("sha256")
    if manifest.get("suite") != case["suite"] or not isinstance(hashes, dict) or set(hashes) != expected:
        raise ValueError("bundle file allowlist/suite mismatch")
    actual = set()
    for entry in path.rglob("*"):
        if entry.is_symlink():
            raise ValueError("symlink in bundle")
        if entry.is_file():
            actual.add(entry.relative_to(path).as_posix())
    if actual != expected | {"manifest.json"}:
        raise ValueError("extra or missing bundle file")
    for name in expected:
        if hashlib.sha256((path / name).read_bytes()).hexdigest() != hashes[name]:
            raise ValueError("bundle file hash mismatch: " + name)
    for name, content in dict(case["files"], **{"prompt.txt": case["prompt"] + "\n"}).items():
        if (path / name).read_text() != content:
            raise ValueError("scenario differs from declared version")
    return manifest, case


def identify_record(path, record):
    """Bind the original response to its inputs without grading its envelope."""
    manifest, case = bundle(path)
    if (not isinstance(record, dict) or record.get("benchmark_version") != VERSION
            or record.get("case_id") != manifest["case_id"]
            or record.get("input_sha256") != digest(manifest)
            or record.get("prompt") != case["prompt"]):
        raise ValueError("record does not match issued inputs")
    if not nonempty(record.get("response")):
        raise ValueError("verbatim response required")
    return manifest, case


def check(path, record):
    manifest, case = identify_record(path, record)
    if not nonempty(record.get("execution")):
        raise ValueError("verbatim response and execution description required")
    session = record.get("session")
    if (not isinstance(session, dict) or any(not nonempty(session.get(k)) for k in ("id", "name", "date"))
            or session.get("kind") not in ("human", "model", "self_review")
            or type(session.get("fresh_context")) is not bool
            or type(session.get("history_messages")) is not int or session["history_messages"] < 0):
        raise ValueError("complete session provenance required")
    matches = None
    if case["suite"] == "resume":
        if not session["fresh_context"] or session["history_messages"] != 0:
            raise ValueError("resume requires declared new context without prior messages")
        recovered = record.get("recovered")
        if (not isinstance(recovered, dict) or set(recovered) != {"part", "practice", "issues", "next_step"}
                or any(not nonempty(recovered.get(k)) for k in ("part", "practice", "next_step"))
                or not isinstance(recovered["issues"], dict)
                or any(not nonempty(k) or v not in ("open", "closed", "withdrawn") for k, v in recovered["issues"].items())):
            raise ValueError("recovered state required")
        snapshot = record.get("snapshot")
        if (not isinstance(snapshot, dict) or set(snapshot) != {"PROGRESS.md", "NOTES.md"}
                or any(not nonempty(v) for v in snapshot.values())):
            raise ValueError("full nonempty state snapshot required")
        matches = {key: recovered[key] == value for key, value in case["expected"].items()}
    return {"record_complete": True, "case_id": manifest["case_id"], "suite": case["suite"],
            "structured_state_matches": matches, "semantic_assessment_required": True,
            "context_independence": "declared; requires orchestrator/session evidence",
            "limitation": "Matching state fields do not verify response or snapshot meaning. No learning outcome inferred."}


def assessment_template(path, record):
    # Keep semantic assessment available for a real response whose recording
    # format failed check(). The original record remains unchanged and hashed.
    _, case = identify_record(path, record)
    return {"benchmark_version": VERSION, "case_id": record["case_id"], "answer_sha256": digest(record),
            "assessor": {"name": "", "kind": ""},
            "criteria": [{"id": f"K{i}", "criterion": text, "result": "pending", "evidence": ""}
                         for i, text in enumerate(case["rubric"], 1)]}


def check_resume_run(index_path):
    index = json.loads(index_path.read_text())
    if not isinstance(index, dict) or not isinstance(index.get("runs"), list):
        raise ValueError("index requires runs array")
    root, cases, sessions, rows = index_path.parent.resolve(), set(), set(), []
    for entry in index["runs"]:
        if not isinstance(entry, dict) or set(entry) != {"bundle", "answer"}:
            raise ValueError("run entry requires bundle and answer paths")
        paths = {}
        for key, value in entry.items():
            if not nonempty(value) or Path(value).is_absolute():
                raise ValueError("run paths must be relative")
            target = (root / value).resolve()
            if not target.is_relative_to(root):
                raise ValueError("run path escapes index directory")
            paths[key] = target
        record = json.loads(paths["answer"].read_text())
        result = check(paths["bundle"], record)
        identity, session_id = result["case_id"], record["session"]["id"]
        if result["suite"] != "resume" or identity in cases or session_id in sessions:
            raise ValueError("resume cases and context IDs must be distinct")
        cases.add(identity)
        sessions.add(session_id)
        rows.append(result)
    expected = {key for key, case in CASES.items() if case["suite"] == "resume"}
    return {"resume_cases": len(rows), "missing": sorted(expected - cases), "rows": rows,
            "structured_state_matches": all(all(row["structured_state_matches"].values()) for row in rows) and cases == expected,
            "semantic_assessment_required": True,
            "context_independence": "distinct declared IDs only; verify real session evidence separately"}


def assess(path, record, assessment):
    template = assessment_template(path, record)
    if not isinstance(assessment, dict) or any(assessment.get(k) != template[k] for k in ("benchmark_version", "case_id", "answer_sha256")):
        raise ValueError("assessment is bound to another record")
    actor = assessment.get("assessor")
    if not isinstance(actor, dict) or not nonempty(actor.get("name")) or actor.get("kind") not in ("human", "model", "self_review"):
        raise ValueError("assessor name and kind required")
    rows = assessment.get("criteria")
    if not isinstance(rows, list) or len(rows) != len(template["criteria"]):
        raise ValueError("all assessment criteria required")
    for row, expected in zip(rows, template["criteria"]):
        if not isinstance(row, dict) or any(row.get(k) != expected[k] for k in ("id", "criterion")):
            raise ValueError("assessment criterion mismatch")
        if row.get("result") not in ("pending", "confirmed", "error", "unverified"):
            raise ValueError("unknown assessment result")
        if row["result"] == "pending":
            if row.get("evidence") != "":
                raise ValueError("pending criterion must have empty evidence")
        elif not nonempty(row.get("evidence")):
            raise ValueError("assessed criterion needs concrete response/snapshot evidence")
    return {"case_id": record["case_id"], "assessor": actor,
            "counts": {s: sum(r["result"] == s for r in rows) for s in ("pending", "confirmed", "error", "unverified")},
            "criteria": rows, "automated_semantic_verification": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("list", "export", "check", "check-resume-run", "assessment-template", "assess"))
    parser.add_argument("path", type=Path, nargs="?")
    parser.add_argument("answer", type=Path, nargs="?")
    parser.add_argument("--case")
    parser.add_argument("--assessment", type=Path)
    args = parser.parse_args()
    try:
        if args.case and args.action != "export":
            parser.error("--case only for export")
        if args.assessment and args.action != "assess":
            parser.error("--assessment only for assess")
        if args.action == "list":
            result = [{"id": key, "suite": value["suite"], "topic": value["topic"]} for key, value in CASES.items()]
        else:
            if args.path is None:
                parser.error("bundle path required")
            if args.action == "check-resume-run":
                result = check_resume_run(args.path)
            elif args.action == "export":
                if args.case is None:
                    parser.error("--case required")
                result = export(args.path, args.case)
            else:
                if args.answer is None:
                    parser.error("answer path required")
                answer = json.loads(args.answer.read_text())
                if args.action == "check":
                    result = check(args.path, answer)
                elif args.action == "assessment-template":
                    result = assessment_template(args.path, answer)
                else:
                    if args.assessment is None:
                        parser.error("--assessment required")
                    result = assess(args.path, answer, json.loads(args.assessment.read_text()))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        matches = result.get("structured_state_matches") if isinstance(result, dict) else None
        if matches is False or isinstance(matches, dict) and not all(matches.values()):
            return 1
        return 0
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(f"Invalid input: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
