#!/usr/bin/env python3
"""Owned loopback TLS fixture. No trust-store changes, downloads, or PID-based cleanup."""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import ssl
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VERSION = "2026-10-12.1"


def private_write(path, data):
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(data)


def owned(path):
    if path.is_symlink():
        raise ValueError("symlink root refused")
    root = path.resolve()
    state = json.loads((root / "owner.json").read_text())
    if state["root"] != str(root) or state["version"] != VERSION:
        raise ValueError("root/version mismatch")
    for name in ("ready.json", "ready.tmp", "serve.lock", "control.key", "ca.pem", "valid.pem", "expired.pem", "valid.key", "expired.key"):
        item = root / name
        if item.is_symlink() or (item.exists() and item.stat().st_nlink != 1):
            raise ValueError("linked fixture file refused")
    return root, state


def prepare(path):
    # This optional dependency is checked before creating any files.
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    if path.exists() or path.is_symlink():
        raise ValueError("prepare requires a new directory; use a new generation after pause")
    root = path.resolve()
    root.mkdir(parents=True, mode=0o700)
    now = dt.datetime.now(dt.timezone.utc)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "OrderFlow ephemeral course CA")])
    ca = (x509.CertificateBuilder().subject_name(issuer).issuer_name(issuer)
          .public_key(key.public_key()).serial_number(x509.random_serial_number())
          .not_valid_before(now - dt.timedelta(days=3)).not_valid_after(now + dt.timedelta(days=2))
          .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
          .sign(key, hashes.SHA256()))
    (root / "ca.pem").write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    state = {"version": VERSION, "root": str(root), "id": secrets.token_hex(16),
             "created_utc": now.isoformat(), "certificates": {},
             "ca_sha256": hashlib.sha256((root / "ca.pem").read_bytes()).hexdigest()}
    for name, start, end in [
        ("valid", now-dt.timedelta(minutes=5), now+dt.timedelta(days=1)),
        ("expired", now-dt.timedelta(days=2), now-dt.timedelta(days=1)),
    ]:
        leaf_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        leaf = (x509.CertificateBuilder()
                .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")]))
                .issuer_name(issuer).public_key(leaf_key.public_key())
                .serial_number(x509.random_serial_number()).not_valid_before(start).not_valid_after(end)
                .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False)
                .sign(key, hashes.SHA256()))
        private_write(root / (name + ".key"), leaf_key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        (root / (name + ".pem")).write_bytes(leaf.public_bytes(serialization.Encoding.PEM))
        state["certificates"][name] = {"not_before": start.isoformat(), "not_after": end.isoformat(),
                                     "san": ["localhost"], "sha256": leaf.fingerprint(hashes.SHA256()).hex()}
    private_write(root / "control.key", secrets.token_hex(32).encode())
    (root / "owner.json").write_text(json.dumps(state, indent=2) + "\n")
    return state


def serve(path):
    root, state = owned(path)
    end = dt.datetime.fromisoformat(state["certificates"]["valid"]["not_after"])
    if end <= dt.datetime.now(dt.timezone.utc):
        raise ValueError("certificate expired; prepare a new directory/generation")
    with (root / "serve.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        ready = root / "ready.json"
        ready.unlink(missing_ok=True)
        instance = secrets.token_hex(16)
        stop = threading.Event()
        token = (root / "control.key").read_text()

        class Handler(BaseHTTPRequestHandler):
            def respond(self, code):
                payload = json.dumps({"id": state["id"], "instance": instance, "status": code,
                                      "host": self.headers.get("Host"), "origin": self.headers.get("Origin")}).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def do_GET(self):
                self.respond(403 if self.path == "/denied" else 200)

            def do_POST(self):
                if (self.server is servers.get("control") and self.path == "/stop"
                        and secrets.compare_digest(self.headers.get("X-Fixture-Control", ""), token)):
                    self.respond(200)
                    stop.set()
                else:
                    self.respond(403)

            def log_message(self, *args):
                pass

        servers, threads = {}, []
        try:
            for name in ("valid", "expired", "control"):
                server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
                servers[name] = server
                if name != "control":
                    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                    context.load_cert_chain(root / (name + ".pem"), root / (name + ".key"))
                    server.socket = context.wrap_socket(server.socket, server_side=True)
                thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
                thread.start()
                threads.append(thread)
            pending = root / "ready.tmp"
            pending.write_text(json.dumps({"id": state["id"], "instance": instance,
                                           "ports": {k: v.server_port for k, v in servers.items()}}) + "\n")
            pending.replace(ready)
            stop.wait()
        finally:
            # Shutdown only started loops; server_close also covers a bind/TLS setup failure.
            for server, thread in zip(servers.values(), threads):
                server.shutdown()
                thread.join(timeout=3)
            for server in servers.values():
                server.server_close()
            ready.unlink(missing_ok=True)


def request(url, context=None, *, headers=None, data=None):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                         urllib.request.HTTPSHandler(context=context))
    req = urllib.request.Request(url, headers=headers or {}, data=data)
    try:
        response = opener.open(req, timeout=3)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        return response.status, json.loads(response.read())


def live(path):
    root, state = owned(path)
    ready = json.loads((root / "ready.json").read_text())
    if not isinstance(ready, dict) or ready.get("id") != state["id"]:
        raise ValueError("stale or malformed readiness; wait for the current serve instance")
    ports = ready.get("ports")
    if (not isinstance(ports, dict) or set(ports) != {"valid", "expired", "control"}
            or not isinstance(ready.get("instance"), str)
            or not all(type(p) is int and 0 < p < 65536 for p in ports.values())):
        raise ValueError("malformed readiness ports/instance")
    status, body = request(f'http://127.0.0.1:{ready["ports"]["control"]}/')
    if status != 200 or body["id"] != state["id"] or body["instance"] != ready["instance"]:
        raise ValueError("stale readiness or another fixture")
    return root, ready


def check(path):
    root, ready = live(path)
    context = ssl.create_default_context(cafile=str(root / "ca.pem"))
    port = ready["ports"]["valid"]
    results = []
    for case, route, expected in [("trusted", "/", 200), ("tls-with-http-denial", "/denied", 403)]:
        status, body = request(f"https://localhost:{port}{route}", context)
        ok = status == expected and body["id"] == ready["id"] and body["instance"] == ready["instance"]
        results.append({"case": case, "http": status, "passed": ok})
    for case, host, number, ctx, codes in [
        ("unknown-ca", "localhost", port, ssl.create_default_context(), {18, 19, 20, 21}),
        ("wrong-name", "127.0.0.1", port, context, {62, 64}),
        ("expired", "localhost", ready["ports"]["expired"], context, {10}),
    ]:
        try:
            request(f"https://{host}:{number}/", ctx)
        except urllib.error.URLError as exc:
            reason = exc.reason
            code = getattr(reason, "verify_code", None)
            results.append({"case": case, "verify_code": code,
                            "passed": isinstance(reason, ssl.SSLCertVerificationError) and code in codes})
        else:
            results.append({"case": case, "passed": False})
    report = {"version": VERSION, "instance": ready["instance"], "checks": results,
              "passed": all(x["passed"] for x in results)}
    (root / ("check-" + str(time.time_ns()) + ".json")).write_text(json.dumps(report, indent=2) + "\n")
    return report


def stop(path):
    root, ready = live(path)
    status, _ = request(f'http://127.0.0.1:{ready["ports"]["control"]}/stop',
                        headers={"X-Fixture-Control": (root / "control.key").read_text()}, data=b"")
    if status != 200:
        raise ValueError("owned server did not accept stop")
    for _ in range(100):
        if not (root / "ready.json").exists():
            return {"stopped": True}
        time.sleep(0.05)
    raise TimeoutError("shutdown not confirmed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "serve", "check", "stop"))
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    try:
        result = globals()[args.action](args.path)
    except (OSError, ValueError, KeyError, ImportError, TimeoutError, AssertionError) as exc:
        print(json.dumps({"status": "unverified", "reason": type(exc).__name__ + ": " + str(exc)}))
        return 2
    if result is not None:
        print(json.dumps(result, indent=2))
    return 1 if isinstance(result, dict) and result.get("passed") is False else 0


if __name__ == "__main__":
    raise SystemExit(main())
