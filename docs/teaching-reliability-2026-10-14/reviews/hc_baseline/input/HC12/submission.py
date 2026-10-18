def consume(event, effect_once, ack):
    effect_once(event["id"], event["payload"])
    ack()
