from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Callable
from tools.smartthings.cloud import list_devices, device_status


async def poll_devices_forever(token: str, on_state: Callable[[str, Dict[str, Any]], None], interval_seconds: int = 30) -> None:
    while True:
        try:
            devices: List[Dict[str, Any]] = await asyncio.to_thread(list_devices, token)
            for d in devices or []:
                device_id = d.get("deviceId") or d.get("device_id") or ""
                if not device_id:
                    continue
                state = await asyncio.to_thread(device_status, token, device_id)
                on_state(device_id, state)
        except Exception:
            pass
        await asyncio.sleep(interval_seconds)

