from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional

from config.settings import settings

try:
    import redis  # type: ignore
except Exception:
    redis = None

try:
    from database.api_database import get_session_factory
    from database.models import DeviceTwin as DeviceTwinModel
except Exception:
    get_session_factory = None  # type: ignore
    DeviceTwinModel = None  # type: ignore


class TwinStore:
    def __init__(self) -> None:
        self._mem: Dict[str, Dict[str, Any]] = {}
        self._rds = redis.Redis.from_url(settings.redis_url) if settings.redis_url and redis is not None else None
        self._SessionFactory = get_session_factory(settings.database_url) if get_session_factory else None

    def _key(self, provider: str, external_id: str) -> str:
        return f"twin:{provider.lower()}:{external_id}"

    def upsert(self, provider: str, external_id: str, name: Optional[str], capabilities: list[str] | None, state: Dict[str, Any] | None) -> None:
        now = int(time.time())
        k = self._key(provider, external_id)
        existing = self.get(provider, external_id) or {}
        version = int(existing.get("_v", 0)) + 1
        doc = {
            "_v": version,
            "_ts": now,
            "provider": provider,
            "external_id": external_id,
            "name": name,
            "capabilities": capabilities or [],
            "state": state or {},
        }
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
        # Fallback to Postgres if available
        if self._SessionFactory and DeviceTwinModel is not None:
            from contextlib import contextmanager
            try:
                session = self._SessionFactory()
                try:
                    twin = (
                        session.query(DeviceTwinModel)
                        .filter(DeviceTwinModel.provider == provider, DeviceTwinModel.external_id == external_id)
                        .one_or_none()
                    )
                    if twin is None:
                        return None
                    # Build doc from DB
                    caps = []
                    try:
                        caps = json.loads(twin.capabilities) if twin.capabilities else []
                    except Exception:
                        caps = []
                    state = {}
                    try:
                        state = json.loads(twin.state) if twin.state else {}
                    except Exception:
                        state = {}
                    doc = {
                        "_v": int(twin.version or 1),
                        "_ts": int(time.time()),
                        "provider": twin.provider,
                        "external_id": twin.external_id,
                        "name": twin.name,
                        "capabilities": caps,
                        "state": state,
                    }
                    # warm caches
                    self._mem[k] = doc
                    if self._rds:
                        try:
                            self._rds.set(k, json.dumps(doc))
                        except Exception:
                            pass
                    return doc
                finally:
                    session.close()
            except Exception:
                return None
        return None


store = TwinStore()

