from __future__ import annotations

import hmac
import hashlib
import base64
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request, HTTPException

from config.settings import settings
from storage.twins import store as twin_store
from tools.events.bus import bus
from api.webhook_security import verify_hmac_base64, seen_event

try:
    import redis  # type: ignore
except Exception:
    redis = None


router = APIRouter()

_rds = redis.Redis.from_url(settings.redis_url) if settings.redis_url and redis is not None else None


def _dlq_push(item: Dict[str, Any]) -> None:
    try:
        if _rds:
            import json as _j
            _rds.lpush("st:dlq", _j.dumps(item))
            _rds.ltrim("st:dlq", 0, 999)
    except Exception:
        pass


@router.post("/integrations/smartthings/webhook")
async def smartthings_webhook(request: Request) -> Dict[str, Any]:
    # SmartThings app verification and event delivery
    raw = await request.body()
    sig = request.headers.get("X-ST-Signature", "")
    if settings.smartthings_client_secret and not verify_hmac_base64(settings.smartthings_client_secret, raw, sig):
        raise HTTPException(status_code=401, detail="invalid signature")

    payload = await request.json()
    # App verification challenge
    if payload.get("lifecycle") == "CONFIRMATION":
        data = payload.get("confirmationData") or {}
        return {"confirmationResponse": {"confirmationUrl": data.get("confirmationUrl", "")}}

    # Event handling
    events: List[Dict[str, Any]] = (payload.get("eventData") or {}).get("events", [])
    for e in events:
        try:
            dev = e.get("deviceEvent") or {}
            if seen_event(dev.get("eventId", ""), ttl=300, prefix="st"):
                continue
            # Publish to event bus
            bus.publish("smartthings.device_event", dev)
            device_id = dev.get("deviceId")
            name = dev.get("displayName")
            capability = dev.get("capability")
            value = dev.get("value")
            if device_id:
                # Upsert minimal twin
                caps = [capability] if capability else []
                state = {capability: value} if capability else {}
                twin_store.upsert("smartthings", device_id, name, caps, state)
        except Exception as exc:
            _dlq_push({"error": str(exc), "event": e})
    return {"ok": True}

