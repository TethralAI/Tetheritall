from __future__ import annotations

from typing import Dict, List


def build_common_iot_paths() -> List[str]:
    return [
        "/api",
        "/rest",
        "/v1",
        "/v2",
        "/swagger.json",
        "/openapi.json",
    ]


def summarize_scan(services: List[Dict]) -> Dict:
    return {"count": len(services)}

