from __future__ import annotations

from typing import Any, Dict, List
import requests


def send_fcm_legacy(server_key: str, token: str, title: str, body: str, data: Dict[str, Any] | None = None) -> Dict[str, Any]:
    headers = {
        "Authorization": f"key={server_key}",
        "Content-Type": "application/json",
    }
    payload = {"to": token, "notification": {"title": title, "body": body}, "data": data or {}}
    try:
        r = requests.post("https://fcm.googleapis.com/fcm/send", headers=headers, json=payload, timeout=10)
        return {"ok": r.ok, "status": r.status_code, "json": r.json() if r.ok else r.text}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

