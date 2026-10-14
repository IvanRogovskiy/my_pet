def reserve(connection, sku):
    cursor = connection.execute("UPDATE stock SET qty=qty-1 WHERE sku=%s AND qty>=1", (sku,))
    return cursor.rowcount == 1
