from __future__ import annotations

from typing import Any, Dict, List, Optional
import requests
import time


class OCPIClient:
    def __init__(self, base_url: str, token: str, timeout: int = 20) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Token {self.token}", "Accept": "application/json"}

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None, retries: int = 2, backoff: float = 0.5) -> Any:
        url = f"{self.base_url}{path}"
        for attempt in range(retries + 1):
            try:
                r = requests.get(url, headers=self._headers(), timeout=self.timeout, params=params or {})
                if r.ok:
                    return r.json()
            except Exception:
                pass
            time.sleep(backoff * (2 ** attempt))
        return []

    def locations(self, *, offset: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        data = self._get("/locations", params={"offset": offset, "limit": limit})
        return data if isinstance(data, list) else []

    def tariffs(self, *, offset: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        data = self._get("/tariffs", params={"offset": offset, "limit": limit})
        return data if isinstance(data, list) else []

    def sessions(self, *, date_from: Optional[str] = None, date_to: Optional[str] = None, offset: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"offset": offset, "limit": limit}
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        data = self._get("/sessions", params=params)
        return data if isinstance(data, list) else []

