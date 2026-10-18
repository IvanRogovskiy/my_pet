def totals(connection):
    return connection.execute("""
        WITH per_order AS (
            SELECT order_id, SUM(price*qty) AS amount
            FROM lines GROUP BY order_id
        )
        SELECT o.buyer_id, SUM(p.amount)
        FROM orders o JOIN per_order p ON p.order_id=o.id
        GROUP BY o.buyer_id
    """).fetchall()
