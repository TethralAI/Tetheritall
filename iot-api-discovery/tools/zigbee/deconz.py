from __future__ import annotations

from typing import Any, Dict, Optional
import requests


def probe_deconz_http(host: str, ports: list[int] | None = None, timeout: int = 5) -> Optional[Dict[str, Any]]:
    """Probe deCONZ/Phoscon REST API (Zigbee) via HTTP.

    Known indicators:
    - GET /api/config returns JSON (requires API key for details but may return structure)
    - Root page mentions "Phoscon"/"deCONZ"
    """
    ports = ports or [80, 8080, 8443]
    headers = {"User-Agent": "IoT-Discovery/1.0"}
    for port in ports:
        base = f"http://{host}:{port}"
        try:
            r = requests.get(base + "/api/config", headers=headers, timeout=timeout)
            if r.status_code in (200, 401, 403):
                text = r.text.lower()
                if any(k in text for k in ("deconz", "phoscon", "bridgeid")):
                    return {"type": "deconz", "host": host, "port": port, "base_url": base}
        except Exception:
            pass
        try:
            r = requests.get(base + "/", headers=headers, timeout=timeout)
            if r.ok:
                t = r.text.lower()
                if "phoscon" in t or "deconz" in t:
                    return {"type": "deconz", "host": host, "port": port, "base_url": base}
        except Exception:
            pass
    return None

