from __future__ import annotations

import asyncio
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from libs.capabilities.register_providers import register_all as register_capability_adapters
from libs.capabilities.registry import registry as capability_registry
from libs.capabilities.schemas import DeviceAddress, CapabilityType


class DimmerBody(BaseModel):
    level: int


class ColorHSV(BaseModel):
    h: float
    s: float
    v: float


class ColorTemp(BaseModel):
    mireds: int


def create_app() -> FastAPI:
    app = FastAPI(title="Integrations Service")

    @app.on_event("startup")
    async def on_start() -> None:
        try:
            register_capability_adapters()
        except Exception:
            pass

    @app.get("/health")
    async def health() -> Dict[str, Any]:
        providers = {
            p: [cap.value for cap in caps.keys()]
            for p, caps in capability_registry._registry.items()  # type: ignore[attr-defined]
        }
        return {"ok": True, "providers": providers}

    @app.post("/capability/{provider}/{external_id}/switch/on")
    async def capability_switch_on(provider: str, external_id: str) -> Dict[str, Any]:
        adapter = capability_registry.get(provider, CapabilityType.SWITCHABLE)
        if not adapter:
            raise HTTPException(status_code=404, detail="capability adapter not found")
        return await asyncio.to_thread(adapter.turn_on, DeviceAddress(provider=provider, external_id=external_id))

    @app.post("/capability/{provider}/{external_id}/switch/off")
    async def capability_switch_off(provider: str, external_id: str) -> Dict[str, Any]:
        adapter = capability_registry.get(provider, CapabilityType.SWITCHABLE)
        if not adapter:
            raise HTTPException(status_code=404, detail="capability adapter not found")
        return await asyncio.to_thread(adapter.turn_off, DeviceAddress(provider=provider, external_id=external_id))

    @app.post("/capability/{provider}/{external_id}/dimmer/set")
    async def capability_dimmer_set(provider: str, external_id: str, body: DimmerBody) -> Dict[str, Any]:
        adapter = capability_registry.get(provider, CapabilityType.DIMMABLE)
        if not adapter:
            raise HTTPException(status_code=404, detail="capability adapter not found")
        return await asyncio.to_thread(adapter.set_brightness, DeviceAddress(provider=provider, external_id=external_id), body.level)

    @app.post("/capability/{provider}/{external_id}/color/hsv")
    async def capability_color_hsv(provider: str, external_id: str, body: ColorHSV) -> Dict[str, Any]:
        adapter = capability_registry.get(provider, CapabilityType.COLOR_CONTROL)
        if not adapter:
            raise HTTPException(status_code=404, detail="capability adapter not found")
        return await asyncio.to_thread(adapter.set_color_hsv, DeviceAddress(provider=provider, external_id=external_id), body.h, body.s, body.v)

    @app.post("/capability/{provider}/{external_id}/color/temp")
    async def capability_color_temp(provider: str, external_id: str, body: ColorTemp) -> Dict[str, Any]:
        adapter = capability_registry.get(provider, CapabilityType.COLOR_CONTROL)
        if not adapter:
            raise HTTPException(status_code=404, detail="capability adapter not found")
        return await asyncio.to_thread(adapter.set_color_temp, DeviceAddress(provider=provider, external_id=external_id), body.mireds)

    return app


app = create_app()

