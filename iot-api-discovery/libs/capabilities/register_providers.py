from __future__ import annotations

from .registry import registry
from .schemas import CapabilityType


def register_all() -> None:
    try:
        from tools.smartthings.adapters import STSwitchAdapter, STDimmableAdapter, STColorControlAdapter

        registry.register("smartthings", CapabilityType.SWITCHABLE, STSwitchAdapter())
        registry.register("smartthings", CapabilityType.DIMMABLE, STDimmableAdapter())
        registry.register("smartthings", CapabilityType.COLOR_CONTROL, STColorControlAdapter())
    except Exception:
        # Adapters optional
        pass

    try:
        from tools.zigbee.adapters import Z2MSwitchAdapter, Z2MDimmableAdapter, Z2MColorControlAdapter

        registry.register("zigbee2mqtt", CapabilityType.SWITCHABLE, Z2MSwitchAdapter())
        registry.register("zigbee2mqtt", CapabilityType.DIMMABLE, Z2MDimmableAdapter())
        registry.register("zigbee2mqtt", CapabilityType.COLOR_CONTROL, Z2MColorControlAdapter())
    except Exception:
        pass

    try:
        from tools.hue.adapters import HueSwitchAdapter, HueDimmableAdapter, HueColorControlAdapter

        registry.register("hue", CapabilityType.SWITCHABLE, HueSwitchAdapter())
        registry.register("hue", CapabilityType.DIMMABLE, HueDimmableAdapter())
        registry.register("hue", CapabilityType.COLOR_CONTROL, HueColorControlAdapter())
    except Exception:
        # Hue adapters optional
        pass

