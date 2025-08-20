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


def list_devices_maker(base_url: str, token: str, timeout: int = 10) -> list[dict[str, Any]]:
    url = f"{base_url}/devices?access_token={token}"
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.json() if r.headers.get("content-type", "").startswith("application/json") else []


def device_command_maker(base_url: str, token: str, device_id: str, command: str, args: list[Any] | None = None, timeout: int = 10) -> dict[str, Any]:
    args = args or []
    # Maker API command format: /devices/{id}/{command}/{arg1}/{arg2}
    path = f"/devices/{device_id}/{command}" + ("/" + "/".join(map(str, args)) if args else "")
    url = f"{base_url}{path}?access_token={token}"
    r = requests.get(url, timeout=timeout)
    return {"ok": r.ok, "status": r.status_code}

