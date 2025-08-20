from __future__ import annotations

from typing import Any, Dict, List


def topic_for_device(device: Dict[str, Any]) -> str:
    # Best-effort topic derivation
    return device.get("friendly_name") or device.get("ieee_address") or "zigbee2mqtt/device"


def map_state_to_capabilities(state: Dict[str, Any]) -> List[str]:
    caps: List[str] = []
    if "state" in state:
        caps.append("switch")
    if "brightness" in state:
        caps.append("dimmer")
    if "color" in state or "color_temp" in state:
        caps.append("colorLight")
    if "temperature" in state:
        caps.append("temperatureSensor")
    if "humidity" in state:
        caps.append("humiditySensor")
    return caps

