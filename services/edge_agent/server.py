from __future__ import annotations

from typing import Any, Dict

from fastapi import FastAPI, HTTPException

from config.settings import settings
from tools.home_assistant.local import list_entities as ha_list
from tools.zigbee.zigbee2mqtt_driver import Zigbee2MQTTDriver
from tools.hue.hue_local import toggle_light as hue_toggle  # type: ignore[attr-defined]
from tools.kasa.local import set_state as kasa_set  # type: ignore[attr-defined]


def create_app() -> FastAPI:
    app = FastAPI(title="Edge Agent (LAN-only)")

    if not settings.edge_lan_only:
        raise RuntimeError("edge agent requires edge_lan_only=true")

    @app.get("/health")
    async def health() -> Dict[str, Any]:
        return {"ok": True, "lan_only": True}

    @app.get("/ha/entities")
    async def ha_entities() -> Dict[str, Any]:
        if not (settings.home_assistant_base_url and settings.home_assistant_token):
            return {"count": 0, "entities": []}
        items = await ha_list(settings.home_assistant_base_url, settings.home_assistant_token)
        return {"count": len(items), "entities": items}

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

