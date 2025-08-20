from __future__ import annotations

from typing import Any, Dict, Optional
import requests


def probe_hubitat_http(host: str, ports: list[int] | None = None, timeout: int = 5) -> Optional[Dict[str, Any]]:
    """Probe Hubitat Elevation hub local interface."""
    ports = ports or [80, 8080]
    headers = {"User-Agent": "IoT-Discovery/1.0"}
    for port in ports:
        base = f"http://{host}:{port}"
        try:
            r = requests.get(base + "/hub/diagnostic", headers=headers, timeout=timeout)
            if r.ok and "hubitat" in r.text.lower():
                return {"type": "hubitat", "host": host, "port": port, "base_url": base}
        except Exception:
            pass
        try:
            r = requests.get(base + "/", headers=headers, timeout=timeout)
            if r.ok and "hubitat" in r.text.lower():
                return {"type": "hubitat", "host": host, "port": port, "base_url": base}
        except Exception:
            pass
    return None

