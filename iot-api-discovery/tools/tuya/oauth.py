from __future__ import annotations

from typing import Dict


def build_auth_url(client_id: str, redirect_uri: str, region: str = "us") -> str:
    base = f"https://openapi.tuya{region}.com" if region != "us" else "https://openapi.tuyaus.com"
    # Placeholder: Tuya OAuth URL varies; return a draft
    return f"{base}/v1.0/auth?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code"


def exchange_code_for_token(client_id: str, client_secret: str, code: str, redirect_uri: str) -> Dict:
    # Placeholder: real Tuya OAuth2 exchange requires specific endpoints/signing
    return {"error": "not_implemented"}

