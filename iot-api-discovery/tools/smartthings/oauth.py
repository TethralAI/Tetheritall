from __future__ import annotations

from typing import Dict
import requests


def build_auth_url(client_id: str, redirect_uri: str, scope: str = "devices:read devices:write") -> str:
    return (
        "https://api.smartthings.com/oauth/authorize?response_type=code"
        f"&client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}"
    )


def exchange_code_for_token(client_id: str, client_secret: str, redirect_uri: str, code: str) -> Dict:
    url = "https://api.smartthings.com/oauth/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "code": code,
    }
    try:
        r = requests.post(url, data=data, timeout=10)
        return r.json() if r.ok else {"error": r.text}
    except Exception as exc:
        return {"error": str(exc)}

