from __future__ import annotations

from typing import Any, Dict
import requests


def site_overview(api_key: str, site_id: str, timeout: int = 15) -> Dict[str, Any]:
    url = f"https://monitoringapi.solaredge.com/site/{site_id}/overview.json"
    params = {"api_key": api_key}
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()

