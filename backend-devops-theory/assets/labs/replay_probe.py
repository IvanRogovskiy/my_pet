"""A real, isolated projection rebuild. Imported only inside a bounded child process."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile


def run(source, data):
    spec = importlib.util.spec_from_file_location("student_replay", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix="replay-", dir=data) as trial:
        db = sqlite3.connect(str(Path(trial) / "projection.sqlite"))
        db.executescript('''CREATE TABLE events(id TEXT PRIMARY KEY, amount INTEGER);
            CREATE TABLE receipts(generation TEXT, event_id TEXT, PRIMARY KEY(generation,event_id));
            CREATE TABLE projection(generation TEXT, event_id TEXT, amount INTEGER,
                                    PRIMARY KEY(generation,event_id));
            INSERT INTO events VALUES ('e1',100),('e2',250);
            INSERT INTO receipts VALUES ('old','e1'),('old','e2');
            INSERT INTO projection VALUES ('old','e1',100),('old','e2',250);''')
        before = db.execute("SELECT * FROM projection WHERE generation='old' ORDER BY event_id").fetchall()
        with db:
            module.rebuild(db, "restored")
        first = db.execute("SELECT event_id,amount FROM projection WHERE generation='restored' ORDER BY event_id").fetchall()
        with db:
            module.rebuild(db, "restored")
        second = db.execute("SELECT event_id,amount FROM projection WHERE generation='restored' ORDER BY event_id").fetchall()
        old = db.execute("SELECT * FROM projection WHERE generation='old' ORDER BY event_id").fetchall()
        expected = [('e1',100),('e2',250)]
        ok = first == expected and second == expected and old == before
        print(json.dumps({"first":first,"repeat":second,"old_preserved":old==before,"expected":expected}))
        db.close()
        return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(run(Path(sys.argv[1]), Path(sys.argv[2])))
