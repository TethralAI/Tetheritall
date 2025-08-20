from __future__ import annotations

import asyncio
import json
from typing import Any, Callable, Dict

import websockets


async def connect_and_listen(base_url: str, token: str, on_event: Callable[[Dict[str, Any]], None]) -> None:
    # base_url like http://host:8123
    ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://")
    ws_url = ws_url.rstrip("/") + "/api/websocket"
    while True:
        try:
            async with websockets.connect(ws_url, ping_interval=30) as ws:
                # Receive hello
                await ws.recv()
                # Auth
                await ws.send(json.dumps({"type": "auth", "access_token": token}))
                msg = json.loads(await ws.recv())
                if msg.get("type") != "auth_ok":
                    await asyncio.sleep(5)
                    continue
                # Subscribe to state_changed
                msg_id = 1
                await ws.send(json.dumps({"id": msg_id, "type": "subscribe_events", "event_type": "state_changed"}))
                # Listen
                while True:
                    raw = await ws.recv()
                    try:
                        data = json.loads(raw)
                        if data.get("type") == "event":
                            on_event(data.get("event", {}))
                    except Exception:
                        pass
        except Exception:
            await asyncio.sleep(5)

