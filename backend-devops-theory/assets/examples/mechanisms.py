#!/usr/bin/env python3
"""Small executable mechanisms, not replacements for PostgreSQL/broker/cloud acceptance."""
import argparse
import asyncio
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import time


def transactions():
    # Explicit schedule of two stale reads. This models an algorithm, not a DB isolation level.
    stock = 1
    a_read = b_read = stock
    accepted = []
    for name, seen in (("A", a_read), ("B", b_read)):
        if seen >= 1:
            stock = seen - 1
            accepted.append(name)
    with closing(sqlite3.connect(":memory:")) as db:
        db.execute("CREATE TABLE stock(id INTEGER PRIMARY KEY, qty INTEGER CHECK(qty>=0))")
        db.execute("INSERT INTO stock VALUES(1,1)")
        outcomes = []
        for _ in range(2):
            with db:
                outcomes.append(db.execute("UPDATE stock SET qty=qty-1 WHERE id=1 AND qty>=1").rowcount)
        return {"level": "scheduled algorithm + sequential SQLite conditional writes",
                "stale_read": {"accepted": accepted, "remaining": stock},
                "conditional_write_rows": outcomes, "postgres_concurrency_verified": False}


async def async_scope():
    started = asyncio.Event()
    events = []
    async def slow():
        events.append("resource-open")
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            events.append("resource-closed")
    async def failing():
        await started.wait()
        raise ValueError("provider rejected request")
    async def grouped():
        failed = False
        try:
            async with asyncio.TaskGroup() as group:
                group.create_task(slow())
                group.create_task(failing())
        except* ValueError:
            failed = True
        return failed
    # Independent demonstrations have independent owning tasks. Early Python 3.11
    # retains TaskGroup cancellation state which must not enter the timeout demo.
    failed = await asyncio.create_task(grouped())
    events.append("scope-left")
    timeout_closed = False
    try:
        async with asyncio.timeout(0.02):
            try:
                await asyncio.Event().wait()
            finally:
                timeout_closed = True
    except TimeoutError:
        pass
    return {"events": events, "value_error_observed": failed, "timeout_cleanup": timeout_closed,
            "live_children": len([task for task in asyncio.all_tasks() if task is not asyncio.current_task()])}


def outbox():
    with tempfile.TemporaryDirectory(prefix="of-outbox-") as directory:
        root = Path(directory)
        with closing(sqlite3.connect(root / "producer.db")) as producer, closing(sqlite3.connect(root / "broker.db")) as broker, closing(sqlite3.connect(root / "consumer.db")) as consumer:
            producer.executescript("CREATE TABLE orders(id TEXT PRIMARY KEY); CREATE TABLE outbox(id TEXT PRIMARY KEY,sent INTEGER);")
            broker.execute("CREATE TABLE deliveries(sequence INTEGER PRIMARY KEY,id TEXT)")
            consumer.executescript("CREATE TABLE receipts(id TEXT PRIMARY KEY); CREATE TABLE effects(id TEXT PRIMARY KEY,amount INTEGER);")
            with producer:
                producer.execute("INSERT INTO orders VALUES('o1')")
                producer.execute("INSERT INTO outbox VALUES('e1',0)")
            # Publisher commits to a separate durable broker, then dies before marking sent.
            with broker:
                broker.execute("INSERT INTO deliveries(id) VALUES('e1')")
            pending_after_crash = producer.execute("SELECT count(*) FROM outbox WHERE sent=0").fetchone()[0]
            for (event,) in producer.execute("SELECT id FROM outbox WHERE sent=0"):
                with broker:
                    broker.execute("INSERT INTO deliveries(id) VALUES(?)", (event,))
                with producer:
                    producer.execute("UPDATE outbox SET sent=1 WHERE id=?", (event,))
            for (event,) in broker.execute("SELECT id FROM deliveries ORDER BY sequence"):
                with consumer:
                    first = consumer.execute("INSERT OR IGNORE INTO receipts VALUES(?)", (event,)).rowcount
                    if first:
                        consumer.execute("INSERT INTO effects VALUES(?,100)", (event,))
            return {"level": "three real SQLite stores, explicit crash boundary; not RabbitMQ",
                    "pending_after_publish_crash": pending_after_crash,
                    "deliveries": broker.execute("SELECT count(*) FROM deliveries").fetchone()[0],
                    "effects": consumer.execute("SELECT count(*),sum(amount) FROM effects").fetchone()}


def release():
    with closing(sqlite3.connect(":memory:")) as db:
        db.execute("CREATE TABLE orders(id INTEGER PRIMARY KEY,amount INTEGER NOT NULL)")
        db.execute("INSERT INTO orders VALUES(1,250)")
        def old_write(amount):
            db.execute("INSERT INTO orders(amount) VALUES(?)", (amount,))
        def old_read():
            return db.execute("SELECT id,amount FROM orders ORDER BY id").fetchall()
        before = old_read()
        db.execute("ALTER TABLE orders ADD COLUMN note TEXT")
        old_write(100)
        db.execute("INSERT INTO orders(amount,note) VALUES(150,'new code')")
        rollback_read = old_read()
        old_write(200)
        tuple_reader_broken = False
        try:
            identity, amount = db.execute("SELECT * FROM orders WHERE id=1").fetchone()
        except ValueError:
            tuple_reader_broken = True
        with db:
            first_backfill = db.execute("UPDATE orders SET note='legacy' WHERE note IS NULL").rowcount
        with db:
            repeat_backfill = db.execute("UPDATE orders SET note='legacy' WHERE note IS NULL").rowcount
        return {"level": "SQLite schema/client compatibility, not image promotion",
                "before": before, "old_reads_after_new_write": rollback_read,
                "rows_after_rollback_write": old_read(), "select_star_tuple_broken": tuple_reader_broken,
                "backfill_changed": first_backfill, "repeat_changed": repeat_backfill}


def restore():
    with tempfile.TemporaryDirectory(prefix="of-restore-") as directory:
        root = Path(directory)
        source = sqlite3.connect(root / "source.db")
        backup = sqlite3.connect(root / "backup.db")
        recovered = sqlite3.connect(root / "recovered.db")
        try:
            source.execute("CREATE TABLE orders(id INTEGER PRIMARY KEY,amount INTEGER)")
            with source:
                source.execute("INSERT INTO orders VALUES(1,250)")
            source.backup(backup)
            with source:
                source.execute("INSERT INTO orders VALUES(2,100)")
            # Stop using source: restoration reads only the backup connection.
            source.close()
            started = time.monotonic()
            backup.backup(recovered)
            rows = recovered.execute("SELECT id,amount FROM orders ORDER BY id").fetchall()
            elapsed = time.monotonic() - started
            return {"level": "local SQLite snapshot/restore, not offsite or PostgreSQL",
                    "restored": rows, "lost_post_backup_ids": [2], "measured_local_restore_seconds": elapsed,
                    "rpo_seconds": None, "rpo_note": "No simulated business timestamps: cannot infer a time RPO from row count"}
        finally:
            source.close()
            backup.close()
            recovered.close()


def run(name):
    if name == "asyncio":
        return asyncio.run(async_scope())
    return {"transactions": transactions, "outbox": outbox, "release": release, "restore": restore}[name]()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("example", choices=("transactions", "asyncio", "outbox", "release", "restore", "all"))
    name = parser.parse_args().example
    results = {n: run(n) for n in ("transactions", "asyncio", "outbox", "release", "restore")} if name == "all" else run(name)
    print(json.dumps(results, ensure_ascii=False, indent=2))
