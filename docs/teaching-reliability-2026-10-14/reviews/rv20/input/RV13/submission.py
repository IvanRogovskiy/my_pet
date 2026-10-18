def deploy(service, config):
    service.config = config
    service.restart()
    return {"changed": 0}
