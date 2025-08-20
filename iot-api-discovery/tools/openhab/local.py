from __future__ import annotations

from typing import Any, Dict, List
import requests


def list_items(base_url: str, token: str | None = None) -> List[Dict[str, Any]]:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = base_url.rstrip("/") + "/rest/items"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.ok:
            return r.json()
    except Exception:
        return []
    return []


def send_command(base_url: str, item: str, command: str, token: str | None = None) -> Dict[str, Any]:
    headers = {"Content-Type": "text/plain"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = base_url.rstrip("/") + f"/rest/items/{item}"
    try:
        r = requests.post(url, headers=headers, data=command, timeout=10)
        return {"ok": r.ok, "status": r.status_code}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

