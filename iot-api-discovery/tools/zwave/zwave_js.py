from __future__ import annotations

from typing import Any, Dict, Optional
import requests


def probe_zwave_js_ws(host: str, port: int = 3000, timeout: int = 5) -> Optional[Dict[str, Any]]:
    """Probe a Z-Wave JS server (often behind Home Assistant addon) via HTTP ping.

    While the main API is WebSocket, many installations expose an HTTP status or
    info endpoint via an add-on proxy. This function best-effort checks known paths.
    """
    candidates = [
        f"http://{host}:{port}/health",
        f"http://{host}:{port}/api",
        f"http://{host}:{port}/",
    ]
    headers = {"User-Agent": "IoT-Discovery/1.0"}
    for url in candidates:
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            if r.ok or r.status_code in (401, 403):
                text = r.text.lower()
                if "zwave" in text or "zwave-js" in text or "zwave_js" in text:
                    return {"type": "zwave-js", "host": host, "port": port, "url": url}
        except Exception:
            continue
    return None

