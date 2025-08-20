from __future__ import annotations

from typing import Any, Dict, List, Tuple
import hashlib
import hmac
import json
import time
import requests


def _sign(client_id: str, secret: str, t: str, body: str = "", path: str = "") -> Tuple[str, str]:
    # Tuya V2 sign: stringToSign = method + \n + \n + \n + sha256(body) + \n + path
    content_sha256 = hashlib.sha256(body.encode()).hexdigest()
    string_to_sign = f"GET\n\n\n{content_sha256}\n{path}"
    sign_str = client_id + t + string_to_sign
    signature = hmac.new(secret.encode(), sign_str.encode(), hashlib.sha256).hexdigest().upper()
    return signature, content_sha256


def list_devices(client_id: str, client_secret: str, base_url: str) -> List[Dict[str, Any]]:
    """Minimal Tuya OpenAPI call (device list) with simple signing (GET).

    Note: Real integration should use Tuya SDK; this is a best-effort.
    """
    path = "/v1.0/devices"
    t = str(int(time.time() * 1000))
    signature, content_sha256 = _sign(client_id, client_secret, t, body="", path=path)
    headers = {
        "client_id": client_id,
        "sign": signature,
        "t": t,
        "sign_method": "HMAC-SHA256",
    }
    try:
        r = requests.get(base_url.rstrip("/") + path, headers=headers, timeout=10)
        if r.ok:
            data = r.json()
            result = data.get("result")
            return result if isinstance(result, list) else []
    except Exception:
        return []
    return []

