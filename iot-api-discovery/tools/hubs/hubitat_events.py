from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict
import requests


async def listen_events_sse(base_url: str, token: str, on_event: Callable[[Dict[str, Any]], None]) -> None:
    url = f"{base_url}/eventsocket?access_token={token}"
    # Fallback to polling if SSE not available
    while True:
        try:
            with requests.get(url, stream=True, timeout=60) as r:
                if r.ok:
                    for line in r.iter_lines():
                        if not line:
                            continue
                        try:
                            text = line.decode("utf-8")
                            if text.startswith("data:"):
                                import json as _json
                                payload = _json.loads(text[5:].strip())
                                on_event(payload)
                        except Exception:
                            pass
                else:
                    await asyncio.sleep(5)
        except Exception:
            await asyncio.sleep(5)

