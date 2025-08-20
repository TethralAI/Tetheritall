from __future__ import annotations

from typing import Any, Dict
import requests


def device_command(base_url: str, access_token: str, device_id: str, command: str) -> Dict[str, Any]:
    url = f"{base_url}/apps/api/devices/{device_id}/{command}?access_token={access_token}"
    try:
        r = requests.get(url, timeout=8)
        return {"ok": r.ok, "status": r.status_code, "text": r.text[:2048]}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

