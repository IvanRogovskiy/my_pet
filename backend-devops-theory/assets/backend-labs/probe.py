"""Runs inside the owned client container. Deliberate process crashes are part of B17."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid

import pika
import psycopg
from psycopg import sql

DSN = 'host=pg dbname=lab user=lab password=local-fixture-only connect_timeout=5'


def db(schema='public'):
    conn = psycopg.connect(DSN, autocommit=True)
    conn.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(schema)))
    conn.execute("SET statement_timeout='10s'")
    conn.execute("SET lock_timeout='8s'")
    return conn


def mq():
    return pika.BlockingConnection(pika.ConnectionParameters('mq', credentials=pika.PlainCredentials('lab', 'local-fixture-only'),
                                  socket_timeout=5, blocked_connection_timeout=10, heartbeat=20))


def submission():
    spec = importlib.util.spec_from_file_location('submission', '/lab/submission.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture():
    schema = 'probe_' + uuid.uuid4().hex
    with db() as conn:
        conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    with db(schema) as conn:
        conn.execute('CREATE TABLE products(id int primary key, stock int NOT NULL CHECK(stock>=0))')
        conn.execute('INSERT INTO products VALUES(1,1)')
        conn.execute('CREATE TABLE orders(id bigserial primary key, owner int, quantity int, note text)')
        conn.execute('CREATE TABLE requests(id bigserial primary key, owner int, key text, quantity int, UNIQUE(owner,key))')
        conn.execute('CREATE TABLE outbox(event text primary key, sent boolean NOT NULL DEFAULT false)')
        conn.execute('CREATE TABLE receipts(event text primary key)')
        conn.execute('CREATE TABLE effects(id int primary key, count int)')
        conn.execute('INSERT INTO effects VALUES(1,0)')
    return schema


def snapshot(schema):
    with db(schema) as conn:
        return {'stock': conn.execute('SELECT stock FROM products').fetchone()[0],
                'orders': conn.execute('SELECT count(*) FROM orders').fetchone()[0],
                'requests': conn.execute('SELECT count(*) FROM requests').fetchone()[0]}


def parallel(schema, function):
    barrier = threading.Barrier(2, timeout=6)
    def worker():
        with db(schema) as conn:
            pid = conn.execute('SELECT pg_backend_pid()').fetchone()[0]
            isolation = conn.execute('SHOW transaction_isolation').fetchone()[0]
            reached = []
            def synchronize():
                reached.append(time.monotonic_ns())
                return barrier.wait()
            try:
                result = {'value': function(conn, synchronize)}
            except Exception as exc:
                result = {'error': type(exc).__name__}
            return {'pid': pid, 'isolation': isolation, 'barrier_arrivals_ns': reached, **result}
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker) for _ in range(2)]
        return [f.result(timeout=20) for f in futures]


def race(schema, app):
    result = parallel(schema, lambda conn, sync: app.reserve(conn, sync))
    after = snapshot(schema)
    with db(schema) as conn:
        conn.execute('TRUNCATE orders')
        conn.execute('UPDATE products SET stock=1')
        raised = False
        try: app.reserve(conn, lambda: None, fail=True)
        except RuntimeError: raised = True
    rollback = snapshot(schema)
    criteria = {'one_order': sorted(r.get('value', -1) for r in result) == [False, True] and after['orders'] == 1,
                'stock_zero': after['stock'] == 0,
                'rollback': raised and rollback['stock'] == 1 and rollback['orders'] == 0,
                'concurrent_sessions': concurrent_proof(result)}
    return criteria, {'concurrent': result, 'after': after, 'rollback': rollback, 'isolation': 'read committed'}


def concurrent_proof(result):
    return len({r['pid'] for r in result}) == 2 and all(len(r['barrier_arrivals_ns']) == 1 and r['isolation'] == 'read committed' for r in result)


def idem(schema, app):
    with db(schema) as conn: conn.execute('UPDATE products SET stock=10')
    result = parallel(schema, lambda conn, sync: app.submit(conn, 10, 'same', 1, sync))
    after = snapshot(schema)
    with db(schema) as conn:
        conflict = False
        try: app.submit(conn, 10, 'same', 2, lambda: None)
        except ValueError: conflict = True
        other = app.submit(conn, 20, 'same', 1, lambda: None)
        before_fail = snapshot(schema)
        shortage = False
        try: app.submit(conn, 10, 'shortage', 99, lambda: None)
        except ValueError: shortage = True
        after_fail = snapshot(schema)
    criteria = {'same_result_one_effect': all('value' in r for r in result) and result[0].get('value') == result[1].get('value') and after == {'stock': 9, 'orders': 1, 'requests': 1},
                'changed_body_rejected': conflict,
                'owner_scope': other not in [r.get('value') for r in result] and before_fail['orders'] == 2,
                'shortage_rollback': shortage and before_fail == after_fail,
                'concurrent_sessions': concurrent_proof(result)}
    return criteria, {'concurrent': result, 'after': after, 'after_other': before_fail, 'after_shortage': after_fail}


def authorization(schema, app):
    with db(schema) as conn: conn.execute("INSERT INTO orders(owner,quantity,note) VALUES(10,1,'original')")
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_GET(self): self.handle_request(False)
        def do_PATCH(self): self.handle_request(True)
        def handle_request(self, write):
            actor = {'fixture-a': 10, 'fixture-b': 20}.get(self.headers.get('X-Fixture-Session'))
            body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', '0'))) or b'{}')
            with db(schema) as conn:
                owner, note = conn.execute('SELECT owner,note FROM orders WHERE id=1').fetchone()
                status = 401 if actor is None else (200 if app.allowed(actor, owner, body.get('owner')) else 403)
                if status == 200 and write:
                    conn.execute('UPDATE orders SET note=%s WHERE id=1', (body['note'],))
            self.send_response(status); self.end_headers()
            self.wfile.write(json.dumps({'note': note} if status == 200 else {}).encode())
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    observed = []
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for actor, body_owner, method, expected in [('fixture-b',20,'GET',403), ('fixture-b',20,'PATCH',403),
                                                   ('fixture-a',20,'GET',200), ('fixture-a',20,'PATCH',200),
                                                   ('missing',10,'GET',401)]:
            with db(schema) as conn: before = conn.execute('SELECT note FROM orders WHERE id=1').fetchone()[0]
            request = urllib.request.Request(f'http://127.0.0.1:{server.server_port}/orders/1',
                data=json.dumps({'owner': body_owner, 'note': actor}).encode(), method=method, headers={'X-Fixture-Session': actor})
            try:
                with opener.open(request, timeout=3) as response: status = response.status
            except urllib.error.HTTPError as exc: status = exc.code; exc.close()
            with db(schema) as conn: after = conn.execute('SELECT note FROM orders WHERE id=1').fetchone()[0]
            observed.append({'actor':actor, 'request_owner':body_owner, 'method':method, 'status':status,
                             'expected':expected, 'before':before, 'after':after})
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=3)
    return {'http_matrix': all(r['status'] == r['expected'] for r in observed),
            'denied_preserves_data': all(r['before'] == r['after'] for r in observed if r['expected'] != 200)}, {'http': observed}


def child(action, schema, queue, crash):
    connection = mq(); channel = connection.channel()
    channel.queue_declare(queue=queue, durable=True)
    if action == 'publisher':
        channel.confirm_delivery()
        with db(schema) as conn:
            for event, in conn.execute('SELECT event FROM outbox WHERE sent=false'):
                channel.basic_publish('', queue, event.encode(), mandatory=True, properties=pika.BasicProperties(delivery_mode=2))
                if crash: os._exit(17)  # Broker confirmed; DB mark has not happened.
                conn.execute('UPDATE outbox SET sent=true WHERE event=%s', (event,))
    else:
        app = submission()
        method, _, body = channel.basic_get(queue, auto_ack=False)
        if method is None: raise RuntimeError('expected a broker delivery')
        with db(schema) as conn: app.consume(conn, body.decode())
        if crash: os._exit(18)  # DB committed; broker has not received ack.
        channel.basic_ack(method.delivery_tag)
    connection.close()


def outbox(schema, app):
    queue = 'course.' + schema
    with db(schema) as conn: conn.execute('INSERT INTO outbox(event) VALUES(%s)', (uuid.uuid4().hex,))
    codes = []
    for action, crash in [('publisher','yes'), ('publisher','no'), ('consumer','yes')]:
        r = subprocess.run([sys.executable, __file__, action, schema, queue, crash], capture_output=True, text=True, timeout=20)
        codes.append(r.returncode)
        if r.returncode not in (0,17,18): raise RuntimeError('child failed: ' + r.stderr[-1000:])
    connection = mq(); channel = connection.channel()
    deliveries = []
    try:
        deadline = time.monotonic() + 8
        while len(deliveries) < 2 and time.monotonic() < deadline:
            method, _, body = channel.basic_get(queue, auto_ack=False)
            if method is None:
                connection.process_data_events(time_limit=0.05); continue
            with db(schema) as conn: app.consume(conn, body.decode())
            deliveries.append({'redelivered': method.redelivered, 'event': body.decode()})
            channel.basic_ack(method.delivery_tag)
        pending = channel.queue_declare(queue, durable=True).method.message_count
        with db(schema) as conn:
            effects = conn.execute('SELECT count FROM effects WHERE id=1').fetchone()[0]
            receipts = conn.execute('SELECT count(*) FROM receipts').fetchone()[0]
            sent = conn.execute('SELECT sent FROM outbox').fetchone()[0]
            conn.execute("CREATE FUNCTION reject_effect() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'injected effect failure'; END $$")
            conn.execute('CREATE TRIGGER reject_effect BEFORE UPDATE ON effects FOR EACH ROW EXECUTE FUNCTION reject_effect()')
            failed_event = uuid.uuid4().hex
            raised = False
            try: app.consume(conn, failed_event)
            except psycopg.errors.RaiseException: raised = True
            remaining = conn.execute('SELECT count(*) FROM receipts WHERE event=%s', (failed_event,)).fetchone()[0]
            unchanged = conn.execute('SELECT count FROM effects WHERE id=1').fetchone()[0] == effects
            conn.execute('DROP TRIGGER reject_effect ON effects')
        criteria = {'crash_windows': codes == [17,0,18] and sent,
                    'broker_redelivery': len(deliveries) == 2 and any(d['redelivered'] for d in deliveries) and pending == 0,
                    'single_effect': effects == 1 and receipts == 1,
                    'receipt_effect_rollback': raised and remaining == 0 and unchanged}
        return criteria, {'child_exits': codes, 'deliveries_after_crash': deliveries, 'effect_count': effects,
                          'receipts': receipts, 'queue_pending': pending, 'queue': queue,
                          'injected_effect_error': raised, 'receipt_after_effect_error': remaining}
    finally:
        # Only this unique fixture queue; database evidence is retained.
        channel.queue_delete(queue=queue); connection.close()


def health():
    with db() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS stand_identity(id int primary key, value text)')
        marker = json.loads(Path('/lab/stand.json').read_text())['id']
        existing = conn.execute('SELECT value FROM stand_identity WHERE id=1').fetchone()
        previously = Path('/lab/health.json').exists()
        if not existing and previously: raise RuntimeError('persistent DB marker was lost')
        if not existing: conn.execute('INSERT INTO stand_identity VALUES(1,%s)', (marker,))
        elif existing[0] != marker: raise RuntimeError('persistent DB marker mismatch')
        version = conn.execute('SHOW server_version').fetchone()[0]
    connection = mq()
    rabbit = connection._impl.server_properties.get('version')
    connection.close()
    result = {'postgres': version, 'rabbitmq': rabbit, 'python': sys.version.split()[0], 'marker': marker,
              'data_preserved': bool(existing), 'passed': True}
    Path('/lab/health.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


def main():
    case = sys.argv[1]
    if case in ('publisher','consumer'):
        child(case, sys.argv[2], sys.argv[3], sys.argv[4] == 'yes'); return 0
    if case == 'health': health(); return 0
    schema = fixture()
    result = {'case': case, 'schema': schema, 'submission_sha256': hashlib.sha256(Path('/lab/submission.py').read_bytes()).hexdigest(),
              'level': 'real PostgreSQL and RabbitMQ / HTTP fixture as applicable'}
    try:
        criteria, detail = {'B07': authorization, 'B08R': race, 'B08I': idem, 'B17': outbox}[case](schema, submission())
        result.update(criteria=criteria, detail=detail, passed=all(criteria.values()))
        code = 0 if result['passed'] else 1
    except Exception as exc:
        result.update(passed=False, unverified=True, error=type(exc).__name__ + ': ' + str(exc)[:600]); code=2
    result['exit'] = code
    Path('/lab/evidence/' + str(time.time_ns()) + '.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
