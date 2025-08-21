from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional

from config.settings import settings

try:
    import redis  # type: ignore
except Exception:
    redis = None


class TwinStore:
    def __init__(self) -> None:
        self._mem: Dict[str, Dict[str, Any]] = {}
        self._rds = redis.Redis.from_url(settings.redis_url) if settings.redis_url and redis is not None else None

    def _key(self, provider: str, external_id: str) -> str:
        return f"twin:{provider.lower()}:{external_id}"

    def upsert(self, provider: str, external_id: str, name: Optional[str], capabilities: list[str] | None, state: Dict[str, Any] | None) -> None:
        doc = {
            "provider": provider,
            "external_id": external_id,
            "name": name,
            "capabilities": capabilities or [],
            "state": state or {},
            "updated_at": int(time.time()),
        }
        k = self._key(provider, external_id)
        self._mem[k] = doc
        if self._rds:
            try:
                self._rds.set(k, json.dumps(doc))
            except Exception:
                pass

    def get(self, provider: str, external_id: str) -> Optional[Dict[str, Any]]:
        k = self._key(provider, external_id)
        if k in self._mem:
            return self._mem[k]
        if self._rds:
            try:
                v = self._rds.get(k)
                if v:
                    doc = json.loads(v)
                    self._mem[k] = doc
                    return doc
            except Exception:
                pass
        return None


store = TwinStore()

