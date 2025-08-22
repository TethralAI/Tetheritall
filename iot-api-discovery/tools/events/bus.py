from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional, Tuple

from config.settings import settings

try:
    import redis  # type: ignore
except Exception:
    redis = None


STREAM_KEY = "events:stream"


class EventBus:
    def __init__(self) -> None:
        self._rds = redis.Redis.from_url(settings.redis_url) if settings.redis_url and redis is not None else None

    def publish(self, topic: str, payload: Dict[str, Any]) -> Optional[str]:
        if not self._rds:
            return None
        try:
            data = {"topic": topic, "ts": int(time.time()), "payload": json.dumps(payload)}
            return self._rds.xadd(STREAM_KEY, data)
        except Exception:
            return None

    def ensure_consumer_group(self, group: str) -> None:
        if not self._rds:
            return
        try:
            self._rds.xgroup_create(name=STREAM_KEY, groupname=group, id="$", mkstream=True)
        except Exception:
            # group may exist
            pass

    def read_group(self, group: str, consumer: str, count: int = 10, block_ms: int = 1000) -> List[Tuple[str, Dict[bytes, bytes]]]:
        if not self._rds:
            return []
        try:
            res = self._rds.xreadgroup(group, consumer, {STREAM_KEY: ">"}, count=count, block=block_ms)
            if not res:
                return []
            # res is list of (stream, [(id, {field: value})...])
            _, entries = res[0]
            return entries
        except Exception:
            return []

    def ack(self, group: str, entry_id: str) -> None:
        if not self._rds:
            return
        try:
            self._rds.xack(STREAM_KEY, group, entry_id)
        except Exception:
            pass


bus = EventBus()