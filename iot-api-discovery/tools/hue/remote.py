from __future__ import annotations

from typing import Any, Dict, List
import requests


def list_resources(token: str) -> List[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}", "hue-application-key": token}
    url = "https://api.meethue.com/route/clip/v2/resource"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.ok:
            data = r.json()
            return data.get("data", []) if isinstance(data, dict) else []
    except Exception:
        return []
    return []

