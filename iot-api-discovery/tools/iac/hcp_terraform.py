from __future__ import annotations

from typing import Any, Dict
import requests


def trigger_run(token: str, workspace_id: str, message: str = "IoT orchestrator run") -> Dict[str, Any]:
    url = f"https://app.terraform.io/api/v2/runs"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/vnd.api+json"}
    payload = {
        "data": {
            "attributes": {"message": message, "is-destroy": False},
            "type": "runs",
            "relationships": {"workspace": {"data": {"type": "workspaces", "id": workspace_id}}},
        }
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=20)
        return {"ok": r.ok, "status": r.status_code, "json": r.json() if r.ok else r.text}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

