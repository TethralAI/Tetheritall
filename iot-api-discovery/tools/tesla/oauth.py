from __future__ import annotations

from typing import Dict
import urllib.parse
import requests


def build_auth_url(client_id: str, redirect_uri: str, scope: str = "openid offline_access vehicle_device_data vehicle_cmds") -> str:
    base = "https://auth.tesla.com/oauth2/v3/authorize"
    q = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "prompt": "login",
    }
    return f"{base}?{urllib.parse.urlencode(q)}"


def exchange_code_for_token(client_id: str, client_secret: str, redirect_uri: str, code: str) -> Dict[str, str]:
    url = "https://auth.tesla.com/oauth2/v3/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "code": code,
    }
    try:
        r = requests.post(url, data=data, timeout=20)
        return r.json() if r.ok else {"error": r.text}
    except Exception as exc:
        return {"error": str(exc)}

