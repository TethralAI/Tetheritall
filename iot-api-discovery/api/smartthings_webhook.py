from __future__ import annotations

import hmac
import hashlib
import base64
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request, HTTPException

from config.settings import settings
from storage.twins import store as twin_store


router = APIRouter()


def _verify_signature(secret: str, body: bytes, signature: str) -> bool:
    if not secret:
        return True
    mac = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    expected = base64.b64encode(mac).decode()
    try:
        return hmac.compare_digest(expected, signature or "")
    except Exception:
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

