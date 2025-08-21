from __future__ import annotations

import json
import time
from typing import Any, Dict

from config.settings import settings

try:
    import redis  # type: ignore
except Exception:
    redis = None


class TelemetryTracker:
    def __init__(self) -> None:
        self._rds = redis.Redis.from_url(settings.redis_url) if settings.redis_url and redis is not None else None

    def track(self, event: str, payload: Dict[str, Any]) -> None:
        if not settings.telemetry_opt_in:
            return
        try:
            ns = settings.telemetry_namespace or "iot"
            key = f"telemetry:{ns}:{event}:{time.strftime('%Y%m%d')}"
            doc = {"ts": int(time.time()), **payload}
            if self._rds:
                self._rds.lpush(key, json.dumps(doc))
                self._rds.ltrim(key, 0, 999)
        except Exception:
            pass


tracker = TelemetryTracker()

