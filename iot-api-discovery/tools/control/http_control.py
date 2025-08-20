from __future__ import annotations

from typing import Any, Dict, Optional
import requests


def invoke_http(endpoint: Dict[str, Any], payload: Optional[Dict[str, Any]] = None, timeout: int = 8) -> Dict[str, Any]:
    url = endpoint.get("url") or endpoint.get("full_url") or endpoint.get("path")
    method = (endpoint.get("method") or "GET").upper()
    if not url:
        raise ValueError("endpoint missing url/path")
    try:
        r = requests.request(method=method, url=url, json=payload, timeout=timeout)
        return {"ok": r.ok, "status": r.status_code, "text": r.text[:2048]}
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc)}

