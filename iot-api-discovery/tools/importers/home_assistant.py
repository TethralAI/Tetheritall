from __future__ import annotations

from typing import Any, Dict, List, Optional
import requests

GITHUB_API = "https://api.github.com"
REPO = "home-assistant/core"
COMPONENTS_PATH = "homeassistant/components"


def list_components(github_token: Optional[str] = None, timeout: int = 20) -> List[Dict[str, Any]]:
    headers = {"Accept": "application/vnd.github+json"}
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"
    url = f"{GITHUB_API}/repos/{REPO}/contents/{COMPONENTS_PATH}"
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    items = r.json() if r.ok else []
    comps: List[Dict[str, Any]] = []
    for it in items or []:
        # only directories
        if it.get("type") == "dir":
            comps.append({"name": it.get("name"), "path": it.get("path")})
    return comps


def fetch_manifest(component: str, github_token: Optional[str] = None, timeout: int = 20) -> Optional[Dict[str, Any]]:
    headers = {"Accept": "application/vnd.github.raw+json"}
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"
    url = f"{GITHUB_API}/repos/{REPO}/contents/{COMPONENTS_PATH}/{component}/manifest.json"
    r = requests.get(url, headers=headers, timeout=timeout)
    if r.status_code == 200:
        try:
            return r.json()
        except Exception:
            return None
    return None


def aggregate_manifests(github_token: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
    comps = list_components(github_token)
    out: List[Dict[str, Any]] = []
    for i, c in enumerate(comps):
        if i >= limit:
            break
        m = fetch_manifest(c["name"], github_token)
        if m:
            out.append({
                "component": c["name"],
                "domain": m.get("domain"),
                "name": m.get("name"),
                "iot_class": m.get("iot_class"),
                "requirements": m.get("requirements", []),
                "config_flow": m.get("config_flow"),
                "dependencies": m.get("dependencies", []),
            })
    return out

