from __future__ import annotations

import base64
import hashlib
import hmac
import time
from typing import Any

from config.settings import settings

try:
    import redis  # type: ignore
except Exception:
    redis = None


_rds = redis.Redis.from_url(settings.redis_url) if settings.redis_url and redis is not None else None
_seen_mem: dict[str, int] = {}


def verify_hmac_base64(secret: str | None, body: bytes, signature: str | None) -> bool:
    if not secret:
        return True
    if signature is None:
        return False
    mac = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    expected = base64.b64encode(mac).decode()
    try:
        return hmac.compare_digest(expected, signature)
    except Exception:
        return False


def verify_hmac_hex(secret: str | None, body: bytes, signature: str | None) -> bool:
    if not secret:
        return True
    if signature is None:
        return False
    mac = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    try:
        return hmac.compare_digest(mac, signature)
    except Exception:
        return False


def seen_event(event_id: str, ttl: int = 300, prefix: str = "wh") -> bool:
    if not event_id:
        return False
    key = f"{prefix}:event:{event_id}"
    try:
        if _rds:
            if _rds.setnx(key, 1):
                _rds.expire(key, ttl)
                return False
            return True
    except Exception:
        pass
    # fallback in-memory
    now = int(time.time())
    # cleanup occasionally
    for k, v in list(_seen_mem.items()):
        if now - v > ttl:
            _seen_mem.pop(k, None)
    if key in _seen_mem:
        return True
    _seen_mem[key] = now
    return False