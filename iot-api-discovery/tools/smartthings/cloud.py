from __future__ import annotations

from typing import Any, Dict, List
import requests


def list_devices(api_token: str) -> List[Dict[str, Any]]:
    """List SmartThings devices via Cloud API (stub call)."""
    headers = {"Authorization": f"Bearer {api_token}"}
    try:
        r = requests.get("https://api.smartthings.com/v1/devices", headers=headers, timeout=10)
        if r.ok:
            return r.json().get("items", [])
    except Exception:
        return []
    return []


def device_commands(api_token: str, device_id: str, commands: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Send commands to a SmartThings device.

    commands: [{"component": "main", "capability": "switch", "command": "on"}]
    """
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    url = f"https://api.smartthings.com/v1/devices/{device_id}/commands"
    try:
        r = requests.post(url, headers=headers, json={"commands": commands}, timeout=10)
        return {"ok": r.ok, "status": r.status_code, "json": r.json() if r.ok else r.text}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

