from __future__ import annotations

from typing import Any, Dict, List
import requests


def list_devices(api_token: str) -> List[Dict[str, Any]]:
    """List SmartThings devices via Cloud API (stub call)."""
    headers = {"Authorization": f"Bearer {api_token}"}
    try:
        r = requests.get("https://api.smartthings.com/v1/devices", headers=headers, timeout=10)
        if r.ok:
            return r.json().get("items", [])
    except Exception:
        return []
    return []

