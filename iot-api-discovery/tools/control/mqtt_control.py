from __future__ import annotations

from typing import Any, Dict


def publish_mqtt(broker: str, topic: str, payload: str, port: int = 1883, username: str | None = None, password: str | None = None, qos: int = 0) -> Dict[str, Any]:
    try:
        import paho.mqtt.client as mqtt  # type: ignore
    except Exception as exc:
        return {"ok": False, "error": f"mqtt unavailable: {exc}"}

    try:
        client = mqtt.Client()
        if username and password:
            client.username_pw_set(username, password)
        client.connect(broker, port, keepalive=10)
        result = client.publish(topic, payload=payload, qos=qos)
        result.wait_for_publish()
        client.disconnect()
        rc = result.rc
        return {"ok": rc == mqtt.MQTT_ERR_SUCCESS, "result": rc}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

