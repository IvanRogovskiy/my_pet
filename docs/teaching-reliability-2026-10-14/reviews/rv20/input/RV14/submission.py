def deploy(service, config):
    changed = service.config != config
    if changed:
        service.config = config
        service.restart()
    return {"changed": int(changed)}
