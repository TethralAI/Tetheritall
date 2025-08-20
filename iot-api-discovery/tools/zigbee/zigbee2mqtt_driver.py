from __future__ import annotations

from typing import Any, Dict, List, Callable


class Zigbee2MQTTDriver:
    def __init__(self, broker: str, port: int = 1883, username: str | None = None, password: str | None = None) -> None:
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password

    def publish(self, topic: str, payload: str) -> Dict[str, Any]:
        try:
            import paho.mqtt.client as mqtt  # type: ignore
        except Exception as exc:
            return {"ok": False, "error": f"mqtt unavailable: {exc}"}
        try:
            client = mqtt.Client()
            if self.username and self.password:
                client.username_pw_set(self.username, self.password)
            client.connect(self.broker, self.port, keepalive=10)
            result = client.publish(topic, payload)
            result.wait_for_publish()
            client.disconnect()
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

