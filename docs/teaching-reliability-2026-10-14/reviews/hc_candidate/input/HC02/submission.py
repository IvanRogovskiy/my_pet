def can_edit(actor, document):
    if actor["role"] == "admin":
        return True
    return actor["team_id"] == document["team_id"]
