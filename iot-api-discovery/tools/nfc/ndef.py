from __future__ import annotations

from typing import Any, Dict, List


def parse_dpp_uri(uri: str) -> Dict[str, Any]:
    """Parse Wi‑Fi DPP (Easy Connect) URI if present in an NFC/QR payload."""
    # Very simple parser for URIs like: DPP:K:WPA-Personal;S:SSID;P:password;C:81/1;;
    if not uri or not uri.upper().startswith("DPP:"):
        return {}
    body = uri[4:]
    parts = [p for p in body.split(";") if p]
    out: Dict[str, Any] = {}
    for p in parts:
        if ":" in p:
            k, v = p.split(":", 1)
            out[k] = v
    return out

