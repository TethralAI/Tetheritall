from __future__ import annotations

from typing import Dict, Any, List

from config.settings import settings
from tools.smartthings.cloud import device_commands, device_status
from libs.capabilities.schemas import DeviceAddress, Switchable, Dimmable, ColorControl


class STSwitchAdapter(Switchable):
    def turn_on(self, address: DeviceAddress) -> Dict[str, Any]:
        return device_commands(settings.smartthings_token or "", address.external_id, [{"component": "main", "capability": "switch", "command": "on"}])

    def turn_off(self, address: DeviceAddress) -> Dict[str, Any]:
        return device_commands(settings.smartthings_token or "", address.external_id, [{"component": "main", "capability": "switch", "command": "off"}])

    def get_state(self, address: DeviceAddress) -> Dict[str, Any]:
        return device_status(settings.smartthings_token or "", address.external_id)


class STDimmableAdapter(STSwitchAdapter, Dimmable):
    def set_brightness(self, address: DeviceAddress, level: int) -> Dict[str, Any]:
        lvl = max(0, min(100, int(level)))
        return device_commands(
            settings.smartthings_token or "",
            address.external_id,
            [{"component": "main", "capability": "switchLevel", "command": "setLevel", "arguments": [lvl]}],
        )


class STColorControlAdapter(STDimmableAdapter, ColorControl):
    def set_color_hsv(self, address: DeviceAddress, h: float, s: float, v: float) -> Dict[str, Any]:
        # SmartThings color commands often accept a map; use setColor with HSV
        payload = {"hue": float(h), "saturation": float(s), "level": float(v)}
        return device_commands(
            settings.smartthings_token or "",
            address.external_id,
            [{"component": "main", "capability": "colorControl", "command": "setColor", "arguments": [payload]}],
        )

    def set_color_temp(self, address: DeviceAddress, mireds: int) -> Dict[str, Any]:
        # ST uses Kelvin typically; convert mireds to kelvin if needed: K = 1e6 / mireds
        kelvin = int(round(1000000.0 / max(1, int(mireds))))
        return device_commands(
            settings.smartthings_token or "",
            address.external_id,
            [{"component": "main", "capability": "colorTemperature", "command": "setColorTemperature", "arguments": [kelvin]}],
        )

