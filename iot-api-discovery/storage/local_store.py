from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

from database.api_database import create_all, get_session_factory, create_device, add_api_endpoint
from database.models import AuthenticationMethod as AuthModel, ScanResult as ScanModel


def _default_dir() -> str:
    base = os.path.expanduser("~/.iot_api_discovery")
    os.makedirs(base, exist_ok=True)
    return base


def save_json(discovery: Dict[str, Any], directory: Optional[str] = None) -> str:
    target_dir = directory or _default_dir()
    os.makedirs(target_dir, exist_ok=True)
    manufacturer = (discovery.get("manufacturer") or "unknown").lower().replace(" ", "-")
    model = (discovery.get("model") or "").lower().replace(" ", "-")
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename = f"{manufacturer}_{model}_{ts}.json" if model else f"{manufacturer}_{ts}.json"
    path = os.path.join(target_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(discovery, f, ensure_ascii=False, indent=2)
    return path


def save_sqlite(discovery: Dict[str, Any], database_url: str = "sqlite:///./iot_discovery_local.db") -> int:
    """Persist discovery result into a local SQLite DB using SQLAlchemy models.

    Returns the device id persisted.
    """
    create_all(database_url)
    SessionFactory = get_session_factory(database_url)
    with SessionFactory() as session:
        device = create_device(
            session,
            model=discovery.get("model") or "",
            manufacturer=discovery.get("manufacturer") or "",
            firmware_version=None,
        )
        # Endpoints
        for ep in discovery.get("endpoints", []) or []:
            add_api_endpoint(
                session,
                device_id=device.id,
                url=str(ep.get("path", "")),
                method=str(ep.get("method")) if ep.get("method") else "GET",
                auth_required=False,
                success_rate=float(ep.get("confidence") or 0.0),
            )
        # Auth methods
        for am in discovery.get("authentication_methods", []) or []:
            session.add(
                AuthModel(
                    device_id=device.id,
                    auth_type=str(am.get("type") or "unknown"),
                    credentials=None,
                    success_rate=float(am.get("confidence") or 0.0),
                )
            )
        # Raw scan result
        session.add(
            ScanModel(
                device_id=device.id,
                agent_type="documentation",
                raw_data=json.dumps(discovery),
            )
        )
        session.commit()
        return device.id

