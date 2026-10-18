#!/usr/bin/env python3
"""Course CI entrypoint: fast checks, Linux runtime, and immutable evidence."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_IDS = {
    "test_labs.Labs.test_loopback_bad_fixed_and_cleanup",
    "test_labs.Labs.test_release_fixture_writes_only_on_post",
    "test_labs.Labs.test_permissions_can_be_rechecked_after_read_only_fixture",
}
EVIDENCE = ("teaching-reliability-2026-10-14", "course-hardening-2026-10-17")


def flatten(suite):
    for child in suite:
        if isinstance(child, unittest.TestSuite):
            yield from flatten(child)
        else:
            yield child


def is_runtime(test):
    return test.id() in RUNTIME_IDS or test.id().startswith("test_course_revision.TLSFixture.")


def run_tests(mode):
    if mode == "runtime" and (sys.platform != "linux" or os.geteuid() == 0):
        raise ValueError("runtime checks require an unprivileged Linux user")
    all_tests = list(flatten(unittest.defaultTestLoader.discover(str(ROOT / "backend-devops-theory/tests"))))
    selected = [t for t in all_tests if is_runtime(t) == (mode == "runtime") or isinstance(t, unittest.loader._FailedTest)]
    if not selected:
        raise ValueError("empty test selection")
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(selected))
    print(json.dumps({"mode": mode, "selected": len(selected), "discovered": len(all_tests),
                      "skipped": len(result.skipped), "successful": result.wasSuccessful()}))
    # A missing optional TLS dependency must not turn runtime CI green.
    return 0 if result.wasSuccessful() and not result.skipped else 1


def verify_manifest(directory):
    if directory.is_symlink() or (directory / "manifest.json").is_symlink():
        raise ValueError("symlink evidence root/manifest")
    manifest = json.loads((directory / "manifest.json").read_text())
    hashes = manifest["sha256"]
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError("nonempty sha256 manifest required")
    for name, expected in hashes.items():
        relative = Path(name)
        target = directory / relative
        if relative.is_absolute() or ".." in relative.parts or any(
                (directory / Path(*relative.parts[:i])).is_symlink() for i in range(1, len(relative.parts) + 1)):
            raise ValueError("unsafe manifest path: " + name)
        if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            raise ValueError("evidence changed: " + str(target))
    entries = list(directory.rglob("*"))
    if any(p.is_symlink() for p in entries):
        raise ValueError("symlink in evidence directory")
    actual = {p.relative_to(directory).as_posix() for p in entries
              if p.is_file() and p.name != ".DS_Store" and "__pycache__" not in p.parts
              and p.suffix not in (".pyc", ".pyo") and p != directory / "manifest.json"}
    if actual != set(hashes):
        raise ValueError("evidence file set changed: " + str(sorted(actual ^ set(hashes))))
    return len(hashes)


def legacy_compatibility():
    sys.path.insert(0, str(ROOT / "backend-devops-theory/assets/teaching-benchmark"))
    import teaching
    legacy = ROOT / "docs/teaching-evaluation-2026-10-14"
    counts = {"format_rejected": 0, "confirmed": 0, "unverified": 0}
    for case in ("RS01", "RS02", "RS03", "HS01", "HS02", "HS03"):
        directory = legacy / "outputs" / case
        answer = json.loads((directory / "answer.json").read_text())
        try:
            teaching.check(legacy / "inputs" / case, answer)
        except ValueError:
            counts["format_rejected"] += 1
        report = teaching.assess(legacy / "inputs" / case, answer,
                                 json.loads((directory / "semantic-assessment.json").read_text()))
        for key in ("confirmed", "unverified"):
            counts[key] += report["counts"][key]
    if counts != {"format_rejected": 6, "confirmed": 23, "unverified": 1}:
        raise ValueError("historical .1 judgments changed: " + str(counts))
    repeats = ROOT / "docs/teaching-reliability-2026-10-14/repeats"
    passed = 0
    for directory in sorted(repeats.iterdir()):
        if not directory.is_dir():
            continue
        answer = json.loads((directory / "output/answer.json").read_text())
        report = teaching.check(directory / "input", answer)
        matches = report["structured_state_matches"]
        if matches is not None and not all(matches.values()):
            raise ValueError("historical .2 state result changed")
        assessment = teaching.assess(directory / "input", answer,
                                     json.loads((directory / "semantic-assessment.json").read_text()))
        if assessment["counts"] != {"pending": 0, "confirmed": 4, "error": 0, "unverified": 0}:
            raise ValueError("historical .2 semantic record changed")
        passed += 1
    if passed != 18:
        raise ValueError("historical .2 run coverage changed")
    return {"legacy_v1": counts, "legacy_v2_records": passed}


def evidence():
    result = {name: verify_manifest(ROOT / "docs" / name) for name in EVIDENCE}
    result["compatibility"] = legacy_compatibility()
    for name in EVIDENCE:
        command = [sys.executable, str(ROOT / "docs" / name / "reproduce.py")]
        run = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=90,
                             env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        if run.returncode:
            raise ValueError(f"reproduction failed: {name}\n{run.stderr[-3000:]}")
        json.loads(run.stdout)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("fast", "runtime", "evidence"))
    args = parser.parse_args()
    try:
        return evidence() if args.mode == "evidence" else run_tests(args.mode)
    except (ValueError, OSError, KeyError, subprocess.TimeoutExpired) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
