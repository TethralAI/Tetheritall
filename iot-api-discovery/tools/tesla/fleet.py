from __future__ import annotations

from typing import Any, Dict, List
import requests


def list_vehicles(access_token: str, timeout: int = 15) -> List[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.get("https://fleet-api.prd.vn.cloud.tesla.com/api/1/vehicles", headers=headers, timeout=timeout)
    r.raise_for_status()
    return (r.json() or {}).get("response", [])


def vehicle_data(access_token: str, vehicle_id: str, timeout: int = 15) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.get(f"https://fleet-api.prd.vn.cloud.tesla.com/api/1/vehicles/{vehicle_id}/vehicle_data", headers=headers, timeout=timeout)
    r.raise_for_status()
    return (r.json() or {}).get("response", {})


def start_charge(access_token: str, vehicle_id: str, timeout: int = 15) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.post(f"https://fleet-api.prd.vn.cloud.tesla.com/api/1/vehicles/{vehicle_id}/command/charge_start", headers=headers, timeout=timeout)
    return r.json() if r.ok else {"ok": False, "status": r.status_code}


def stop_charge(access_token: str, vehicle_id: str, timeout: int = 15) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.post(f"https://fleet-api.prd.vn.cloud.tesla.com/api/1/vehicles/{vehicle_id}/command/charge_stop", headers=headers, timeout=timeout)
    return r.json() if r.ok else {"ok": False, "status": r.status_code}

