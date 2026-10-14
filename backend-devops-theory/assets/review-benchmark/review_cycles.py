#!/usr/bin/env python3
"""Export sequential review turns and check recorded state, not the truth of prose."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

from assessment import answer_digest, assessment_template, summarize_assessment
from cycle_corpus import CYCLES, VERSION, validate


REVIEW = """# Повторное ревью учебной практики

Работай по assignment.md, текущему submission.py и prompt.txt. Сохраняй историю
замечаний из initial-history.json и history.json. Следующую сдачу ведущий выдаст
после записи твоего ответа. Не читай авторский корпус, ключи или будущие сдачи.

Проверь все объявленные критерии и затронутые прежние сценарии. При частичном
исправлении различай закрытое и оставшееся открытым. Новый дефект — отдельное
замечание. Обоснованное возражение ученика требует пересмотра исходного вывода.
Сохраняй ID замечаний: open — дефект остаётся; closed — исправлен в коде;
withdrawn — замечание снято как ошибочное. Не удаляй историю и не используй
снятый ID для другого дефекта. Объясняй основания и следующее действие,
сохраняя самостоятельность ученика. Не добавляй скрытых условий к v1.

Верни дословный ответ в response и структурированное состояние в review:
criteria — статус каждого критерия (confirmed/error/unverified);
verdict — accepted/needs_changes/unverified;
issues — вся история {id, criterion, status, reason}; next_step — действие.
snapshot содержит полный текст PROGRESS.md и NOTES.md отдельного синтетического
ученика после этого хода. Не изменяй настоящее learning/.

Заполни только последний ход answer-template.json; предыдущие записи и их
порядок сохраняй. Укажи reviewer.name, date, kind (human/model/self_review).
Если это модель, укажи известную версию, не выдумывай недоступную информацию.
Отделяй собственный запуск от чтения кода. Сохрани ответ вне каталога выдачи.
Автоматическая проверка структуры и статусов не оценивает смысл объяснения.
"""


def cycle_and_step(identity, turn):
    if (not isinstance(identity, str) or identity not in CYCLES
            or type(turn) is not int or not 1 <= turn <= len(CYCLES[identity]["steps"])):
        raise ValueError("unknown cycle or turn")
    return CYCLES[identity], CYCLES[identity]["steps"][turn - 1]


def input_files(identity, turn):
    cycle, step = cycle_and_step(identity, turn)
    return {"REVIEW.md": REVIEW,
            "assignment.md": f"# {identity}, тема {cycle['topic']}\n\n{cycle['assignment']}\n",
            "submission.py": step["code"], "prompt.txt": step["prompt"] + "\n",
            "initial-history.json": json.dumps({"history": cycle["initial_history"],
                                               "issues": cycle["initial_issues"]}, ensure_ascii=False, indent=2) + "\n"}


def input_hashes(identity, turn):
    return {name: hashlib.sha256(text.encode()).hexdigest() for name, text in input_files(identity, turn).items()}


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def validate_transcript(transcript):
    if not isinstance(transcript, dict) or transcript.get("benchmark_version") != VERSION:
        raise ValueError("wrong transcript version")
    identity = transcript.get("cycle_id")
    if not isinstance(identity, str) or identity not in CYCLES:
        raise ValueError("unknown cycle_id")
    cycle = CYCLES[identity]
    reviewer = transcript.get("reviewer")
    if (not isinstance(reviewer, dict) or not nonempty(reviewer.get("name"))
            or not nonempty(reviewer.get("date"))
            or reviewer.get("kind") not in ("human", "model", "self_review")):
        raise ValueError("reviewer requires name, date and kind")
    turns = transcript.get("turns")
    if not isinstance(turns, list) or not 1 <= len(turns) <= len(cycle["steps"]):
        raise ValueError("expected a nonempty sequential turns array")
    previous = None
    for number, entry in enumerate(turns, 1):
        if not isinstance(entry, dict) or type(entry.get("turn")) is not int or entry["turn"] != number:
            raise ValueError("missing, duplicate or reordered turn")
        if entry.get("input_sha256") != input_hashes(identity, number):
            raise ValueError(f"assignment/submission/prompt mismatch at turn {number}")
        if entry.get("previous_sha256") != previous:
            raise ValueError(f"earlier response or snapshot changed before turn {number}")
        if entry.get("prompt") != cycle["steps"][number - 1]["prompt"] or not nonempty(entry.get("response")):
            raise ValueError(f"wrong prompt or empty response at turn {number}")
        snapshot = entry.get("snapshot")
        if (not isinstance(snapshot, dict) or set(snapshot) != {"PROGRESS.md", "NOTES.md"}
                or not all(nonempty(value) for value in snapshot.values())):
            raise ValueError(f"incomplete state snapshot at turn {number}")
        review = entry.get("review")
        if not isinstance(review, dict) or not isinstance(review.get("criteria"), dict):
            raise ValueError("review requires criteria object")
        if (set(review["criteria"]) != set(cycle["criteria"])
                or any(value not in ("confirmed", "error", "unverified") for value in review["criteria"].values())):
            raise ValueError("criteria must match the original assignment")
        if review.get("verdict") not in ("accepted", "needs_changes", "unverified") or not nonempty(review.get("next_step")):
            raise ValueError("review requires verdict and next_step")
        issues = review.get("issues")
        if not isinstance(issues, list):
            raise ValueError("issues must be an array")
        seen = set()
        for issue in issues:
            if (not isinstance(issue, dict) or not nonempty(issue.get("id"))
                    or issue["id"] in seen or issue.get("criterion") not in cycle["criteria"]
                    or issue.get("status") not in ("open", "closed", "withdrawn")
                    or not nonempty(issue.get("reason"))):
                raise ValueError("invalid or duplicate issue")
            seen.add(issue["id"])
        previous = answer_digest(entry)
    return cycle


def export(destination, identity, turn=1, history=None):
    cycle, step = cycle_and_step(identity, turn)
    if turn == 1:
        if history is not None:
            raise ValueError("first turn cannot have an earlier transcript")
        transcript = {"benchmark_version": VERSION, "cycle_id": identity,
                      "reviewer": {"name": "", "date": "", "kind": ""}, "turns": []}
    else:
        validate_transcript(history)
        if history["cycle_id"] != identity or len(history["turns"]) != turn - 1:
            raise ValueError("next turn requires exactly the preceding recorded turns")
        transcript = deepcopy(history)
    if destination.exists() or destination.is_symlink():
        raise ValueError("export requires a new directory")
    files = input_files(identity, turn)
    files["history.json"] = json.dumps(history, ensure_ascii=False, indent=2) + "\n"
    previous = answer_digest(transcript["turns"][-1]) if transcript["turns"] else None
    transcript["turns"].append({"turn": turn, "prompt": step["prompt"],
                                "input_sha256": input_hashes(identity, turn), "previous_sha256": previous,
                                "response": "", "review": {"criteria": dict.fromkeys(cycle["criteria"], "unverified"),
                                "verdict": "unverified", "issues": [], "next_step": ""},
                                "snapshot": {"PROGRESS.md": "", "NOTES.md": ""}})
    files["answer-template.json"] = json.dumps(transcript, ensure_ascii=False, indent=2) + "\n"
    destination.mkdir(parents=True, mode=0o700)
    for name, content in files.items():
        (destination / name).write_text(content, encoding="utf-8")
    manifest = {"benchmark_version": VERSION, "cycle_id": identity, "turn": turn,
                "sha256": {name: hashlib.sha256(content.encode()).hexdigest() for name, content in files.items()}}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def check(transcript):
    cycle = validate_transcript(transcript)
    return {"structurally_valid": True, "transcript_complete": len(transcript["turns"]) == len(cycle["steps"]),
            "recorded_turns": len(transcript["turns"]), "expected_turns": len(cycle["steps"]),
            "turn_sha256": [answer_digest(entry) for entry in transcript["turns"]],
            "semantic_assessment_required": True}


def assessment_answer(transcript):
    validate_transcript(transcript)
    return {"benchmark_version": VERSION, "cycle_id": transcript["cycle_id"], "reviewer": transcript["reviewer"],
            "reviews": [{"case_id": f"{transcript['cycle_id']}:{entry['turn']:02}", **entry}
                        for entry in transcript["turns"]]}


def score(transcript, assessment=None):
    result = check(transcript)
    identity = transcript["cycle_id"]
    cycle = CYCLES[identity]
    previous = {issue["id"]: issue for issue in cycle["initial_issues"]}
    previous_criteria = None
    rows, premature, regressions, lost = [], [], [], []
    for entry in transcript["turns"]:
        number = entry["turn"]
        expected = cycle["steps"][number - 1]
        review = entry["review"]
        current = {issue["id"]: issue for issue in review["issues"]}
        states = {}
        for issue in current.values():
            states.setdefault(issue["criterion"], []).append(issue["status"])
        states = {key: sorted(value) for key, value in states.items()}
        expected_states = {key: sorted(value) for key, value in expected["issues"].items()}
        missing_ids = sorted(set(previous) - set(current))
        reused_ids = sorted(key for key in previous.keys() & current.keys()
                            if previous[key]["criterion"] != current[key]["criterion"])
        altered_withdrawals = sorted(key for key in previous.keys() & current.keys()
                                     if previous[key]["status"] == "withdrawn" and current[key]["status"] != "withdrawn")
        for key in missing_ids:
            lost.append({"turn": number, "issue_id": key})
        if review["verdict"] == "accepted" and expected["verdict"] != "accepted":
            premature.append(number)
        if previous_criteria is not None:
            for criterion, status in expected["expected"].items():
                if (previous_criteria[criterion] == "confirmed" and status == "error"
                        and review["criteria"][criterion] != "error"):
                    regressions.append({"turn": number, "criterion": criterion})
        matches = {"criteria_match": review["criteria"] == expected["expected"],
                   "verdict_matches": review["verdict"] == expected["verdict"],
                   "issue_states_match": states == expected_states,
                   "issue_history_preserved": not (missing_ids or reused_ids or altered_withdrawals)}
        rows.append({"turn": number, **matches, "matches": all(matches.values()),
                     "missing_issue_ids": missing_ids, "reused_issue_ids": reused_ids,
                     "altered_withdrawals": altered_withdrawals, "explanation_verified": False})
        previous = current
        previous_criteria = expected["expected"]
    expected_ids = {f"{identity}:{turn:02}" for turn in range(1, len(cycle["steps"]) + 1)}
    result.update(benchmark_version=VERSION, cycle_id=identity, rows=rows,
                  matched_turns=sum(row["matches"] for row in rows),
                  structured_cycle_matches=result["transcript_complete"] and all(row["matches"] for row in rows),
                  premature_acceptances=premature, missed_regressions=regressions, lost_issue_ids=lost,
                  explanation_assessment=summarize_assessment(assessment, assessment_answer(transcript), VERSION, expected_ids),
                  limitation="Recorded state and labels only. Agreement with prose, evidence, acknowledgement of a wrong review and usefulness require external assessment.")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("validate", "export", "check", "score", "assessment-template"))
    parser.add_argument("path", nargs="?", type=Path)
    parser.add_argument("--cycle", choices=tuple(CYCLES))
    parser.add_argument("--turn", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--history", type=Path)
    parser.add_argument("--assessment", type=Path)
    args = parser.parse_args()
    try:
        if args.assessment and args.action != "score":
            parser.error("--assessment is only supported by score")
        if args.action != "export" and (args.cycle or args.history or args.turn != 1):
            parser.error("--cycle/--turn/--history are only supported by export")
        if args.action == "validate":
            report = validate()
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if all(row["matches"] for rows in report.values() for row in rows) else 1
        if args.path is None:
            parser.error("path required")
        if args.action == "export":
            if args.cycle is None:
                parser.error("--cycle required")
            history = json.loads(args.history.read_text()) if args.history else None
            export(args.path, args.cycle, args.turn, history)
            print(args.path)
            return 0
        transcript = json.loads(args.path.read_text())
        if args.action == "assessment-template":
            report = assessment_template(assessment_answer(transcript), VERSION)
            passed = True
        elif args.action == "check":
            report = check(transcript)
            passed = report["transcript_complete"]
        else:
            assessment = json.loads(args.assessment.read_text()) if args.assessment else None
            report = score(transcript, assessment)
            passed = report["structured_cycle_matches"]
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if passed else 1
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(f"Invalid input: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
