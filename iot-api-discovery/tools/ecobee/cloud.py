from __future__ import annotations

from typing import Any, Dict, List
import requests


def list_thermostats(api_key: str, access_token: str, timeout: int = 15) -> List[Dict[str, Any]]:
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"}
    body = {
        "selection": {
            "selectionType": "registered",
            "selectionMatch": "",
            "includeRuntime": True,
            "includeSensors": True,
            "includeEquipmentStatus": True,
        }
    }
    r = requests.post("https://api.ecobee.com/1/thermostat", json=body, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.json().get("thermostatList", [])

