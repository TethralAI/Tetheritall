from __future__ import annotations

from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Request
import ipaddress
import asyncio
import json
import os
import time

from config.settings import settings
from tools.home_assistant.local import list_entities as ha_list
from tools.zigbee.zigbee2mqtt_driver import Zigbee2MQTTDriver
from tools.hue.hue_local import toggle_light as hue_toggle  # type: ignore[attr-defined]
from tools.kasa.local import set_state as kasa_set  # type: ignore[attr-defined]

try:
    import httpx
except Exception:
    httpx = None  # type: ignore


def _parse_subnets(val: str | None) -> List[ipaddress._BaseNetwork]:  # type: ignore[name-defined]
    nets: List[ipaddress._BaseNetwork] = []  # type: ignore[name-defined]
    for part in (val or "").split(","):
        p = part.strip()
        if not p:
            continue
        try:
            nets.append(ipaddress.ip_network(p))
        except Exception:
            continue
    return nets


class OfflineQueue:
    def __init__(self) -> None:
        self._q: List[Dict[str, Any]] = []
        self._backoff = 1.0

    def enqueue(self, item: Dict[str, Any]) -> None:
        self._q.append(item)

    async def drain(self, send_func) -> None:
        if not self._q:
            self._backoff = 1.0
            return
        remaining: List[Dict[str, Any]] = []
        for item in self._q:
            try:
                ok = await send_func(item)
                if not ok:
                    remaining.append(item)
            except Exception:
                remaining.append(item)
        self._q = remaining
        if self._q:
            await asyncio.sleep(self._backoff)
            self._backoff = min(self._backoff * 2.0, 30.0)
        else:
            self._backoff = 1.0


def create_app() -> FastAPI:
    app = FastAPI(title="Edge Agent (LAN-only)")

    if not settings.edge_lan_only:
        raise RuntimeError("edge agent requires edge_lan_only=true")

    ALLOW_SUBNETS = _parse_subnets(os.getenv("EDGE_ALLOW_SUBNETS"))
    app.state.offline_q = OfflineQueue()

    @app.middleware("http")
    async def _subnet_allowlist(request: Request, call_next):
        # Only allow requests from allowed subnets if configured
        if ALLOW_SUBNETS:
            try:
                client_ip = ipaddress.ip_address(request.client.host if request.client else "127.0.0.1")
                if not any(client_ip in n for n in ALLOW_SUBNETS):
                    return HTTPException(status_code=403, detail="forbidden")
            except Exception:
                return HTTPException(status_code=403, detail="forbidden")
        return await call_next(request)

    @app.get("/health")
    async def health() -> Dict[str, Any]:
        return {"ok": True, "lan_only": True}

    @app.get("/ha/entities")
    async def ha_entities() -> Dict[str, Any]:
        if not (settings.home_assistant_base_url and settings.home_assistant_token):
            return {"count": 0, "entities": []}
        items = await ha_list(settings.home_assistant_base_url, settings.home_assistant_token)
        return {"count": len(items), "entities": items}

    async def _send_to_gateway(item: Dict[str, Any]) -> bool:
        if httpx is None:
            return False
        base = os.getenv("GATEWAY_BASE_URL")
        api_key = os.getenv("EDGE_API_KEY", "")
        if not base:
            return False
        mtls_ca = os.getenv("MTLS_CA_PATH")
        mtls_cert = os.getenv("MTLS_CLIENT_CERT_PATH")
        mtls_key = os.getenv("MTLS_CLIENT_KEY_PATH")
        args: Dict[str, Any] = {}
        if mtls_ca:
            args["verify"] = mtls_ca
        if mtls_cert and mtls_key:
            args["cert"] = (mtls_cert, mtls_key)
        try:
            async with httpx.AsyncClient(timeout=10, **args) as client:
                r = await client.post(f"{base.rstrip('/')}/proxy/integrations/edge/event", json=item, headers={"x-api-key": api_key})
                return r.status_code < 500
        except Exception:
            return False

    @app.post("/edge/event")
    async def edge_event(item: Dict[str, Any]) -> Dict[str, Any]:
        # Minimal telemetry gating
        if not settings.telemetry_opt_in:
            return {"ok": True}
        ok = await _send_to_gateway(item)
        if not ok:
            app.state.offline_q.enqueue(item)
        # background drain
        asyncio.create_task(app.state.offline_q.drain(_send_to_gateway))
        return {"ok": True, "queued": not ok}

    @app.post("/z2m/{external_id}/switch/{state}")
    async def z2m_switch(external_id: str, state: str) -> Dict[str, Any]:
        drv = Zigbee2MQTTDriver(
            broker=settings.z2m_broker or "localhost",
            port=settings.z2m_port,
            username=settings.z2m_username,
            password=settings.z2m_password,
        )
        desired = "ON" if state.lower() in ("on", "1", "true") else "OFF"
        return drv.publish(f"zigbee2mqtt/{external_id}/set", "{\"state\": \"%s\"}" % desired)

    return app


app = create_app()

