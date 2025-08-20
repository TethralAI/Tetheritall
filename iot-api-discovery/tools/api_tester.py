from __future__ import annotations

from typing import Any, Dict, Optional

import requests


def test_http_endpoint(url: str, method: str = "GET", timeout: int = 5) -> Dict[str, Any]:
    try:
        response = requests.request(method=method, url=url, timeout=timeout)
        return {"url": url, "status": response.status_code, "ok": response.ok}
    except requests.RequestException as exc:
        return {"url": url, "error": str(exc), "ok": False}

