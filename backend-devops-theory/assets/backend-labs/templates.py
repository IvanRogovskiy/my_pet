"""Instructor fixtures; show the faulty variant first, references only after an attempt."""
BAD = {
'B07': '''def allowed(actor, owner, request_owner):
    return actor == request_owner
''',
'B08R': '''def reserve(db, sync, fail=False):
    with db.transaction():
        stock = db.execute("SELECT stock FROM products WHERE id=1").fetchone()[0]
        sync()
        if stock < 1:
            return False
        db.execute("UPDATE products SET stock=%s WHERE id=1", (stock-1,))
        if fail:
            raise RuntimeError("injected order failure")
        db.execute("INSERT INTO orders(owner, quantity) VALUES(10, 1)")
        return True
''',
'B08I': '''def submit(db, owner, key, quantity, sync):
    with db.transaction():
        row = db.execute("SELECT id, quantity FROM requests WHERE key=%s", (key,)).fetchone()
        sync()
        if row:
            return row[0]
        ident = db.execute("INSERT INTO requests(owner, key, quantity) VALUES(%s,%s,%s) RETURNING id", (owner,key,quantity)).fetchone()[0]
        changed = db.execute("UPDATE products SET stock=stock-%s WHERE id=1 AND stock>=%s", (quantity, quantity)).rowcount
        if not changed:
            raise ValueError("out of stock")
        db.execute("INSERT INTO orders(owner, quantity) VALUES(%s,%s)", (owner,quantity))
        return ident
''',
'B17': '''def consume(db, event):
    with db.transaction():
        db.execute("UPDATE effects SET count=count+1 WHERE id=1")
''',
}
GOOD = {
'B07': '''def allowed(actor, owner, request_owner):
    return actor == owner
''',
'B08R': '''def reserve(db, sync, fail=False):
    with db.transaction():
        sync()
        changed = db.execute("UPDATE products SET stock=stock-1 WHERE id=1 AND stock>=1").rowcount
        if not changed:
            return False
        if fail:
            raise RuntimeError("injected order failure")
        db.execute("INSERT INTO orders(owner, quantity) VALUES(10,1)")
        return True
''',
'B08I': '''def submit(db, owner, key, quantity, sync):
    with db.transaction():
        sync()
        row = db.execute("INSERT INTO requests(owner,key,quantity) VALUES(%s,%s,%s) ON CONFLICT(owner,key) DO NOTHING RETURNING id", (owner,key,quantity)).fetchone()
        if not row:
            previous = db.execute("SELECT id,quantity FROM requests WHERE owner=%s AND key=%s", (owner,key)).fetchone()
            if previous[1] != quantity:
                raise ValueError("payload conflict")
            return previous[0]
        changed = db.execute("UPDATE products SET stock=stock-%s WHERE id=1 AND stock>=%s", (quantity,quantity)).rowcount
        if not changed:
            raise ValueError("out of stock")
        db.execute("INSERT INTO orders(owner,quantity) VALUES(%s,%s)", (owner,quantity))
        return row[0]
''',
'B17': '''def consume(db, event):
    with db.transaction():
        inserted = db.execute("INSERT INTO receipts(event) VALUES(%s) ON CONFLICT DO NOTHING RETURNING event", (event,)).fetchone()
        if inserted:
            db.execute("UPDATE effects SET count=count+1 WHERE id=1")
''',
}
ASSIGNMENTS = {
'B07': ('07/2', 'Исправь allowed: actor получен из доверенной fixture-сессии, owner из PostgreSQL, request_owner из недоверенного тела. C1: чужой заказ GET/PATCH даёт 403; C2: свой GET/PATCH даёт 200; C3: подмена request_owner не меняет права, отказ не меняет заказ. Сдай diff и HTTP/SQL evidence. Это object authorization, не аудит реализации входа.'),
'B08R': ('08/2', 'Исправь reserve: PostgreSQL Read Committed, товар stock=1, два независимых соединения. C1: ровно один True и один заказ; C2: итоговый stock=0; C3: ошибка создания заказа откатывает остаток и заказ. sync() — тестовый барьер: вызвать один раз до записи, не удерживая блокировку строки; его нельзя удалять. Можно использовать условный UPDATE или блокировку после барьера. Сдай diff, расписание и evidence.'),
'B08I': ('08/3', 'Исправь submit: область (owner,key), quantity — уже проверенное положительное целое, операция только create-order. C1: одновременный одинаковый запрос возвращает один id и создаёт один заказ/эффект; C2: другой quantity того же owner/key отвергается ValueError; C3: другой owner с тем же key независим. sync() вызывается один раз до конкурентной записи. C4: недоступный остаток не оставляет request/order. HTTP 409 проверяется в проекте отдельно.'),
'B17': ('17/3', 'Исправь consume. Harness публикует реальное RabbitMQ сообщение с publisher confirm, убивает publisher перед mark, затем повторяет публикацию. Consumer аварийно завершится после DB commit перед ack. C1: publish/mark окно даёт 2 сообщения; C2: сообщение после потери ack доставляется повторно; C3: эффект в PostgreSQL ровно один, receipt/effect атомарны. Сдай diff, объяснение границ commit/ack и evidence. Один publisher, один consumer; throughput и Celery routing здесь не проверяются.'),
}
