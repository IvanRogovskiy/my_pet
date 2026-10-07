#!/usr/bin/env python3
"""Owned, local-only course fixtures. No downloads, cloud creation or global cleanup."""
import argparse
import contextlib
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid

from catalog import CASES, VERSION, dump, files

if __name__ == "__main__":
    sys.modules["lab"] = sys.modules[__name__]

MARKER = ".orderflow-lab.json"
RUNNER_REVISION = "2026-10-06.2"


class Unavailable(RuntimeError):
    pass


def command(args, cwd=None, env=None, timeout=30):
    try:
        result = subprocess.run([str(x) for x in args], cwd=cwd, env=env,
                                capture_output=True, text=True, timeout=timeout)
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired) as exc:
        raise Unavailable(f"{args[0]}: {type(exc).__name__}") from exc
    return {"exit": result.returncode, "stdout": result.stdout[-12000:], "stderr": result.stderr[-12000:]}


def must(args, **kwargs):
    r = command(args, **kwargs)
    if r["exit"]:
        raise Unavailable(f"{args[0]} failed: {r['stderr'][-1500:] or r['stdout'][-1500:]}")
    return r


def beneath(root, relative):
    candidate = root / relative
    if candidate.is_symlink() or root not in candidate.resolve().parents:
        raise ValueError(f"unsafe path: {relative}")
    if candidate.is_file() and candidate.stat().st_nlink != 1:
        raise ValueError(f"hard-linked file refused: {relative}")
    current = candidate.parent
    while current != root:
        if current.is_symlink():
            raise ValueError(f"symlink parent: {relative}")
        current = current.parent
    return candidate


def write(root, relative, text):
    path = beneath(root, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def load(path):
    if path.is_symlink():
        raise ValueError("lab root must not be a symlink")
    root = path.resolve()
    if any(part in {".git", ".agents", ".codex", ".aws"} for part in root.parts):
        raise ValueError("lab cannot be created inside a protected configuration directory")
    marker = beneath(root, MARKER)
    state = json.loads(marker.read_text())
    if state.get("root") != str(root) or state.get("version") != VERSION:
        raise ValueError("root/version mismatch; use original owned workspace")
    if not re.fullmatch(r"[0-9a-f]{32}", state.get("id", "")) or state.get("case") not in CASES:
        raise ValueError("invalid ownership marker")
    for name in ("work", "data", "evidence"):
        beneath(root, name)
    return root, state


def prepare(path, case, reference=False):
    if case not in CASES:
        raise ValueError("unknown case")
    if path.exists() or path.is_symlink():
        raise ValueError("prepare requires a new directory; existing content is never adopted")
    # Resolve parent first; a symlink *root* is still rejected by load.
    root = path.resolve()
    if any(part in {".git", ".agents", ".codex", ".aws"} for part in root.parts):
        raise ValueError("lab cannot be created inside a protected configuration directory")
    root.mkdir(parents=True, mode=0o700)
    state = {"version": VERSION, "root": str(root), "case": case, "id": uuid.uuid4().hex}
    write(root, MARKER, dump(state))
    for name in ("work", "data", "evidence"):
        beneath(root, name).mkdir(mode=0o700)
    write(root, "data/identity.txt", state["id"])
    topic, backend, task = CASES[case]
    write(root, "ASSIGNMENT.md", f"# {case} — {topic}\n\n{task}\n\nСреда: {backend}. Версия: {VERSION}.\n"
          "Изменяй файлы work/. Сдай diff, объяснение и evidence/*.json.\n"
          "Exit check: 0 — объявленные проверки пройдены, 1 — нарушение, 2 — среда/подготовка не проверена.\n"
          "Локальная модель C12 не подтверждает hosted GitLab; SQLite B29 не подтверждает восстановление PostgreSQL/offsite.\n")
    restore(root, state, reference)
    return root


def restore(root, state, reference=False):
    for name, content in files(state["case"], reference).items():
        write(root, "work/" + name, content)
    # No recursive delete: data, evidence and extra learner files are retained.


def config(root):
    return json.loads(beneath(root, "work/config.json").read_text())


@contextlib.contextmanager
def exclusive(root):
    with beneath(root, ".run.lock").open("a+") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Unavailable("another check/reset owns this workspace") from exc
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def port():
    try:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]
    except OSError as exc:
        raise Unavailable("loopback bind unavailable") from exc


def http(number, path="/", timeout=2, method="GET"):
    # Never send local lab requests through an inherited proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        request = urllib.request.Request(f"http://127.0.0.1:{number}{path}", method=method,
                                         data=b"{}" if method == "POST" else None)
        with opener.open(request, timeout=timeout) as response:
            return json.loads(response.read())
    except (OSError, ValueError, urllib.error.URLError):
        return None


def wait_http(number, seconds=5):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        value = http(number, timeout=0.3)
        if value is not None:
            return value
        time.sleep(0.05)
    return None


@contextlib.contextmanager
def server(root, number, filename="server.py"):
    with tempfile.TemporaryFile(mode="w+") as log:
        try:
            process = subprocess.Popen([sys.executable, str(beneath(root, "work/" + filename)),
                                        str(beneath(root, "data")), str(number)], stdout=log, stderr=log)
        except OSError as exc:
            raise Unavailable("could not start own server") from exc
        try:
            yield process, log
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)


def loopback(root, state, options):
    occupied = port()
    with server(root, occupied) as (blocker, _):
        original = wait_http(occupied)
        if not original or original.get("pid") != blocker.pid:
            raise Unavailable("baseline loopback server did not start")
        target = occupied if config(root)["port"] == "occupied" else port()
        with server(root, target) as (app, log):
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and app.poll() is None:
                observed = http(target)
                if observed and observed.get("pid") == app.pid:
                    break
                time.sleep(0.05)
            observed = http(target)
            log.flush()
            log.seek(0)
            detail = log.read()[-2000:]
            ok = bool(observed and observed.get("pid") == app.pid and blocker.poll() is None)
            return ok, {"level": "real loopback processes", "occupied_port": occupied,
                        "target_port": target, "target_exit": app.poll(), "diagnostic": detail,
                        "own_blocker_survived": blocker.poll() is None}


def permissions(root, state, options):
    if sys.platform != "linux" or os.geteuid() == 0:
        raise Unavailable("requires Linux with an unprivileged current user")
    directory = beneath(root, "data/public")
    directory.mkdir(exist_ok=True)
    marker = beneath(root, "data/public/marker.txt")
    if not marker.exists():
        marker.write_text("orderflow")
    marker.chmod(0o400)
    mode = int(config(root)["directory_mode"], 8)
    if mode not in (0o400, 0o500, 0o700, 0o755):
        raise ValueError("unexpected directory mode")
    directory.chmod(mode)
    try:
        result = command([sys.executable, "-c", "from pathlib import Path; import sys; print(Path(sys.argv[1]).read_text())", marker])
        return result["exit"] == 0 and result["stdout"].strip() == "orderflow", {"mode": oct(mode), **result, "level": "Linux current UID traversal"}
    finally:
        directory.chmod(0o700)  # Restore accessibility even on failure; no data removed.


def dag(root, state, options):
    graph = json.loads(beneath(root, "work/pipeline.json").read_text())
    jobs = {k: v for k, v in graph.items() if isinstance(v, dict)}
    if not {"build", "gate", "marker"}.issubset(jobs):
        return False, {"reason": "required job missing", "level": "local dependency model"}
    if jobs["gate"].get("allow_failure") or jobs["marker"].get("when") == "always":
        return False, {"reason": "gate is optional or marker ignores failure", "level": "local dependency model"}
    if any(set(v) & {"rules", "only", "except", "extends"} for v in jobs.values()):
        raise Unavailable("conditional GitLab features require hosted checking, outside this local DAG model")
    stages = graph.get("stages", [])
    def parents(name):
        job = jobs[name]
        if "needs" in job:
            return [x if isinstance(x, str) else x["job"] for x in job["needs"]]
        idx = stages.index(job["stage"])
        return [k for k, v in jobs.items() if stages.index(v["stage"]) < idx]
    def runnable(name, failed, visited=None):
        visited = set() if visited is None else visited
        if name in visited or name not in jobs:
            raise ValueError("cycle or absent dependency")
        if name == failed:
            return False
        return all(runnable(p, failed, visited | {name}) for p in parents(name))
    blocked = not runnable("marker", "gate")
    normal = runnable("marker", None)
    return blocked and normal, {"level": "local dependency model, not GitLab scheduler", "failed_gate_blocks_marker": blocked,
                              "successful_gate_allows_marker": normal, "hosted_ci_verified": False,
                              "export": "work/pipeline.json is YAML-compatible; publish only in a chosen lab project"}


def replay(root, state, options):
    source = beneath(root, "work/replay.py")
    # Child process: learner code cannot hang the controller indefinitely.
    driver = Path(__file__).with_name("replay_probe.py")
    result = command([sys.executable, driver, source, beneath(root, "data")], timeout=10)
    detail = {"level": "real SQLite transactions/replay, not PostgreSQL/offsite", **result}
    return result["exit"] == 0, detail


def terraform(root, state, options):
    binary = shutil.which(options.terraform)
    if not binary:
        raise Unavailable("Terraform >=1.4 required; no installation or provider download is automatic")
    work = beneath(root, "work")
    # An isolated copy for probes; original plan/state and learner data remain untouched.
    with tempfile.TemporaryDirectory(prefix="tf-probe-", dir=beneath(root, "data")) as temp:
        trial = Path(temp)
        if beneath(root, "work/main.tf").read_text() != files("T24")["main.tf"]:
            raise ValueError("only plan.sh is editable in this local Terraform exercise; provider/backend changes are refused")
        shutil.copyfile(beneath(root, "work/main.tf"), trial / "main.tf")
        shutil.copyfile(beneath(root, "work/plan.sh"), trial / "plan.sh")
        env = os.environ.copy()
        env.update(TF_IN_AUTOMATION="1", TF_DATA_DIR=str(trial / ".terraform"))
        shim = trial / "bin"
        shim.mkdir()
        (shim / "terraform").symlink_to(binary)
        env["PATH"] = str(shim) + os.pathsep + env.get("PATH", "")
        init = must([binary, "init", "-input=false", "-no-color"], cwd=trial, env=env)
        must([binary, "apply", "-auto-approve", "-input=false", "-no-color"], cwd=trial, env=env)
        unchanged = command(["sh", "plan.sh"], cwd=trial, env=env)
        content = (trial / "main.tf").read_text()
        if '"v1"' not in content:
            raise ValueError("fixture input v1 must remain available for change experiment")
        (trial / "main.tf").write_text(content.replace('"v1"', '"v2"'))
        changed = command(["sh", "plan.sh"], cwd=trial, env=env)
        (trial / "invalid.tf").write_text("not valid hcl !!!")
        invalid = command(["sh", "plan.sh"], cwd=trial, env=env)
        return [x["exit"] for x in (unchanged, changed, invalid)] == [0, 2, 1], {
            "level": "Terraform local backend only", "unchanged": unchanged, "changed": changed, "invalid": invalid,
            "version": must([binary, "version", "-json"])["stdout"]}


def systemd(root, state, options):
    if sys.platform != "linux" or not shutil.which("systemd-run"):
        raise Unavailable("Linux with a running systemd user manager required")
    must(["systemctl", "--user", "show", "--property=Version"])
    name = "oflab-" + state["id"]
    number = port()
    executable = sys.executable if state["case"] == "A25" or config(root)["python"] == "current" else str(beneath(root, "work/pythno"))
    # A fresh transient name; refuse to operate on a pre-existing unit.
    existing = command(["systemctl", "--user", "show", name, "--property=LoadState", "--value"])
    if existing["stdout"].strip() not in ("", "not-found"):
        raise Unavailable("owned unit name already exists; inspect it instead of replacing")
    started_at = str(int(time.time()))
    started = command(["systemd-run", "--user", "--unit=" + name, "--property=Type=exec", "--collect",
                       shutil.which("env") or "/usr/bin/env", executable,
                       beneath(root, "work/server.py"), beneath(root, "data"), str(number)])
    details = {"level": "Linux systemd user service", "start": started}
    try:
        baseline = wait_http(number)
        details["http"] = baseline
        if state["case"] == "A25":
            if not baseline:
                raise Unavailable("systemd baseline did not become ready")
            if not shutil.which(options.ansible):
                raise Unavailable("ansible-playbook required")
            env = os.environ.copy()
            env.update(COURSE_UNIT=name, COURSE_DATA=str(beneath(root, "data")), COURSE_VALUE="v1",
                       ANSIBLE_NOCOLOR="1", ANSIBLE_STDOUT_CALLBACK="default")
            runs, snapshots = [], []
            for value in ("v1", "v1", "v2", "v2"):
                env["COURSE_VALUE"] = value
                runs.append(command([options.ansible, "-i", "localhost,", "playbook.json"], cwd=beneath(root, "work"), env=env))
                snapshots.append(wait_http(number))
            pids = [x.get("pid") if x else None for x in snapshots]
            hashes = [x.get("config_sha") if x else None for x in snapshots]
            changed = [re.findall(r"\bchanged=(\d+)", r["stdout"]) for r in runs]
            if not all(changed):
                raise Unavailable("Ansible recap could not be read; idempotence not fully verified")
            ok = all(r["exit"] == 0 for r in runs) and all(pids) and pids[0] == pids[1] and pids[1] != pids[2] and pids[2] == pids[3]
            ok = ok and hashes[0] == hashes[1] and hashes[1] != hashes[2] and hashes[2] == hashes[3]
            ok = ok and changed[1][-1] == changed[3][-1] == "0"
            before_check = beneath(root, "data/service.conf").read_bytes()
            env["COURSE_VALUE"] = "v3"
            check_mode = command([options.ansible, "-i", "localhost,", "playbook.json", "--check", "--diff"], cwd=beneath(root, "work"), env=env)
            check_snapshot = wait_http(number)
            check_unchanged = before_check == beneath(root, "data/service.conf").read_bytes() and check_snapshot == snapshots[-1]
            details.update(runs=runs, snapshots=snapshots, changed=changed, check_mode=check_mode, check_mode_unchanged=check_unchanged)
            ok = ok and check_mode["exit"] == 0 and check_unchanged
        else:
            ok = bool(baseline and baseline.get("identity") == state["id"])
        details["status"] = command(["systemctl", "--user", "show", name, "--property=ActiveState,MainPID,ExecMainStatus"])
        details["journal"] = command(["journalctl", "--user-unit=" + name, "--since=@" + started_at,
                                      "-n", "20", "--no-pager", "-o", "json"])
        if details["journal"]["exit"] or not details["journal"]["stdout"].strip():
            raise Unavailable("no readable journal entries for this user unit; check journal access before grading")
        properties = dict(line.split("=", 1) for line in details["status"]["stdout"].splitlines() if "=" in line)
        observed = check_snapshot if state["case"] == "A25" else baseline
        ok = ok and details["status"]["exit"] == 0 and properties.get("ActiveState") == "active"
        ok = ok and observed and str(observed.get("pid")) == properties.get("MainPID")
        return ok, details
    finally:
        write(root, "evidence/systemd-last-diagnostics.json", dump(details))
        command(["systemctl", "--user", "stop", name])
        command(["systemctl", "--user", "reset-failed", name])


def execute(root, state, options):
    backend = CASES[state["case"]][1]
    handlers = {"loopback": loopback, "linux-permissions": permissions, "dag-model": dag,
                "sqlite-replay": replay, "terraform": terraform, "systemd": systemd, "ansible-systemd": systemd}
    if backend in handlers:
        return handlers[backend](root, state, options)
    from infrastructure import run_infrastructure
    return run_infrastructure(root, state, options)


def check(root, state, options):
    report = {"case": state["case"], "version": VERSION, "runner_revision": RUNNER_REVISION,
              "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "platform": sys.platform, "python": sys.version.split()[0], "source_sha256": {}}
    try:
        for name in files(state["case"]):
            file = beneath(root, "work/" + name)
            report["source_sha256"][name] = hashlib.sha256(file.read_bytes()).hexdigest()
        ok, detail = execute(root, state, options)
        code = 0 if ok else 1
        report.update(status="passed" if ok else "failed", detail=detail)
    except Unavailable as exc:
        code = 2
        report.update(status="unverified", reason=str(exc))
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        code = 2
        report.update(status="unverified", reason=f"preparation/configuration: {exc}")
    report["exit"] = code
    name = "evidence/" + str(time.time_ns()) + ".json"
    write(root, name, dump(report))
    print(dump(report), end="")
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("list", "prepare", "check", "reset", "reference"))
    parser.add_argument("path", type=Path, nargs="?")
    parser.add_argument("--case", choices=sorted(CASES))
    parser.add_argument("--image", help="locally cached Python image by repository@sha256 digest")
    parser.add_argument("--postgres-image", help="locally cached PostgreSQL image by digest")
    parser.add_argument("--context", help="explicit kind-* context with a loopback API endpoint")
    parser.add_argument("--terraform", default="terraform")
    parser.add_argument("--ansible", default="ansible-playbook")
    parser.add_argument("--helm", default="helm")
    options = parser.parse_args(argv)
    try:
        if options.action == "list":
            print(dump({k: {"topic": v[0], "backend": v[1], "task": v[2]} for k,v in CASES.items()}), end="")
            return 0
        if options.path is None:
            parser.error("path is required")
        if options.action == "prepare":
            if not options.case:
                parser.error("--case is required for prepare")
            print(prepare(options.path, options.case))
            return 0
        root, state = load(options.path)
        with exclusive(root):
            if options.action == "check":
                return check(root, state, options)
            restore(root, state, reference=options.action == "reference")
        print("Sources restored; data and evidence retained.")
        return 0
    except (ValueError, OSError, KeyError, Unavailable) as exc:
        print(f"Refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
