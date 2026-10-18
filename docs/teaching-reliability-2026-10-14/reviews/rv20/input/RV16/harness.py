import json

def run(ready_path, client_check):
    ready = json.loads(ready_path.read_text())
    instance = ready["id"]
    return client_check(instance)
