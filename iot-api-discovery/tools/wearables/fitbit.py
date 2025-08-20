from __future__ import annotations

from typing import Any, Dict
import requests
import urllib.parse


def build_auth_url(client_id: str, redirect_uri: str, scope: str = "activity heartrate sleep") -> str:
    base = "https://www.fitbit.com/oauth2/authorize"
    q = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "prompt": "login",
    }
    return f"{base}?{urllib.parse.urlencode(q)}"


def exchange_code(client_id: str, client_secret: str, redirect_uri: str, code: str) -> Dict[str, Any]:
    url = "https://api.fitbit.com/oauth2/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code": code,
    }
    auth = requests.auth.HTTPBasicAuth(client_id, client_secret)
    r = requests.post(url, data=data, auth=auth, timeout=15)
    return r.json() if r.ok else {"error": r.text}


def heart_rate_intraday(access_token: str, date: str) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"https://api.fitbit.com/1/user/-/activities/heart/date/{date}/1d/1min.json"
    r = requests.get(url, headers=headers, timeout=15)
    return r.json() if r.ok else {"error": r.text}

