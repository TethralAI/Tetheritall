from __future__ import annotations

from typing import Any, Dict
import requests
import urllib.parse


def build_auth_url(client_id: str, redirect_uri: str, scope: str = "offline_access read_glycemic") -> str:
    base = "https://sandbox-api.dexcom.com/v2/oauth2/login"
    q = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
    }
    return f"{base}?{urllib.parse.urlencode(q)}"


def exchange_code(client_id: str, client_secret: str, redirect_uri: str, code: str) -> Dict[str, Any]:
    url = "https://sandbox-api.dexcom.com/v2/oauth2/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "code": code,
    }
    r = requests.post(url, data=data, timeout=15)
    return r.json() if r.ok else {"error": r.text}


def egvs(access_token: str, start: str, end: str) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"https://sandbox-api.dexcom.com/v2/users/self/egvs?startDate={urllib.parse.quote(start)}&endDate={urllib.parse.quote(end)}"
    r = requests.get(url, headers=headers, timeout=15)
    return r.json() if r.ok else {"error": r.text}

