from __future__ import annotations

from typing import Any, Dict
import requests
import urllib.parse


def build_auth_url(client_id: str, redirect_uri: str, scope: str = "daily,heartrate,workout") -> str:
    base = "https://cloud.ouraring.com/oauth/authorize"
    q = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
    }
    return f"{base}?{urllib.parse.urlencode(q)}"


def exchange_code(client_id: str, client_secret: str, redirect_uri: str, code: str) -> Dict[str, Any]:
    url = "https://api.ouraring.com/oauth/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "code": code,
    }
    r = requests.post(url, data=data, timeout=15)
    return r.json() if r.ok else {"error": r.text}


def daily_summary(access_token: str) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.get("https://api.ouraring.com/v2/usercollection/daily_summary", headers=headers, timeout=15)
    return r.json() if r.ok else {"error": r.text}

