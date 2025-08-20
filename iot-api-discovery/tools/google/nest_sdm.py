from __future__ import annotations

from typing import Any, Dict, List
import requests


def list_devices(access_token: str) -> List[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {access_token}"}
    url = "https://smartdevicemanagement.googleapis.com/v1/enterprises/project-id/devices"
    # Note: SDM requires enterprise/project setup; placeholder URL shows structure.
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.ok:
            return r.json().get("devices", [])
    except Exception:
        return []
    return []

