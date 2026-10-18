"""Versioned author fixtures. Never give these rubrics to the teacher."""
from copy import deepcopy
from teaching_cases_v1 import CASES as LEGACY_CASES, VERSION as LEGACY_VERSION

VERSION = "teaching-2026-10-14.2"
CASES = deepcopy(LEGACY_CASES)
# Measure analysis of a race schedule, including a scaffold supplied by the
# teacher. Construction without scaffolding is a different learning objective.
CASES["HS02"]["rubric"][2] = (
    "Одно диагностическое действие: ученик объясняет значения чтений или исход "
    "проверок в расписании; расписание может быть дано преподавателем. "
    "Преподаватель не отвечает за ученика на свой диагностический вопрос."
)
VERSIONS = {LEGACY_VERSION: LEGACY_CASES, VERSION: CASES}


def cases_for(version):
    if version not in VERSIONS:
        raise ValueError("unknown teaching benchmark version")
    return VERSIONS[version]
