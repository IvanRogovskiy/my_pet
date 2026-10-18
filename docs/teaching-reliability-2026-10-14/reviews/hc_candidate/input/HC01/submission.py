def can_edit(actor, document):
    return actor["role"] == "admin" or actor["team_id"] in document["team_id"]
