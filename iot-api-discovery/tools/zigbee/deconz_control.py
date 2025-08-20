from __future__ import annotations

from typing import Any, Dict
import requests


def toggle_light(base_url: str, api_key: str, light_id: str, on: bool) -> Dict[str, Any]:
    url = f"{base_url}/api/{api_key}/lights/{light_id}/state"
    try:
        r = requests.put(url, json={"on": on}, timeout=8)
        return {"ok": r.ok, "status": r.status_code, "json": r.json() if r.ok else r.text}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

