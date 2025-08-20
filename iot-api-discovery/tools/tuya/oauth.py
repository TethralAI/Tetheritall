from __future__ import annotations

from typing import Dict
import requests


def build_auth_url(client_id: str, redirect_uri: str, region: str = "us") -> str:
    base = f"https://openapi.tuya{region}.com" if region != "us" else "https://openapi.tuyaus.com"
    # Placeholder: Tuya OAuth URL varies; return a draft
    return f"{base}/v1.0/auth?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code"


def exchange_code_for_token(client_id: str, client_secret: str, code: str, redirect_uri: str) -> Dict:
    # Placeholder: Tuya OAuth varies by region/account; attempt a generic exchange endpoint
    url = "https://openapi.tuyaus.com/v1.0/token?grant_type=1"
    headers = {"client_id": client_id, "sign_method": "HMAC-SHA256"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        return r.json() if r.ok else {"error": r.text}
    except Exception as exc:
        return {"error": str(exc)}

