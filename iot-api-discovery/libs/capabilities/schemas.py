from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable, Dict, Any, Optional


class CapabilityType(str, Enum):
    SWITCHABLE = "switchable"
    DIMMABLE = "dimmable"
    COLOR_CONTROL = "color_control"
    THERMOSTAT = "thermostat"
    COVER = "cover"
    FAN = "fan"
    MEDIA = "media"


@dataclass
class DeviceAddress:
    provider: str
    external_id: str


@runtime_checkable
class Switchable(Protocol):
    def turn_on(self, address: DeviceAddress) -> Dict[str, Any]:
        ...

    def turn_off(self, address: DeviceAddress) -> Dict[str, Any]:
        ...

    def get_state(self, address: DeviceAddress) -> Dict[str, Any]:
        ...


@runtime_checkable
class Dimmable(Switchable, Protocol):
    def set_brightness(self, address: DeviceAddress, level: int) -> Dict[str, Any]:
        ...


@runtime_checkable
class ColorControl(Dimmable, Protocol):
    def set_color_hsv(self, address: DeviceAddress, h: float, s: float, v: float) -> Dict[str, Any]:
        ...

    def set_color_temp(self, address: DeviceAddress, mireds: int) -> Dict[str, Any]:
        ...


@runtime_checkable
class Thermostat(Protocol):
    def set_mode(self, address: DeviceAddress, mode: str) -> Dict[str, Any]:
        ...

    def set_cooling_setpoint(self, address: DeviceAddress, celsius: float) -> Dict[str, Any]:
        ...

    def set_heating_setpoint(self, address: DeviceAddress, celsius: float) -> Dict[str, Any]:
        ...

    def get_status(self, address: DeviceAddress) -> Dict[str, Any]:
        ...


@runtime_checkable
class Cover(Protocol):
    def open(self, address: DeviceAddress) -> Dict[str, Any]:
        ...

    def close(self, address: DeviceAddress) -> Dict[str, Any]:
        ...

    def set_position(self, address: DeviceAddress, percent: int) -> Dict[str, Any]:
        ...


@runtime_checkable
class Fan(Protocol):
    def set_speed(self, address: DeviceAddress, percent: int) -> Dict[str, Any]:
        ...


@runtime_checkable
class Media(Protocol):
    def play(self, address: DeviceAddress) -> Dict[str, Any]:
        ...

    def pause(self, address: DeviceAddress) -> Dict[str, Any]:
        ...

    def set_volume(self, address: DeviceAddress, percent: int) -> Dict[str, Any]:
        ...


