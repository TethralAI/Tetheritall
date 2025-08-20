from __future__ import annotations

from typing import Any, Dict, List


async def discover_devices() -> List[Dict[str, Any]]:
    try:
        from kasa import Discover  # type: ignore
    except Exception:
        return []
    devices: List[Dict[str, Any]] = []
    found = await Discover.discover()
    for addr, dev in (found or {}).items():
        await dev.update()
        devices.append({
            "host": addr,
            "alias": getattr(dev, "alias", addr),
            "is_on": getattr(dev, "is_on", None),
            "device_type": dev.__class__.__name__,
        })
    return devices


async def _set_state_async(host: str, on: bool) -> Dict[str, Any]:
    try:
        from kasa import SmartDevice  # type: ignore
    except Exception as exc:
        return {"ok": False, "error": f"python-kasa missing: {exc}"}
    dev = SmartDevice(host)
    await dev.update()
    if on:
        await dev.turn_on()
    else:
        await dev.turn_off()
    await dev.update()
    return {"ok": True, "is_on": getattr(dev, "is_on", None)}


def set_state(host: str, on: bool) -> Dict[str, Any]:
    try:
        import asyncio as _a
        return _a.run(_set_state_async(host, on))
    except RuntimeError:
        # If event loop running, create new loop in thread
        import threading
        result: Dict[str, Any] = {}

        def _runner():
            nonlocal result
            import asyncio as _a2
            result = _a2.run(_set_state_async(host, on))

        t = threading.Thread(target=_runner)
        t.start()
        t.join()
        return result

