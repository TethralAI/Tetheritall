from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException, Depends, Request
from fastapi.security import APIKeyHeader
import time
import yaml
from pydantic import BaseModel

from agents.coordinator import CoordinatorAgent, CoordinatorConfig
from config.policy import ConsentPolicy
from app.models.capabilities import normalize_capabilities
from automation.engine import AutomationEngine, Rule
from config.settings import settings
from tools.smartthings.cloud import list_devices as st_list, device_commands as st_cmd
from tools.tuya.cloud import list_devices as tuya_list
from tools.notify.fcm import send_fcm_legacy
from tools.cloud.aws import upload_s3
from tools.iac.hcp_terraform import trigger_run as tf_trigger
from tools.home_assistant.local import list_entities as ha_list, call_service as ha_call
from tools.google.nest_sdm import list_devices as nest_list
from tools.hue.remote import list_resources as hue_list
from tools.openhab.local import list_items as oh_list, send_command as oh_cmd
from tools.zwave.zwave_js_ws import ping_version as zwjs_version
from api.alexa_webhook import router as alexa_router


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

    api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

    async def rate_limiter(request: Request):
        # simple in-memory rate limiter per client IP
        key = f"rl:{request.client.host}"
        now = int(time.time())
        window = now // 60
        store = getattr(app.state, "rate_store", {})
        app.state.rate_store = store
        count = store.get((key, window), 0)
        limit = settings.rate_limit_requests_per_minute
        if count >= limit:
            raise HTTPException(status_code=429, detail="rate limit exceeded")
        store[(key, window)] = count + 1

    async def require_api_key(api_key: str | None = Depends(api_key_header)):
        if settings.api_token and api_key != settings.api_token:
            raise HTTPException(status_code=401, detail="invalid api key")

    @app.on_event("startup")
    async def on_start() -> None:
        await coordinator.start()
        await engine.start()

    @app.on_event("shutdown")
    async def on_stop() -> None:
        await coordinator.stop()
        await engine.stop()

    app.include_router(alexa_router)

    @app.post("/scan/device", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def start_scan(req: ScanRequest) -> Dict[str, Any]:
        task_id = await coordinator.add_task(
            manufacturer=req.manufacturer,
            model=req.model,
            ip_ranges=req.ip_ranges or [],
            priority=req.priority,
            consent=req.consent or ConsentPolicy(),
        )
        return {"task_id": task_id}

    @app.get("/tasks/{task_id}", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def task_status(task_id: str) -> Dict[str, Any]:
        return coordinator.get_task_status(task_id)

    @app.post("/tasks/{task_id}/cancel", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def cancel_task(task_id: str) -> Dict[str, Any]:
        # Soft cancel: mark as cancelled; workers check status (future work)
        # For now, just update state for visibility
        await asyncio.to_thread(coordinator._update_task_state, task_id, "cancelled")
        return {"ok": True}

    @app.post("/tasks/{task_id}/pause", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def pause_task(task_id: str) -> Dict[str, Any]:
        await asyncio.to_thread(coordinator._update_task_state, task_id, "paused")
        return {"ok": True}

    @app.post("/tasks/{task_id}/resume", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
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

    @app.post("/capabilities", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
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
    @app.get("/integrations/smartthings/devices", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def smartthings_devices() -> Dict[str, Any]:
        token = settings.smartthings_token or ""
        items = await asyncio.to_thread(st_list, token) if token else []
        return {"count": len(items), "devices": items}

    class STCommandIn(BaseModel):
        device_id: str
        commands: List[Dict[str, Any]]

    @app.post("/integrations/smartthings/commands", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def smartthings_commands(body: STCommandIn) -> Dict[str, Any]:
        token = settings.smartthings_token or ""
        res = await asyncio.to_thread(st_cmd, token, body.device_id, body.commands) if token else {"ok": False, "error": "missing token"}
        return res

    # Tuya Cloud (minimal)
    @app.get("/integrations/tuya/devices", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def tuya_devices() -> Dict[str, Any]:
        if not (settings.tuya_client_id and settings.tuya_client_secret and settings.tuya_base_url):
            return {"count": 0, "devices": []}
        items = await asyncio.to_thread(tuya_list, settings.tuya_client_id, settings.tuya_client_secret, settings.tuya_base_url)
        return {"count": len(items), "devices": items}

    class FCMIn(BaseModel):
        token: str
        title: str
        body: str
        data: Dict[str, Any] | None = None

    @app.post("/integrations/fcm/send", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def fcm_send(body: FCMIn) -> Dict[str, Any]:
        if not settings.fcm_server_key:
            return {"ok": False, "error": "missing server key"}
        return await asyncio.to_thread(send_fcm_legacy, settings.fcm_server_key, body.token, body.title, body.body, body.data)

    class S3In(BaseModel):
        key: str
        content: str

    @app.post("/integrations/aws/s3/upload", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def s3_upload(body: S3In) -> Dict[str, Any]:
        if not settings.aws_s3_bucket:
            return {"ok": False, "error": "missing bucket"}
        return await asyncio.to_thread(upload_s3, settings.aws_s3_bucket, body.key, body.content.encode("utf-8"), settings.aws_region)

    @app.post("/integrations/hcp/terraform/run", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def hcp_tf_run() -> Dict[str, Any]:
        if not (settings.hcp_terraform_token and settings.hcp_terraform_workspace_id):
            return {"ok": False, "error": "missing terraform config"}
        return await asyncio.to_thread(tf_trigger, settings.hcp_terraform_token, settings.hcp_terraform_workspace_id)

    # Firmware upload and export endpoints
    @app.post("/firmware/upload", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def firmware_upload(file: UploadFile = File(...)) -> Dict[str, Any]:
        content = await file.read()
        # Placeholder: save to S3 if configured
        if settings.aws_s3_bucket:
            key = f"firmware/{file.filename}"
            res = await asyncio.to_thread(upload_s3, settings.aws_s3_bucket, key, content, settings.aws_region)
            return res
        return {"ok": True, "received": len(content)}

    @app.post("/export", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def export_json(payload: Dict[str, Any]) -> Dict[str, Any]:
        fmt = payload.get("format", "json")
        data = payload.get("data", {})
        if fmt == "yaml":
            return {"format": "yaml", "content": yaml.safe_dump(data)}
        return {"format": "json", "content": data}

    # Home Assistant local
    @app.get("/integrations/home_assistant/entities", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def home_assistant_entities() -> Dict[str, Any]:
        if not (settings.home_assistant_base_url and settings.home_assistant_token):
            return {"count": 0, "entities": []}
        items = await asyncio.to_thread(ha_list, settings.home_assistant_base_url, settings.home_assistant_token)
        return {"count": len(items), "entities": items}

    class HACallIn(BaseModel):
        domain: str
        service: str
        payload: Dict[str, Any]

    @app.post("/integrations/home_assistant/call", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def home_assistant_call(body: HACallIn) -> Dict[str, Any]:
        if not (settings.home_assistant_base_url and settings.home_assistant_token):
            return {"ok": False, "error": "missing HA config"}
        return await asyncio.to_thread(ha_call, settings.home_assistant_base_url, settings.home_assistant_token, body.domain, body.service, body.payload)

    # Google Nest SDM (placeholder; requires full setup)
    @app.get("/integrations/google/nest/devices", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def google_nest_devices() -> Dict[str, Any]:
        token = settings.google_nest_access_token or ""
        items = await asyncio.to_thread(nest_list, token) if token else []
        return {"count": len(items), "devices": items}

    # Hue Remote API (placeholder)
    @app.get("/integrations/hue/remote/resources", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def hue_remote_resources() -> Dict[str, Any]:
        token = settings.hue_remote_token or ""
        items = await asyncio.to_thread(hue_list, token) if token else []
        return {"count": len(items), "resources": items}

    # openHAB local
    @app.get("/integrations/openhab/items", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def openhab_items() -> Dict[str, Any]:
        if not settings.openhab_base_url:
            return {"count": 0, "items": []}
        items = await asyncio.to_thread(oh_list, settings.openhab_base_url, settings.openhab_token)
        return {"count": len(items), "items": items}

    class OHCommandIn(BaseModel):
        item: str
        command: str

    @app.post("/integrations/openhab/command", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def openhab_command(body: OHCommandIn) -> Dict[str, Any]:
        if not settings.openhab_base_url:
            return {"ok": False, "error": "missing openhab base url"}
        return await asyncio.to_thread(oh_cmd, settings.openhab_base_url, body.item, body.command, settings.openhab_token)

    # Z-Wave JS WS
    @app.get("/integrations/zwave_js/version", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def zwave_js_version() -> Dict[str, Any]:
        if not settings.zwave_js_url:
            return {"ok": False, "error": "missing zwave_js_url"}
        return await zwjs_version(settings.zwave_js_url)


    return app


app = create_app()

