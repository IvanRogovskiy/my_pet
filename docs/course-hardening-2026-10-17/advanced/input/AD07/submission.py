def page(rows, cursor, limit):
    ordered = sorted(rows)
    if cursor is not None:
        ordered = [row for row in ordered if row[0] > cursor[0]]
    return ordered[:limit]
