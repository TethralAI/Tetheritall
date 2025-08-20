from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class Capability(str, Enum):
    SWITCH = "switch"
    DIMMER = "dimmer"
    COLOR_LIGHT = "colorLight"
    TEMPERATURE_SENSOR = "temperatureSensor"
    HUMIDITY_SENSOR = "humiditySensor"
    MOTION_SENSOR = "motionSensor"
    CONTACT_SENSOR = "contactSensor"
    LOCK = "lock"
    THERMOSTAT = "thermostat"
    ENERGY_METER = "energyMeter"


@dataclass
class CapabilityEntry:
    capability: Capability
    endpoint: Dict[str, Any]
    source: str
    confidence: float = 0.5


def normalize_capabilities(discovery: Dict[str, Any]) -> List[CapabilityEntry]:
    entries: List[CapabilityEntry] = []
    endpoints = discovery.get("endpoints", []) or []
    for ep in endpoints:
        path = str(ep.get("path", "")).lower()
        method = str(ep.get("method", "")).upper()
        source = str(ep.get("source", ""))
        conf = float(ep.get("confidence") or 0.5)

        def add(cap: Capability, boost: float = 0.0) -> None:
            entries.append(CapabilityEntry(capability=cap, endpoint=ep, source=source, confidence=min(1.0, conf + boost)))

        if any(k in path for k in ["/light", "/lights", "brightness", "illum"]):
            if "brightness" in path or "dim" in path:
                add(Capability.DIMMER, 0.1)
            else:
                add(Capability.SWITCH, 0.1)
        if any(k in path for k in ["/color", "/hue", "/saturation"]):
            add(Capability.COLOR_LIGHT, 0.1)
        if any(k in path for k in ["/temp", "/temperature"]):
            add(Capability.TEMPERATURE_SENSOR, 0.1)
        if "/humidity" in path:
            add(Capability.HUMIDITY_SENSOR, 0.1)
        if any(k in path for k in ["/motion", "/pir"]):
            add(Capability.MOTION_SENSOR)
        if any(k in path for k in ["/contact", "/door", "/window"]):
            add(Capability.CONTACT_SENSOR)
        if "/lock" in path:
            add(Capability.LOCK)
        if any(k in path for k in ["thermostat", "/hvac", "/setpoint"]):
            add(Capability.THERMOSTAT)
        if any(k in path for k in ["/power", "/energy", "/watt", "/kwh"]):
            add(Capability.ENERGY_METER)

    # MQTT hints via proxy controllers
    proxy = discovery.get("proxy_controllers", []) or []
    for ctrl in proxy:
        t = str(ctrl.get("type", "")).lower()
        if t in ("zigbee2mqtt",):
            entries.append(CapabilityEntry(capability=Capability.SWITCH, endpoint={"protocol": "mqtt"}, source=t, confidence=0.4))

    return entries

