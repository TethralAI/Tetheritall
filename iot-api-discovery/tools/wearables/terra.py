from __future__ import annotations

from typing import Any, Dict
import requests


def daily_summary(api_key: str, user_id: str) -> Dict[str, Any]:
    headers = {"x-api-key": api_key}
    url = f"https://api.tryterra.co/v2/daily?user_id={user_id}"
    r = requests.get(url, headers=headers, timeout=15)
    return r.json() if r.ok else {"error": r.text}

