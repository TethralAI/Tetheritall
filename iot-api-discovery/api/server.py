from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from agents.coordinator import CoordinatorAgent, CoordinatorConfig
from config.policy import ConsentPolicy
from app.models.capabilities import normalize_capabilities
from automation.engine import AutomationEngine, Rule
from config.settings import settings
from tools.smartthings.cloud import list_devices as st_list, device_commands as st_cmd
from tools.tuya.cloud import list_devices as tuya_list


class ScanRequest(BaseModel):
    manufacturer: str
    model: Optional[str] = None
    ip_ranges: Optional[List[str]] = None
    priority: int = 10
    consent: Optional[ConsentPolicy] = None


def create_app() -> FastAPI:
    app = FastAPI(title="IoT Discovery Coordinator API")
    coordinator = CoordinatorAgent(CoordinatorConfig())
    engine = AutomationEngine()

    @app.on_event("startup")
    async def on_start() -> None:
        await coordinator.start()
        await engine.start()

    @app.on_event("shutdown")
    async def on_stop() -> None:
        await coordinator.stop()
        await engine.stop()

    @app.post("/scan/device")
    async def start_scan(req: ScanRequest) -> Dict[str, Any]:
        task_id = await coordinator.add_task(
            manufacturer=req.manufacturer,
            model=req.model,
            ip_ranges=req.ip_ranges or [],
            priority=req.priority,
            consent=req.consent or ConsentPolicy(),
        )
        return {"task_id": task_id}

    @app.get("/tasks/{task_id}")
    async def task_status(task_id: str) -> Dict[str, Any]:
        return coordinator.get_task_status(task_id)

    @app.post("/tasks/{task_id}/cancel")
    async def cancel_task(task_id: str) -> Dict[str, Any]:
        # Soft cancel: mark as cancelled; workers check status (future work)
        # For now, just update state for visibility
        await asyncio.to_thread(coordinator._update_task_state, task_id, "cancelled")
        return {"ok": True}

    @app.post("/tasks/{task_id}/pause")
    async def pause_task(task_id: str) -> Dict[str, Any]:
        await asyncio.to_thread(coordinator._update_task_state, task_id, "paused")
        return {"ok": True}

    @app.post("/tasks/{task_id}/resume")
    async def resume_task(task_id: str) -> Dict[str, Any]:
        await asyncio.to_thread(coordinator._update_task_state, task_id, "queued")
        return {"ok": True}

    @app.websocket("/updates")
    async def updates(ws: WebSocket) -> None:
        await ws.accept()
        q = coordinator.subscribe_status()
        try:
            while True:
                msg = await q.get()
                await ws.send_json(msg)
        except WebSocketDisconnect:
            pass
        finally:
            coordinator.unsubscribe_status(q)

    @app.post("/capabilities")
    async def capabilities(result: Dict[str, Any]) -> Dict[str, Any]:
        caps = normalize_capabilities(result)
        return {"count": len(caps), "capabilities": [c.__dict__ for c in caps]}

    class RuleIn(BaseModel):
        id: str
        trigger: Dict[str, Any]
        conditions: List[Dict[str, Any]] = []
        actions: List[Dict[str, Any]] = []

    @app.post("/automation/rules")
    async def add_rule(rule: RuleIn) -> Dict[str, Any]:
        engine.add_rule(Rule(id=rule.id, trigger=rule.trigger, conditions=rule.conditions, actions=rule.actions))
        return {"ok": True}

    # SmartThings Cloud
    @app.get("/integrations/smartthings/devices")
    async def smartthings_devices() -> Dict[str, Any]:
        token = settings.smartthings_token or ""
        items = await asyncio.to_thread(st_list, token) if token else []
        return {"count": len(items), "devices": items}

    class STCommandIn(BaseModel):
        device_id: str
        commands: List[Dict[str, Any]]

    @app.post("/integrations/smartthings/commands")
    async def smartthings_commands(body: STCommandIn) -> Dict[str, Any]:
        token = settings.smartthings_token or ""
        res = await asyncio.to_thread(st_cmd, token, body.device_id, body.commands) if token else {"ok": False, "error": "missing token"}
        return res

    # Tuya Cloud (minimal)
    @app.get("/integrations/tuya/devices")
    async def tuya_devices() -> Dict[str, Any]:
        if not (settings.tuya_client_id and settings.tuya_client_secret and settings.tuya_base_url):
            return {"count": 0, "devices": []}
        items = await asyncio.to_thread(tuya_list, settings.tuya_client_id, settings.tuya_client_secret, settings.tuya_base_url)
        return {"count": len(items), "devices": items}


    return app


app = create_app()

