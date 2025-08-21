from __future__ import annotations

import json
from typing import Dict, Any

from config.settings import settings
from libs.capabilities.schemas import DeviceAddress, Switchable, Dimmable, ColorControl
from tools.zigbee.zigbee2mqtt import topic_for_device
from tools.zigbee.zigbee2mqtt_driver import Zigbee2MQTTDriver


def _driver() -> Zigbee2MQTTDriver:
    return Zigbee2MQTTDriver(
        broker=settings.z2m_broker or "localhost",
        port=settings.z2m_port,
        username=settings.z2m_username,
        password=settings.z2m_password,
    )


class Z2MSwitchAdapter(Switchable):
    def turn_on(self, address: DeviceAddress) -> Dict[str, Any]:
        topic = f"zigbee2mqtt/{address.external_id}/set"
        return _driver().publish(topic, json.dumps({"state": "ON"}))

    def turn_off(self, address: DeviceAddress) -> Dict[str, Any]:
        topic = f"zigbee2mqtt/{address.external_id}/set"
        return _driver().publish(topic, json.dumps({"state": "OFF"}))

    def get_state(self, address: DeviceAddress) -> Dict[str, Any]:
        # Best-effort, state retrieval via MQTT is non-trivial without subscription; return address
        return {"ok": True, "provider": "zigbee2mqtt", "external_id": address.external_id}


class Z2MDimmableAdapter(Z2MSwitchAdapter, Dimmable):
    def set_brightness(self, address: DeviceAddress, level: int) -> Dict[str, Any]:
        lvl = max(0, min(254, int(round(level * 2.54))))  # scale 0-100 to 0-254
        topic = f"zigbee2mqtt/{address.external_id}/set"
        return _driver().publish(topic, json.dumps({"brightness": lvl}))


class Z2MColorControlAdapter(Z2MDimmableAdapter, ColorControl):
    def set_color_hsv(self, address: DeviceAddress, h: float, s: float, v: float) -> Dict[str, Any]:
        topic = f"zigbee2mqtt/{address.external_id}/set"
        payload = {"color": {"h": float(h), "s": float(s), "v": float(v)}}
        return _driver().publish(topic, json.dumps(payload))

    def set_color_temp(self, address: DeviceAddress, mireds: int) -> Dict[str, Any]:
        topic = f"zigbee2mqtt/{address.external_id}/set"
        return _driver().publish(topic, json.dumps({"color_temp": int(mireds)}))

