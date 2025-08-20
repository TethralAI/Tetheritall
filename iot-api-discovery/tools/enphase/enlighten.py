from __future__ import annotations

from typing import Any, Dict
import requests


def summary(api_key: str, user_id: str, system_id: str, timeout: int = 15) -> Dict[str, Any]:
    url = f"https://api.enphaseenergy.com/api/v4/systems/{system_id}/summary"
    params = {"key": api_key, "user_id": user_id}
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()

