from __future__ import annotations

import base64
import os
import secrets
import time
from typing import Any, Dict, List
import requests


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def begin_pkce(client_id: str, redirect_uri: str, scope: str = "read_vehicle_info read_battery charge") -> Dict[str, str]:
    verifier = _b64url(os.urandom(32))
    challenge = _b64url(base64.urlsafe_b64encode(verifier.encode()))
    auth_url = (
        "https://connect.smartcar.com/oauth/authorize?response_type=code"
        f"&client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}&mode=test&code_challenge={challenge}&code_challenge_method=plain"
    )
    return {"auth_url": auth_url, "code_verifier": verifier}


def exchange_code(client_id: str, client_secret: str, redirect_uri: str, code: str, code_verifier: str) -> Dict[str, Any]:
    url = "https://auth.smartcar.com/oauth/token"
    data = {
        "code": code,
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
    }
    try:
        r = requests.post(url, data=data, timeout=10)
        return r.json() if r.ok else {"error": r.text}
    except Exception as exc:
        return {"error": str(exc)}


def list_vehicles(access_token: str) -> List[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        r = requests.get("https://api.smartcar.com/v2.0/vehicles", headers=headers, timeout=10)
        if r.ok:
            return r.json().get("vehicles", [])
    except Exception:
        return []
    return []


def vehicle_soc(access_token: str, vehicle_id: str) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        r = requests.get(f"https://api.smartcar.com/v2.0/vehicles/{vehicle_id}/battery", headers=headers, timeout=10)
        return r.json() if r.ok else {"error": r.text}
    except Exception as exc:
        return {"error": str(exc)}


def start_charge(access_token: str, vehicle_id: str) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        r = requests.post(f"https://api.smartcar.com/v2.0/vehicles/{vehicle_id}/charge", headers=headers, timeout=10)
        return {"ok": r.ok, "status": r.status_code}
    except Exception as exc:
        return {"error": str(exc)}


def stop_charge(access_token: str, vehicle_id: str) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        r = requests.delete(f"https://api.smartcar.com/v2.0/vehicles/{vehicle_id}/charge", headers=headers, timeout=10)
        return {"ok": r.ok, "status": r.status_code}
    except Exception as exc:
        return {"error": str(exc)}

