from __future__ import annotations

from typing import Any, Dict, List
import requests


def list_entities(base_url: str, token: str) -> List[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"}
    url = base_url.rstrip("/") + "/api/states"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.ok:
            return r.json()
    except Exception:
        return []
    return []


def call_service(base_url: str, token: str, domain: str, service: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = base_url.rstrip("/") + f"/api/services/{domain}/{service}"
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        return {"ok": r.ok, "status": r.status_code, "json": r.json() if r.ok else r.text}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

