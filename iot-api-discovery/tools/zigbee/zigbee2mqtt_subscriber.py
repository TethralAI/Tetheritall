from __future__ import annotations

import json
from typing import Any, Callable


def subscribe(broker: str, topic: str, on_message: Callable[[str, dict], None], port: int = 1883, username: str | None = None, password: str | None = None) -> None:
    try:
        import paho.mqtt.client as mqtt  # type: ignore
    except Exception:
        return

    def _on_connect(client, userdata, flags, rc):
        client.subscribe(topic)

    def _on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except Exception:
            payload = {"raw": msg.payload.decode("utf-8", errors="ignore")}
        on_message(msg.topic, payload)

    client = mqtt.Client()
    if username and password:
        client.username_pw_set(username, password)
    client.on_connect = _on_connect
    client.on_message = _on_message
    client.connect(broker, port, 10)
    client.loop_start()

