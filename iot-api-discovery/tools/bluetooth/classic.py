from __future__ import annotations

from typing import Any, Dict, List


def discover_bt_classic(duration: int = 4) -> List[Dict[str, Any]]:
    """Bluetooth Classic device inquiry and (optional) SDP fetch.

    Returns list of {address, name}. SDP is platform-dependent and omitted here.
    """
    try:
        import bluetooth  # pybluez  # type: ignore
    except Exception:
        return []
    try:
        found = bluetooth.discover_devices(duration=duration, lookup_names=True)
        return [{"address": addr, "name": name} for addr, name in found]
    except Exception:
        return []

