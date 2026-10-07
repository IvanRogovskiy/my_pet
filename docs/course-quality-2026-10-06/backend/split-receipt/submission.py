def consume(db, event):
    with db.transaction():
        inserted = db.execute("INSERT INTO receipts(event) VALUES(%s) ON CONFLICT DO NOTHING RETURNING event", (event,)).fetchone()
    if inserted:
        with db.transaction():
            db.execute("UPDATE effects SET count=count+1 WHERE id=1")
