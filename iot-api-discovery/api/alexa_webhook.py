from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from typing import Any, Dict

from config.settings import settings
from api.webhook_security import verify_hmac_hex, seen_event


router = APIRouter()


@router.post("/integrations/alexa/webhook")
async def alexa_webhook(request: Request) -> Dict[str, Any]:
    secret = settings.alexa_skill_secret
    body = await request.body()
    sig = request.headers.get("X-Signature", "")
    if secret and not verify_hmac_hex(secret, body, sig):
        raise HTTPException(status_code=401, detail="invalid signature")
    payload = await request.json()
    message_id = (
        payload.get("directive", {})
        .get("header", {})
        .get("messageId", "")
    )
    if seen_event(message_id, ttl=300, prefix="alexa"):
        return {"ok": True}
    # Minimal Smart Home response stub
    return {
        "event": {
            "header": {"namespace": "Alexa", "name": "Response", "messageId": message_id},
            "payload": {},
        }
    }

