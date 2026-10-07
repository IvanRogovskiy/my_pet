"""Actual Docker / local Kubernetes backends. Never starts Docker or creates a cluster."""
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import time
from urllib.parse import urlsplit

from catalog import APP, dump
from lab import Unavailable, beneath, command, config, http, must, port, wait_http, write


def disk_preflight(root):
    if shutil.disk_usage(root).free < 5 * 1024 ** 3:
        raise Unavailable("host has less than 5 GiB free; infrastructure trial was not started")


def image_digest(image):
    if not image or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[0-9a-f]{64}", image):
        raise Unavailable("supply an explicit locally cached repository@sha256 digest")
    return image


def local_docker(image, root):
    disk_preflight(root)
    image_digest(image)
    must(["docker", "version", "--format", "{{.Server.Version}}"])
    must(["docker", "image", "inspect", image, "--format", "{{.Id}}"])
    # Reports capacity inside Docker's data filesystem; no network and no image pull.
    r = must(["docker", "run", "--rm", "--pull=never", "--network=none", image, "python", "-c",
              "import shutil; print(shutil.disk_usage('/').free)"])
    try:
        free = int(r["stdout"].strip())
    except ValueError as exc:
        raise Unavailable("image must provide Python; Docker free-space probe failed") from exc
    if free < 1024 ** 3:
        raise Unavailable("Docker data filesystem has less than 1 GiB free")


def owned_remove_container(name, token):
    r = command(["docker", "inspect", name, "--format", '{{index .Config.Labels "course.owner"}}'])
    if r["exit"]:
        return
    if r["stdout"].strip() != token:
        raise Unavailable("container ownership mismatch; cleanup refused")
    must(["docker", "rm", "-f", name])


def docker_run(name, state, image, root, number, target, args, code_dir=None):
    existing = command(["docker", "inspect", name, "--format", "{{.Id}}"])
    if existing["exit"] == 0:
        raise Unavailable("container already exists; refusing to replace it")
    argv = ["docker", "run", "-d", "--pull=never", "--name", name,
            "--label", "course.owner=" + state["id"], "--memory=128m", "--cpus=0.5",
            "-p", f"127.0.0.1:{number}:{target}",
            "--mount", f"type=bind,src={beneath(root, 'data')},dst=/data",
            "--health-cmd", "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=1)\"",
            "--health-interval=1s", "--health-timeout=2s", "--health-retries=5"]
    if code_dir:
        argv += ["--mount", f"type=bind,src={code_dir},dst=/app,readonly"]
    return command(argv + [image] + args)


def wait_health(name):
    until = time.monotonic() + 12
    while time.monotonic() < until:
        r = command(["docker", "inspect", name, "--format", "{{.State.Status}} {{.State.Health.Status}}"])
        if r["exit"] or "exited" in r["stdout"] or "unhealthy" in r["stdout"]:
            return False
        if r["stdout"].strip() == "running healthy":
            return True
        time.sleep(0.2)
    return False


def docker_port(root, state, options):
    local_docker(options.image, root)
    target = config(root)["container_port"]
    if target not in (8000, 8001):
        raise ValueError("this port-mapping exercise uses internal ports 8000/8001")
    name = "oflab-" + state["id"]
    number = port()
    marker = beneath(root, "data/identity.txt").read_text()
    started = docker_run(name, state, options.image, root, number, target,
                         ["python", "/app/server.py", "/data", "8000", "0.0.0.0"], beneath(root, "work"))
    detail = {"level": "real Docker container and host HTTP", "start": started}
    try:
        if started["exit"]:
            raise Unavailable("Docker run failed before app readiness")
        healthy = wait_health(name)
        if not healthy:
            detail["logs"] = command(["docker", "logs", "--tail", "40", name])
            raise Unavailable("baseline app is not healthy; mapping defect not isolated")
        first = wait_http(number, seconds=2)
        owned_remove_container(name, state["id"])
        must_run = docker_run(name, state, options.image, root, number, target,
                             ["python", "/app/server.py", "/data", "8000", "0.0.0.0"], beneath(root, "work"))
        if must_run["exit"]:
            raise Unavailable("recreate failed")
        second_health = wait_health(name)
        second = wait_http(number, seconds=2)
        data_ok = beneath(root, "data/identity.txt").read_text() == marker
        ok = all(v and v.get("identity") == state["id"] for v in (first, second)) and second_health and data_ok
        detail.update(healthy=healthy, before_recreate=first, after_recreate=second, marker_preserved=data_ok,
                      logs=command(["docker", "logs", "--tail", "40", name]))
        return bool(ok), detail
    finally:
        write(root, "evidence/docker-last-diagnostics.json", dump(detail))
        owned_remove_container(name, state["id"])


def release(root, state, options):
    local_docker(options.image, root)
    old = beneath(root, "data/old-build")
    old.mkdir(exist_ok=True)
    write(root, "data/old-build/app.py", APP)
    write(root, "data/old-build/version.txt", "v1\n")
    write(root, "data/old-build/Dockerfile", 'ARG BASE\nFROM ${BASE}\nWORKDIR /app\nCOPY app.py version.txt /app/\nCMD ["python", "app.py"]\n')
    tags = ["oflab-" + state["id"] + ":old", "oflab-" + state["id"] + ":new"]
    names = ["oflab-" + state["id"] + "-old", "oflab-" + state["id"] + "-new"]
    built = []
    db = beneath(root, "data/orders.sqlite")
    with sqlite3.connect(db) as c:
        c.execute("CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY, amount INTEGER NOT NULL)")
        c.execute("INSERT OR IGNORE INTO orders(id,amount) VALUES (1,250)")
        original = c.execute("SELECT id,amount FROM orders ORDER BY id").fetchall()
    detail = {"level": "two actual Docker image IDs and SQLite expand/rollback; not PostgreSQL production"}
    try:
        for tag, directory in zip(tags, (old, beneath(root, "work"))):
            if command(["docker", "image", "inspect", tag])["exit"] == 0:
                raise Unavailable("build tag already exists; refusing overwrite")
            r = command(["docker", "build", "--network=none", "--pull=false", "--label", "course.owner=" + state["id"],
                         "--build-arg", "BASE=" + options.image, "-t", tag, directory], timeout=60)
            if r["exit"]:
                raise Unavailable("image build failed; runtime defect not reached")
            built.append(tag)
        detail["image_ids"] = [must(["docker", "image", "inspect", t, "--format", "{{.Id}}"])["stdout"].strip() for t in tags]
        first_port = port()
        r = docker_run(names[0], state, tags[0], root, first_port, 8000, [])
        if r["exit"] or not wait_health(names[0]):
            raise Unavailable("old image baseline unavailable")
        before = http(first_port, "/orders", method="POST")
        owned_remove_container(names[0], state["id"])
        with sqlite3.connect(db) as c:
            if "note" not in [x[1] for x in c.execute("PRAGMA table_info(orders)")]:
                c.execute("ALTER TABLE orders ADD COLUMN note TEXT")
            protected = c.execute("SELECT id,amount FROM orders ORDER BY id").fetchall()
        second_port = port()
        new_start = docker_run(names[1], state, tags[1], root, second_port, 8000, [])
        if new_start["exit"]:
            raise Unavailable("new container could not be created")
        new_health = wait_health(names[1])
        new_http = http(second_port, "/orders", method="POST") if new_health else None
        detail["new_logs"] = command(["docker", "logs", "--tail", "40", names[1]])
        owned_remove_container(names[1], state["id"])
        third_port = port()
        rollback = docker_run(names[0], state, tags[0], root, third_port, 8000, [])
        rollback_health = wait_health(names[0]) if rollback["exit"] == 0 else False
        old_http = http(third_port, "/orders", method="POST") if rollback_health else None
        with sqlite3.connect(db) as c:
            after = c.execute("SELECT id,amount FROM orders ORDER BY id").fetchall()
            schema_kept = "note" in [x[1] for x in c.execute("PRAGMA table_info(orders)")]
        data_ok = all(row in after for row in original + protected)
        detail.update(before=before, new_healthy=new_health, new_http=new_http, rollback_http=old_http,
                      schema_kept=schema_kept, prior_rows_preserved=data_ok, production_promoted=False)
        return bool(new_health and new_http and new_http.get("version") == "v2" and old_http
                    and old_http.get("version") == "v1" and data_ok and schema_kept), detail
    finally:
        write(root, "evidence/release-last-diagnostics.json", dump(detail))
        for name in names:
            owned_remove_container(name, state["id"])
        for tag in built:
            owner = must(["docker", "image", "inspect", tag, "--format", '{{index .Config.Labels "course.owner"}}'])["stdout"].strip()
            if owner != state["id"]:
                raise Unavailable("image ownership mismatch; cleanup refused")
            must(["docker", "image", "rm", tag])  # No shared images, caches or volumes pruned.


class Cluster:
    def __init__(self, root, state, options):
        disk_preflight(root)
        context = options.context
        if not context or not context.startswith("kind-"):
            raise Unavailable("explicit kind-* context required; no cluster is created")
        self.prefix = ["kubectl", "--context", context, "--request-timeout=10s"]
        endpoint = must(self.prefix + ["config", "view", "--minify", "-o", "jsonpath={.clusters[0].cluster.server}"])["stdout"]
        if urlsplit(endpoint).hostname not in ("127.0.0.1", "localhost", "::1"):
            raise Unavailable("only loopback Kubernetes API endpoints are accepted")
        self.root, self.state, self.options = root, state, options
        self.ns = "oflab-" + state["id"]
        self.events = []
        # Create atomically, so an unrelated pre-existing namespace is never adopted.
        obj = {"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": self.ns, "labels": {"course.owner": state["id"]}}}
        path = beneath(root, "data/namespace.json")
        write(root, "data/namespace.json", dump(obj))
        existing = self.call(["get", "namespace", self.ns, "-o", "json"], namespaced=False)
        if existing["exit"] == 0:
            live = json.loads(existing["stdout"])
            record = beneath(root, "data/cluster-owner.json")
            if not record.exists() or json.loads(record.read_text()).get("uid") != live["metadata"]["uid"]:
                raise Unavailable("namespace already exists without matching recorded UID")
            if live["metadata"].get("labels", {}).get("course.owner") != state["id"]:
                raise Unavailable("namespace owner label mismatch")
        else:
            must(self.prefix + ["create", "-f", path])
            live = json.loads(must(self.prefix + ["get", "namespace", self.ns, "-o", "json"])["stdout"])
            write(root, "data/cluster-owner.json", dump({"uid": live["metadata"]["uid"], "context": context}))

    def call(self, args, namespaced=True, timeout=20):
        prefix = self.prefix + (["-n", self.ns] if namespaced else [])
        return command(prefix + args, timeout=timeout)

    def apply(self, name, obj):
        write(self.root, "data/" + name, dump(obj))
        r = self.call(["apply", "-f", beneath(self.root, "data/" + name)])
        if r["exit"]:
            raise Unavailable("could not apply lab workload")

    def diagnostics(self):
        # Synthetic namespace only; no Secrets, kubeconfig, describe/env dumps.
        result = {}
        deadline = time.monotonic() + 20
        def collect(args):
            try:
                return self.call(args, timeout=4)
            except Unavailable as exc:
                return {"exit":2,"stderr":str(exc),"stdout":""}
        for resource in ("pods", "pvc", "events", "services", "endpointslices"):
            if time.monotonic() >= deadline:
                break
            result[resource] = collect(["get", resource, "-o", "wide"])
        pods = collect(["get", "pods", "-o", "jsonpath={.items[*].metadata.name}"])
        for pod in pods["stdout"].split():
            for previous in (False, True):
                if time.monotonic() >= deadline:
                    break
                args = ["logs", pod, "--all-containers", "--tail=25"] + (["--previous"] if previous else [])
                result[pod + ("-previous" if previous else "-current")] = collect(args)
        return result

    def stop(self):
        # Keep PVC and namespace: explicit manual disposal is documented, never a reset side effect.
        try:
            return self.call(["scale", "deployment", "--all", "--replicas=0"])
        except Unavailable as exc:
            return {"exit":2,"stderr":str(exc),"stdout":""}


def postgres_fixture(cluster, root):
    """Seed once per owned workspace; later checks must reveal data loss."""
    seeded = beneath(root, "data/postgres-seeded.json")
    if seeded.exists():
        return
    result = cluster.call(["exec", "deployment/db", "--", "psql", "-U", "postgres", "-h", "/var/run/postgresql", "-v", "ON_ERROR_STOP=1", "-c",
                           "CREATE TABLE IF NOT EXISTS lab_marker(id int PRIMARY KEY); INSERT INTO lab_marker VALUES(1) ON CONFLICT DO NOTHING;"])
    if result["exit"]:
        raise Unavailable("SQL fixture preparation failed")
    write(root, "data/postgres-seeded.json", dump({"seeded": True}))


def wait_cluster_command(cluster, args, seconds=15):
    """Readiness and Service routing converge separately; retry a bounded read."""
    deadline = time.monotonic() + seconds
    while True:
        result = cluster.call(args, timeout=6)
        if result["exit"] == 0 or time.monotonic() >= deadline:
            return result
        time.sleep(0.2)


def kubernetes(root, state, options):
    image = image_digest(options.postgres_image if state["case"] == "K27" else options.image)
    if state["case"] == "H28" and not shutil.which(options.helm):
        raise Unavailable("Helm is required")
    cluster = Cluster(root, state, options)
    detail = {"level": "real local Kubernetes", "namespace": cluster.ns}
    try:
        if state["case"] == "K27":
            probe = config(root)["probe_host"]
            if probe not in ("db", "127.0.0.1"):
                raise ValueError("probe_host must be db or 127.0.0.1 for this exercise")
            cluster.apply("postgres.json", {"apiVersion": "v1", "kind": "List", "items": [
                {"apiVersion": "v1", "kind": "PersistentVolumeClaim", "metadata": {"name": "db"}, "spec": {
                    "accessModes": ["ReadWriteOnce"], "resources": {"requests": {"storage": "128Mi"}}}},
                {"apiVersion": "v1", "kind": "Service", "metadata": {"name": "db"}, "spec": {
                    "selector": {"app": "db"}, "ports": [{"port": 5432, "targetPort": 5432}]}},
                {"apiVersion": "apps/v1", "kind": "Deployment", "metadata": {"name": "db"}, "spec": {
                    "replicas": 1, "strategy": {"type": "Recreate"}, "selector": {"matchLabels": {"app": "db"}},
                    "template": {"metadata": {"labels": {"app": "db"}}, "spec": {"containers": [{
                        "name": "db", "image": image, "imagePullPolicy": "Never",
                        "env": [{"name": "POSTGRES_PASSWORD", "value": "synthetic-lab-only"}, {"name": "PGHOST", "value": "db"},
                                {"name": "PGDATA", "value": "/var/lib/postgresql/data/pgdata"}],
                        "volumeMounts": [{"name": "data", "mountPath": "/var/lib/postgresql/data"}],
                        "resources": {"requests": {"cpu": "50m", "memory": "64Mi"}, "limits": {"cpu": "500m", "memory": "256Mi"}},
                        "readinessProbe": {"exec": {"command": ["pg_isready", "-h", probe, "-U", "postgres"]}, "periodSeconds": 2}}],
                        "volumes": [{"name": "data", "persistentVolumeClaim": {"claimName": "db"}}]}}}}]})
            local = None
            until = time.monotonic() + 40
            while time.monotonic() < until:
                local = cluster.call(["exec", "deployment/db", "--", "pg_isready", "-h", "127.0.0.1", "-U", "postgres"], timeout=6)
                if local["exit"] == 0:
                    break
                time.sleep(0.3)
            if not local or local["exit"]:
                raise Unavailable("database did not become locally ready; inspect image/PVC before diagnosing probe")
            postgres_fixture(cluster, root)
            ready = cluster.call(["rollout", "status", "deployment/db", "--timeout=12s"], timeout=16)
            route_args = ["exec", "deployment/db", "--", "pg_isready", "-h", "db", "-U", "postgres"]
            route = wait_cluster_command(cluster, route_args) if ready["exit"] == 0 else cluster.call(route_args)
            rows = cluster.call(["exec", "deployment/db", "--", "psql", "-U", "postgres", "-h", "/var/run/postgresql", "-Atc", "SELECT count(*) FROM lab_marker;"])
            sql_args = ["exec", "deployment/db", "--", "env", "PGPASSWORD=synthetic-lab-only", "PGCONNECT_TIMEOUT=2",
                        "psql", "-U", "postgres", "-h", "db", "-Atc", "SELECT count(*) FROM lab_marker;"]
            service_sql = wait_cluster_command(cluster, sql_args) if ready["exit"] == 0 else cluster.call(sql_args)
            detail.update(local=local, ready=ready, service=route, marker=rows, service_sql=service_sql)
            ok = ready["exit"] == route["exit"] == rows["exit"] == service_sql["exit"] == 0 and rows["stdout"].strip() == service_sql["stdout"].strip() == "1"
        else:
            helm = command([options.helm, "--kube-context", options.context, "upgrade", "--install", "web",
                            beneath(root, "work/chart"), "--namespace", cluster.ns, "--set-string", "image=" + image,
                            "--wait", "--timeout", "40s"], timeout=45)
            if helm["exit"]:
                raise Unavailable("Helm workload failed before Service selector experiment")
            route = cluster.call(["exec", "deployment/web", "--", "python", "-c",
                                  "import urllib.request; print(urllib.request.urlopen('http://web:8000/',timeout=3).status)"])
            detail.update(helm=helm, route=route, endpoints=cluster.call(["get", "endpointslices", "-l", "kubernetes.io/service-name=web", "-o", "wide"]))
            ok = route["exit"] == 0 and route["stdout"].strip() == "200"
        return ok, detail
    finally:
        try:
            detail["diagnostics"] = cluster.diagnostics()
        finally:
            detail["stop"] = cluster.stop()
            write(root, "evidence/cluster-last-diagnostics.json", dump(detail))


def run_infrastructure(root, state, options):
    if state["case"] == "D10":
        return docker_port(root, state, options)
    if state["case"] == "R26":
        return release(root, state, options)
    return kubernetes(root, state, options)
