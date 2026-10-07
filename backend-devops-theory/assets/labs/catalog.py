"""Versioned, synthetic exercises. Reference variants are for authors, not student exports."""
import json

VERSION = "2026-10-06.1"
CASES = {
    "L02a": ("02/1", "systemd", "Служба не стартует. Исправь запуск; предъяви журнал, active, PID и HTTP."),
    "L02b": ("02/3", "loopback", "HTTP не запускается: порт занят собственным учебным процессом. Не останавливай чужие процессы."),
    "L02c": ("02/1", "linux-permissions", "Файл существует, но чтение через родительский каталог запрещено. Исправь минимальные права."),
    "D10": ("10/3", "docker", "Контейнер healthy, с хоста HTTP недоступен. Исправь mapping и сохрани маркер данных."),
    "C12": ("12/1", "dag-model", "Падающий gate не блокирует marker. Исправь зависимости, затем проверь успешный gate."),
    "T24": ("24/3", "terraform", "Plan с изменениями считается пустым. Различи отсутствие изменений, diff и ошибку."),
    "A25": ("25/2", "ansible-systemd", "Неизменный повтор playbook перезапускает сервис. Сохрани PID, конфиг и HTTP."),
    "R26": ("26/3", "docker-release", "Новый образ не стартует после expand-миграции. Проверь запуск и настоящий откат к старому образу."),
    "K27": ("27/2", "kubernetes-postgres", "PostgreSQL готов локально, но Pod не Ready. Раздели локальную готовность и маршрут Service."),
    "H28": ("28/1", "helm", "Helm --wait успешен, но Service не ведёт к приложению. Исправь связь selector/labels."),
    "B29": ("29/2", "sqlite-replay", "После восстановления новая проекция пуста. Исправь область receipts и проверь повтор без дублей."),
}

SERVER = '''import hashlib, json, os, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
root, port = Path(sys.argv[1]), int(sys.argv[2])
identity = (root / "identity.txt").read_text().strip()
config = root / "service.conf"
digest = hashlib.sha256(config.read_bytes() if config.exists() else b"").hexdigest()
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"identity": identity, "pid": os.getpid(), "config_sha": digest}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *args):
        pass
HTTPServer((sys.argv[3] if len(sys.argv)>3 else "127.0.0.1", port), Handler).serve_forever()
'''

APP = '''import json, os, sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
db = Path(os.environ.get("COURSE_DATA_DIR", "/data")) / "orders.sqlite"
version = Path(__file__).with_name("version.txt").read_text().strip()
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/health"):
            self.send_error(404)
            return
        self.respond(200)
    def do_POST(self):
        if self.path != "/orders":
            self.send_error(404)
            return
        with sqlite3.connect(db) as c:
            c.execute("INSERT INTO orders(amount) VALUES (100)")
        self.respond(201)
    def respond(self, status):
        with sqlite3.connect(db) as c:
            rows = c.execute("SELECT id,amount FROM orders ORDER BY id").fetchall()
        body = json.dumps({"version": version, "rows": rows}).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *args):
        pass
HTTPServer((os.environ.get("COURSE_BIND", "0.0.0.0"),int(os.environ.get("COURSE_PORT", "8000"))),Handler).serve_forever()
'''

REPLAY_BAD = '''def rebuild(connection, generation):
    for event_id, amount in connection.execute("SELECT id,amount FROM events ORDER BY id").fetchall():
        seen = connection.execute("SELECT 1 FROM receipts WHERE event_id=?", (event_id,)).fetchone()
        if not seen:
            connection.execute("INSERT INTO projection VALUES (?,?,?)", (generation,event_id,amount))
            connection.execute("INSERT INTO receipts VALUES (?,?)", (generation,event_id))
'''
REPLAY_GOOD = REPLAY_BAD.replace(
    'WHERE event_id=?", (event_id,)',
    'WHERE generation=? AND event_id=?", (generation,event_id)')


def dump(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def files(case, reference=False):
    """Sources only. Persistent learner data and evidence never belong to reset."""
    if case not in CASES:
        raise ValueError("unknown case")
    result = {"server.py": SERVER}
    if case == "L02a":
        result["config.json"] = dump({"python": "current" if reference else "pythno"})
    elif case == "L02b":
        result["config.json"] = dump({"port": "free" if reference else "occupied"})
    elif case == "L02c":
        result["config.json"] = dump({"directory_mode": "0500" if reference else "0400"})
    elif case == "D10":
        result["config.json"] = dump({"container_port": 8000 if reference else 8001})
    elif case == "C12":
        graph = {
            "stages": ["build", "verify", "marker"],
            "build": {"stage": "build", "script": ["true"]},
            "gate": {"stage": "verify", "needs": ["build"], "script": ["exit 1"]},
            "marker": {"stage": "marker", "needs": ["build", "gate"] if reference else ["build"],
                       "script": ["printf 'marker-ran\\n'"]},
        }
        result["pipeline.json"] = dump(graph)  # JSON is also valid YAML for GitLab.
    elif case == "T24":
        result["main.tf"] = 'terraform { required_version = ">= 1.4, < 2.0" }\nresource "terraform_data" "probe" { input = "v1" }\n'
        result["plan.sh"] = '#!/bin/sh\nterraform plan -input=false -no-color' + (' -detailed-exitcode' if reference else '') + '\n'
    elif case == "A25":
        restart = {"name": "Restart lab service", "ansible.builtin.systemd_service": {
            "name": "{{ lookup('env', 'COURSE_UNIT') }}", "scope": "user", "state": "restarted"}}
        copy = {"name": "Write lab config", "ansible.builtin.copy": {
            "content": "{{ lookup('env', 'COURSE_VALUE') }}\n",
            "dest": "{{ lookup('env', 'COURSE_DATA') }}/service.conf", "mode": "0600"}}
        if reference:
            copy["notify"] = "Restart lab service"
        result["playbook.json"] = dump([{"hosts": "localhost", "connection": "local", "gather_facts": False,
            "tasks": [copy] if reference else [copy, restart], "handlers": [restart] if reference else []}])
    elif case == "R26":
        result["app.py"] = APP
        result["Dockerfile"] = ('ARG BASE\nFROM ${BASE}\nWORKDIR /app\nCOPY app.py version.txt /app/\n'
                                + ('CMD ["python", "app.py"]\n' if reference else 'CMD ["python", "-m", "missing_app"]\n'))
        result["version.txt"] = "v2\n"
    elif case == "K27":
        result["config.json"] = dump({"probe_host": "127.0.0.1" if reference else "db"})
    elif case == "H28":
        result["chart/Chart.yaml"] = 'apiVersion: v2\nname: orderflow-lab\nversion: 0.1.0\n'
        result["chart/values.yaml"] = dump({"selector": "orderflow-lab" if reference else "orderflow-lab-mismatch"})
        result["chart/templates/web.yaml"] = '''apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 1
  selector:
    matchLabels: {app: orderflow-lab}
  template:
    metadata:
      labels: {app: orderflow-lab}
    spec:
      containers:
        - name: web
          image: {{ .Values.image | quote }}
          imagePullPolicy: Never
          command: [python, -m, http.server, "8000", --directory, /tmp]
          readinessProbe:
            httpGet: {path: /, port: 8000}
          resources:
            requests: {cpu: 10m, memory: 24Mi}
            limits: {cpu: 100m, memory: 96Mi}
---
apiVersion: v1
kind: Service
metadata:
  name: web
spec:
  selector:
    app: {{ .Values.selector | quote }}
  ports:
    - port: 8000
      targetPort: 8000
'''
    elif case == "B29":
        result["replay.py"] = REPLAY_GOOD if reference else REPLAY_BAD
    return result
