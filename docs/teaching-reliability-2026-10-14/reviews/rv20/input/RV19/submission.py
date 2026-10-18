def totals(connection):
    return connection.execute("""
        SELECT o.buyer_id, SUM(DISTINCT l.price*l.qty)
        FROM orders o JOIN lines l ON l.order_id=o.id
        GROUP BY o.buyer_id
    """).fetchall()
