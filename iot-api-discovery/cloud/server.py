from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from database.api_database import create_all, get_session_factory
from database.models import Device, ApiEndpoint, AuthenticationMethod, ScanResult


class DiscoveryIngest(BaseModel):
    manufacturer: str
    model: Optional[str]
    sources: Dict[str, List[Dict[str, Any]]]
    endpoints: List[Dict[str, Any]]
    authentication_methods: List[Dict[str, Any]]
    examples: List[Dict[str, Any]]


def create_app(database_url: str = "sqlite:///./iot_discovery_cloud.db") -> FastAPI:
    create_all(database_url)
    SessionFactory = get_session_factory(database_url)

    app = FastAPI(title="IoT API Discovery Cloud Ingest")

    @app.post("/ingest")
    def ingest(payload: DiscoveryIngest) -> Dict[str, Any]:
        with SessionFactory() as session:
            device = Device(
                model=payload.model or "",
                manufacturer=payload.manufacturer,
            )
            session.add(device)
            session.flush()
            for ep in payload.endpoints:
                session.add(
                    ApiEndpoint(
                        device_id=device.id,
                        url=str(ep.get("path", "")),
                        method=str(ep.get("method")) if ep.get("method") else "GET",
                        auth_required=False,
                        success_rate=float(ep.get("confidence") or 0.0),
                    )
                )
            for am in payload.authentication_methods:
                session.add(
                    AuthenticationMethod(
                        device_id=device.id,
                        auth_type=str(am.get("type") or "unknown"),
                        credentials=None,
                        success_rate=float(am.get("confidence") or 0.0),
                    )
                )
            session.add(
                ScanResult(
                    device_id=device.id,
                    agent_type="documentation",
                    raw_data=payload.model_dump_json(),
                )
            )
            session.commit()
            return {"device_id": device.id}

    return app

app = create_app()

