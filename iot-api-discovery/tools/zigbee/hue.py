from __future__ import annotations

from typing import Any, Dict, List, Optional
import requests


def probe_hue_http(host: str, port: int = 80, timeout: int = 5) -> Optional[Dict[str, Any]]:
    base = f"http://{host}:{port}"
    try:
        r = requests.get(base + "/description.xml", timeout=timeout)
        text = r.text.lower()
        if "philips hue" in text or "hue bridge" in text:
            return {"type": "hue", "host": host, "port": port, "base_url": base}
    except Exception:
        pass
    try:
        # Some bridges expose /api/config (will require pairing for full data)
        r = requests.get(base + "/api/config", timeout=timeout)
        if r.status_code in (200, 401, 403) and "whitelist" in r.text.lower():
            return {"type": "hue", "host": host, "port": port, "base_url": base}
    except Exception:
        pass
    return None

