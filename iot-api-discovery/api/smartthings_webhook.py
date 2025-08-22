from __future__ import annotations

import hmac
import hashlib
import base64
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request, HTTPException

from config.settings import settings
from storage.twins import store as twin_store

try:
    import redis  # type: ignore
except Exception:
    redis = None


router = APIRouter()

_rds = redis.Redis.from_url(settings.redis_url) if settings.redis_url and redis is not None else None
_seen_mem: dict[str, int] = {}


def _verify_signature(secret: str, body: bytes, signature: str) -> bool:
    if not secret:
        return True
    mac = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    expected = base64.b64encode(mac).decode()
    try:
        return hmac.compare_digest(expected, signature or "")
    except Exception:
        return False


def _seen(event_id: str, ttl: int = 300) -> bool:
    if not event_id:
        return False
    key = f"st:event:{event_id}"
    try:
        if _rds:
            if _rds.setnx(key, 1):
                _rds.expire(key, ttl)
                return False
            return True
    except Exception:
        pass
    # fallback in-memory
    import time
    now = int(time.time())
    # cleanup occasionally
    for k, v in list(_seen_mem.items()):
        if now - v > ttl:
            _seen_mem.pop(k, None)
    if key in _seen_mem:
        return True
    _seen_mem[key] = now
    return False


@router.post("/integrations/smartthings/webhook")
async def smartthings_webhook(request: Request) -> Dict[str, Any]:
    # SmartThings app verification and event delivery
    body = await request.body()
    sig = request.headers.get("X-ST-Signature", "")
    if settings.smartthings_client_secret and not _verify_signature(settings.smartthings_client_secret, body, sig):
        raise HTTPException(status_code=401, detail="invalid signature")

    payload = await request.json()
    # App verification challenge
    if payload.get("lifecycle") == "CONFIRMATION":
        data = payload.get("confirmationData") or {}
        return {"confirmationResponse": {"confirmationUrl": data.get("confirmationUrl", "")}}

    # Event handling
    events: List[Dict[str, Any]] = (payload.get("eventData") or {}).get("events", [])
    for e in events:
        dev = e.get("deviceEvent") or {}
        if _seen(dev.get("eventId", "")):
            continue
        device_id = dev.get("deviceId")
        name = dev.get("displayName")
        capability = dev.get("capability")
        value = dev.get("value")
        if device_id:
            # Upsert minimal twin
            caps = [capability] if capability else []
            state = {capability: value} if capability else {}
            twin_store.upsert("smartthings", device_id, name, caps, state)
    return {"ok": True}

