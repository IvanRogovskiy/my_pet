def reserve(db, sync, fail=False):
    with db.transaction():
        sync()
        stock = db.execute("SELECT stock FROM products WHERE id=1 FOR UPDATE").fetchone()[0]
        if stock < 1:
            return False
        db.execute("UPDATE products SET stock=stock-1 WHERE id=1")
        if fail:
            raise RuntimeError("injected order failure")
        db.execute("INSERT INTO orders(owner,quantity) VALUES(10,1)")
        return True
