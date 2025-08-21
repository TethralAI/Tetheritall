from __future__ import annotations

from typing import Any, Dict, List
import requests


class OCPIClient:
    def __init__(self, base_url: str, token: str, timeout: int = 20) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Token {self.token}", "Accept": "application/json"}

    def locations(self) -> List[Dict[str, Any]]:
        r = requests.get(f"{self.base_url}/locations", headers=self._headers(), timeout=self.timeout)
        return r.json() if r.ok else []

    def tariffs(self) -> List[Dict[str, Any]]:
        r = requests.get(f"{self.base_url}/tariffs", headers=self._headers(), timeout=self.timeout)
        return r.json() if r.ok else []

    def sessions(self) -> List[Dict[str, Any]]:
        r = requests.get(f"{self.base_url}/sessions", headers=self._headers(), timeout=self.timeout)
        return r.json() if r.ok else []

