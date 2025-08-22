from __future__ import annotations

import asyncio
import time
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
        app.state.cb = {}

    def _cb_get(provider: str) -> Dict[str, int]:
        st = app.state.cb.get(provider, {"open_until": 0, "fails": 0})
        app.state.cb[provider] = st
        return st

    def _cb_check(provider: str) -> None:
        now = int(time.time())
        st = _cb_get(provider)
        if st["open_until"] > now:
            raise HTTPException(status_code=503, detail=f"{provider} unavailable")

    def _cb_record(provider: str, success: bool, *, fails: int = 3, cooldown: int = 20) -> None:
        now = int(time.time())
        st = _cb_get(provider)
        if success:
            st["fails"] = 0
            st["open_until"] = 0
        else:
            st["fails"] = st.get("fails", 0) + 1
            if st["fails"] >= fails:
                st["open_until"] = now + cooldown
        app.state.cb[provider] = st

    async def _retry(provider: str, func, *args, retries: int = 2, backoff: float = 0.3):
        _cb_check(provider)
        for attempt in range(retries + 1):
            try:
                res = await asyncio.to_thread(func, *args)
                ok = isinstance(res, dict) and (res.get("ok") or True)
                _cb_record(provider, True)
                return res
            except Exception:
                if attempt >= retries:
                    _cb_record(provider, False)
                    raise HTTPException(status_code=502, detail=f"{provider} error")
                await asyncio.sleep(backoff * (2 ** attempt))
        raise HTTPException(status_code=502, detail=f"{provider} error")

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
        return await _retry(provider, adapter.turn_on, DeviceAddress(provider=provider, external_id=external_id))

    @app.post("/capability/{provider}/{external_id}/switch/off")
    async def capability_switch_off(provider: str, external_id: str) -> Dict[str, Any]:
        adapter = capability_registry.get(provider, CapabilityType.SWITCHABLE)
        if not adapter:
            raise HTTPException(status_code=404, detail="capability adapter not found")
        return await _retry(provider, adapter.turn_off, DeviceAddress(provider=provider, external_id=external_id))

    @app.post("/capability/{provider}/{external_id}/dimmer/set")
    async def capability_dimmer_set(provider: str, external_id: str, body: DimmerBody) -> Dict[str, Any]:
        adapter = capability_registry.get(provider, CapabilityType.DIMMABLE)
        if not adapter:
            raise HTTPException(status_code=404, detail="capability adapter not found")
        return await _retry(provider, adapter.set_brightness, DeviceAddress(provider=provider, external_id=external_id), body.level)

    @app.post("/capability/{provider}/{external_id}/color/hsv")
    async def capability_color_hsv(provider: str, external_id: str, body: ColorHSV) -> Dict[str, Any]:
        adapter = capability_registry.get(provider, CapabilityType.COLOR_CONTROL)
        if not adapter:
            raise HTTPException(status_code=404, detail="capability adapter not found")
        return await _retry(provider, adapter.set_color_hsv, DeviceAddress(provider=provider, external_id=external_id), body.h, body.s, body.v)

    @app.post("/capability/{provider}/{external_id}/color/temp")
    async def capability_color_temp(provider: str, external_id: str, body: ColorTemp) -> Dict[str, Any]:
        adapter = capability_registry.get(provider, CapabilityType.COLOR_CONTROL)
        if not adapter:
            raise HTTPException(status_code=404, detail="capability adapter not found")
        return await _retry(provider, adapter.set_color_temp, DeviceAddress(provider=provider, external_id=external_id), body.mireds)

    return app


app = create_app()

