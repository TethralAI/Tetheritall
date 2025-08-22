from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException
import requests

from config.settings import settings


router = APIRouter()


@router.post("/integrations/smartthings/subscriptions/create")
def st_create_subscription(app_id: str, location_id: str, callback_url: str) -> Dict[str, Any]:
    token = settings.smartthings_token or ""
    if not token:
        raise HTTPException(status_code=400, detail="missing smartthings token")
    url = f"https://api.smartthings.com/v1/apps/{app_id}/subscriptions"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {"sourceType": "DEVICE", "device": {"all": True}, "notificationUrl": callback_url, "locationId": location_id}
    r = requests.post(url, headers=headers, json=body, timeout=15)
    return {"ok": r.ok, "status": r.status_code, "json": r.json() if r.ok else r.text}


@router.get("/integrations/smartthings/subscriptions")
def st_list_subscriptions(app_id: str) -> Dict[str, Any]:
    token = settings.smartthings_token or ""
    if not token:
        raise HTTPException(status_code=400, detail="missing smartthings token")
    url = f"https://api.smartthings.com/v1/apps/{app_id}/subscriptions"
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers, timeout=15)
    return {"ok": r.ok, "status": r.status_code, "json": r.json() if r.ok else r.text}

