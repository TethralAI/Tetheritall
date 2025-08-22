from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, Optional

from config.settings import settings
from tools.events.bus import bus

try:
    import redis  # type: ignore
except Exception:
    redis = None


QUEUE_KEY = "st:dlq"


class SmartThingsDLQConsumer:
    def __init__(self) -> None:
        self._rds = redis.Redis.from_url(settings.redis_url) if settings.redis_url and redis is not None else None

    def _pop(self, timeout: int = 5) -> Optional[Dict[str, Any]]:
        if not self._rds:
            return None
        try:
            res = self._rds.brpop(QUEUE_KEY, timeout=timeout)
            if not res:
                return None
            _, raw = res
            try:
                return json.loads(raw)
            except Exception:
                return None
        except Exception:
            return None

    def _requeue(self, item: Dict[str, Any]) -> None:
        if not self._rds:
            return
        try:
            self._rds.lpush(QUEUE_KEY, json.dumps(item))
            self._rds.ltrim(QUEUE_KEY, 0, 999)
        except Exception:
            pass

    async def run(self) -> None:
        backoff_seconds = 1.0
        while True:
            item = self._pop(timeout=5)
            if not item:
                await asyncio.sleep(0.1)
                continue
            event = item.get("event") or {}
            attempts = int(item.get("attempts", 0))
            published_id = None
            try:
                published_id = bus.publish("smartthings.device_event", event)
            except Exception:
                published_id = None
            if published_id:
                backoff_seconds = 1.0
                continue
            # publish failed: backoff and requeue with attempts
            attempts += 1
            item["attempts"] = attempts
            # cap backoff
            backoff_seconds = min(backoff_seconds * 2.0, 30.0)
            await asyncio.sleep(backoff_seconds)
            self._requeue(item)


async def main() -> None:
    consumer = SmartThingsDLQConsumer()
    await consumer.run()


if __name__ == "__main__":
    asyncio.run(main())