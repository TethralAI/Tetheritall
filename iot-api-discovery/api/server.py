from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from agents.coordinator import CoordinatorAgent, CoordinatorConfig
from config.policy import ConsentPolicy


class ScanRequest(BaseModel):
    manufacturer: str
    model: Optional[str] = None
    ip_ranges: Optional[List[str]] = None
    priority: int = 10
    consent: Optional[ConsentPolicy] = None


def create_app() -> FastAPI:
    app = FastAPI(title="IoT Discovery Coordinator API")
    coordinator = CoordinatorAgent(CoordinatorConfig())

    @app.on_event("startup")
    async def on_start() -> None:
        await coordinator.start()

    @app.on_event("shutdown")
    async def on_stop() -> None:
        await coordinator.stop()

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

    return app


app = create_app()

