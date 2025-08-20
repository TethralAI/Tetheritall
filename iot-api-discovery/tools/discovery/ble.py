from __future__ import annotations

from typing import Any, Dict, List


def discover_ble(timeout_seconds: int = 5) -> List[Dict[str, Any]]:
    """Discover nearby BLE devices (requires bluez/bleak support)."""
    try:
        from bleak import BleakScanner  # type: ignore
    except Exception:
        return []

    devices = []
    try:
        found = BleakScanner.discover(timeout=timeout_seconds)
        for d in found:
            devices.append({"address": getattr(d, "address", None), "name": getattr(d, "name", None)})
    except Exception:
        return []
    return devices

