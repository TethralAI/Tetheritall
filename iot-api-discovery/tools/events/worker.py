from __future__ import annotations

import asyncio
import json
from typing import Any, Dict

from tools.events.bus import bus

GROUP = "workers"
CONSUMER = "worker-1"


async def process_event(event: Dict[str, Any]) -> None:
    topic = event.get("topic")
    payload = event.get("payload", {})
    try:
        if isinstance(payload, str):
            payload = json.loads(payload)
    except Exception:
        payload = {}
    # Route by topic
    if topic == "smartthings.device_event":
        # no-op placeholder; future: trigger rules, persist state, etc.
        return


async def run_worker() -> None:
    bus.ensure_consumer_group(GROUP)
    while True:
        entries = bus.read_group(GROUP, CONSUMER, count=10, block_ms=1000)
        for entry_id, fields in entries:
            try:
                event = {k.decode(): v.decode() if isinstance(v, bytes) else v for k, v in fields.items()}
                await process_event(event)
                bus.ack(GROUP, entry_id)
            except Exception:
                # Leave unacked for redelivery or move to DLQ in future
                pass
        await asyncio.sleep(0.1)


if __name__ == "__main__":
    asyncio.run(run_worker())