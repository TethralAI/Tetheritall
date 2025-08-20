from __future__ import annotations

import asyncio
import json
from typing import Any, Dict

import websockets


async def ping_version(ws_url: str, timeout: int = 10) -> Dict[str, Any]:
    try:
        async with websockets.connect(ws_url, close_timeout=1) as ws:
            req = {"command": "version"}
            await ws.send(json.dumps(req))
            resp = await asyncio.wait_for(ws.recv(), timeout=timeout)
            data = json.loads(resp)
            return {"ok": True, "data": data}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

