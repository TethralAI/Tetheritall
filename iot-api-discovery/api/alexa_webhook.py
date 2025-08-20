from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from typing import Any, Dict
import hmac
import hashlib

from config.settings import settings


router = APIRouter()


def _verify_signature(secret: str, body: bytes, sig: str) -> bool:
    mac = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, sig or "")


@router.post("/integrations/alexa/webhook")
async def alexa_webhook(request: Request) -> Dict[str, Any]:
    secret = settings.alexa_skill_secret
    body = await request.body()
    sig = request.headers.get("X-Signature", "")
    if secret and not _verify_signature(secret, body, sig):
        raise HTTPException(status_code=401, detail="invalid signature")
    # Echo back directive (stub)
    payload = await request.json()
    # Minimal Smart Home response stub
    return {
        "event": {
            "header": {"namespace": "Alexa", "name": "Response", "messageId": payload.get("directive", {}).get("header", {}).get("messageId", "")},
            "payload": {},
        }
    }

