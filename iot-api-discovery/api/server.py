from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException, Depends, Request
from fastapi.security import APIKeyHeader
import time
import yaml
from pydantic import BaseModel
from starlette_exporter import PrometheusMiddleware, handle_metrics
from fastapi.middleware.cors import CORSMiddleware

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
from tools.zwave.zwave_js_ws import ping_version as zwjs_version, get_nodes as zwjs_nodes, set_value as zwjs_set_value
from api.alexa_webhook import router as alexa_router
from api.hue_commissioning import router as hue_commissioning_router
from api.device_discovery_api import router as device_discovery_router
from tools.smartthings.oauth import build_auth_url as st_auth_url, exchange_code_for_token as st_exchange
from tools.tuya.oauth import build_auth_url as tuya_auth_url
from libs.capabilities.register_providers import register_all as register_capability_adapters
from libs.capabilities.registry import registry as capability_registry
from libs.capabilities.schemas import DeviceAddress, CapabilityType
from adapters import usgs as usgs_adapter, nws as nws_adapter
from tools.importers import home_assistant as ha_importer
from tools.hubs import hubitat as hubitat_tools
from tools.wearables import oura as oura_tools, terra as terra_tools
import httpx
from api.smartthings_webhook import router as st_events_router
from api.smartthings_subscriptions import router as st_sub_router
from storage.twins import store as twin_store
from tools.llm.guard import LLMGuard
from tools.energy.ocpi_client import OCPIClient
from api.middleware import request_id_and_logging_middleware
from tools.events.bus import bus

# Performance enhancements
from api.performance_middleware import (
    performance_middleware, 
    enhanced_rate_limiter, 
    performance_monitor,
    RateLimitConfig,
    CircuitBreakerConfig
)
from services.cache.enhanced_cache import enhanced_cache, CacheConfig, CacheLayer

# Optional OpenTelemetry setup
try:
    import os
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as OTLPHTTPExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
except Exception:
    trace = None  # type: ignore

try:
    from prometheus_client import Histogram
except Exception:
    Histogram = None  # type: ignore

_request_hist = None
if Histogram is not None:
    _request_hist = Histogram(
        "api_request_duration_seconds",
        "API request duration",
        labelnames=("method", "path", "status"),
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
    )


def _current_trace_id() -> Optional[str]:
    try:
        if trace is None:
            return None
        span = trace.get_current_span()
        ctx = span.get_span_context()
        if not ctx or not ctx.trace_id:
            return None
        return f"{ctx.trace_id:032x}"
    except Exception:
        return None


def _init_tracing(service_name: str) -> None:
    if trace is None:
        return
    try:
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or "http://localhost:4318"
        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)
        exporter = OTLPHTTPExporter(endpoint=f"{endpoint}/v1/traces")
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        # Instrumentations
        FastAPIInstrumentor.instrument()
        HTTPXClientInstrumentor().instrument()
        SQLAlchemyInstrumentor().instrument()
        RedisInstrumentor().instrument()
    except Exception:
        pass


class ScanRequest(BaseModel):
    manufacturer: str
    model: Optional[str] = None
    ip_ranges: Optional[List[str]] = None
    priority: int = 10
    consent: Optional[ConsentPolicy] = None


def create_app() -> FastAPI:
    app = FastAPI(title="IoT Discovery Coordinator API")
    # CORS allowlist
    allow = [o.strip() for o in (settings.outbound_allowlist or "").split(",") if o.strip()]
    if allow:
        app.add_middleware(CORSMiddleware, allow_origins=allow, allow_methods=["*"], allow_headers=["*"])
    # Security headers
    @app.middleware("http")
    async def _security_headers(request: Request, call_next):
        resp = await call_next(request)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "no-referrer"
        return resp
    app.middleware("http")(request_id_and_logging_middleware)
    app.add_middleware(PrometheusMiddleware)
    app.add_route("/metrics", handle_metrics)
    
    # Add performance monitoring middleware
    @app.middleware("http")
    async def performance_monitoring_middleware(request: Request, call_next):
        return await performance_monitor(request, call_next)

    # Request timing middleware with exemplars
    if _request_hist is not None:
        @app.middleware("http")
        async def _metrics_timing(request: Request, call_next):
            start = time.time()
            resp = await call_next(request)
            dur = time.time() - start
            labels = (request.method, request.url.path, str(getattr(resp, "status_code", 200)))
            if _request_hist is not None:
                ex = {}
                tid = _current_trace_id()
                if tid:
                    ex = {"trace_id": tid}
                try:
                    _request_hist.labels(*labels).observe(dur, exemplar=ex or None)  # type: ignore[arg-type]
                except Exception:
                    _request_hist.labels(*labels).observe(dur)
            return resp

    coordinator = CoordinatorAgent(CoordinatorConfig())
    engine = AutomationEngine()
    llm_guard = LLMGuard()

    api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

    async def rate_limiter(request: Request):
        # Enhanced rate limiting with Redis support
        await enhanced_rate_limiter(request)

    async def require_api_key(api_key: str | None = Depends(api_key_header)):
        if settings.api_token and api_key != settings.api_token:
            raise HTTPException(status_code=401, detail="invalid api key")

    @app.on_event("startup")
    async def on_start() -> None:
        # Initialize performance middleware
        await performance_middleware.initialize()
        
        # Initialize enhanced cache
        await enhanced_cache.initialize()
        
        await coordinator.start()
        await engine.start()
        # Register capability adapters (optional/no-op if not available)
        try:
            register_capability_adapters()
        except Exception:
            pass

    @app.on_event("shutdown")
    async def on_stop() -> None:
        await coordinator.stop()
        await engine.stop()
        
        # Stop performance components
        await enhanced_cache.stop()

    app.include_router(alexa_router)
    app.include_router(st_events_router)
    app.include_router(st_sub_router)
    app.include_router(hue_commissioning_router)
    app.include_router(device_discovery_router)

    @app.get("/events/health")
    async def events_health() -> Dict[str, Any]:
        return bus.health()

    # Performance monitoring endpoints
    @app.get("/performance/health")
    async def performance_health() -> Dict[str, Any]:
        """Get performance system health status."""
        return {
            "rate_limiter": {
                "enabled": True,
                "redis_connected": performance_middleware.rate_limiter.redis_client is not None
            },
            "cache": enhanced_cache.get_stats(),
            "circuit_breakers": {
                name: {
                    "state": cb.state,
                    "failure_count": cb.failure_count,
                    "last_failure_time": cb.last_failure_time
                }
                for name, cb in performance_middleware.circuit_breakers.items()
            },
            "connection_pools": {
                name: {
                    "active_connections": pool.active_connections,
                    "max_connections": pool.config.max_connections
                }
                for name, pool in performance_middleware.connection_pools.items()
            }
        }

    @app.get("/performance/metrics")
    async def performance_metrics() -> Dict[str, Any]:
        """Get detailed performance metrics."""
        return {
            "cache_stats": enhanced_cache.get_stats(),
            "rate_limiter_stats": {
                "local_buckets": len(performance_middleware.rate_limiter.local_buckets),
                "redis_connected": performance_middleware.rate_limiter.redis_client is not None
            },
            "circuit_breaker_stats": {
                name: {
                    "state": cb.state,
                    "failure_count": cb.failure_count,
                    "success_count": cb.success_count
                }
                for name, cb in performance_middleware.circuit_breakers.items()
            }
        }

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
        # Use enhanced cache for task status
        cache_key = f"task_status:{task_id}"
        return await enhanced_cache.get_or_set(
            cache_key,
            lambda: coordinator.get_task_status(task_id),
            ttl=30,  # Cache for 30 seconds
            cache_layer=CacheLayer.L1
        )

    @app.post("/tasks/{task_id}/cancel", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def cancel_task(task_id: str) -> Dict[str, Any]:
        # Soft cancel: mark as cancelled; workers check status (future work)
        # For now, just update state for visibility
        await asyncio.to_thread(coordinator._update_task_state, task_id, "cancelled")
        
        # Invalidate cache
        cache_key = f"task_status:{task_id}"
        await enhanced_cache.delete(cache_key, CacheLayer.L1)
        
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

    # New capability endpoints (non-breaking; additive)
    @app.post("/capability/{provider}/{external_id}/switch/on", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def capability_switch_on(provider: str, external_id: str) -> Dict[str, Any]:
        if settings.proxy_capabilities_via_integrations and settings.integrations_base_url:
            async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
                r = await client.post(f"{settings.integrations_base_url}/capability/{provider}/{external_id}/switch/on")
                return r.json() if r.status_code < 500 else {"error": r.text}
        adapter = capability_registry.get(provider, CapabilityType.SWITCHABLE)
        if not adapter:
            raise HTTPException(status_code=404, detail="capability adapter not found")
        return await asyncio.to_thread(adapter.turn_on, DeviceAddress(provider=provider, external_id=external_id))

    @app.post("/capability/{provider}/{external_id}/switch/off", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def capability_switch_off(provider: str, external_id: str) -> Dict[str, Any]:
        if settings.proxy_capabilities_via_integrations and settings.integrations_base_url:
            async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
                r = await client.post(f"{settings.integrations_base_url}/capability/{provider}/{external_id}/switch/off")
                return r.json() if r.status_code < 500 else {"error": r.text}
        adapter = capability_registry.get(provider, CapabilityType.SWITCHABLE)
        if not adapter:
            raise HTTPException(status_code=404, detail="capability adapter not found")
        return await asyncio.to_thread(adapter.turn_off, DeviceAddress(provider=provider, external_id=external_id))

    class DimmerBody(BaseModel):
        level: int

    @app.post("/capability/{provider}/{external_id}/dimmer/set", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def capability_dimmer_set(provider: str, external_id: str, body: DimmerBody) -> Dict[str, Any]:
        if settings.proxy_capabilities_via_integrations and settings.integrations_base_url:
            async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
                r = await client.post(f"{settings.integrations_base_url}/capability/{provider}/{external_id}/dimmer/set", json={"level": body.level})
                return r.json() if r.status_code < 500 else {"error": r.text}
        adapter = capability_registry.get(provider, CapabilityType.DIMMABLE)
        if not adapter:
            raise HTTPException(status_code=404, detail="capability adapter not found")
        return await asyncio.to_thread(adapter.set_brightness, DeviceAddress(provider=provider, external_id=external_id), body.level)

    class ColorHSV(BaseModel):
        h: float
        s: float
        v: float

    class ColorTemp(BaseModel):
        mireds: int

    @app.post("/capability/{provider}/{external_id}/color/hsv", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def capability_color_hsv(provider: str, external_id: str, body: ColorHSV) -> Dict[str, Any]:
        if settings.proxy_capabilities_via_integrations and settings.integrations_base_url:
            async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
                r = await client.post(f"{settings.integrations_base_url}/capability/{provider}/{external_id}/color/hsv", json={"h": body.h, "s": body.s, "v": body.v})
                return r.json() if r.status_code < 500 else {"error": r.text}
        adapter = capability_registry.get(provider, CapabilityType.COLOR_CONTROL)
        if not adapter:
            raise HTTPException(status_code=404, detail="capability adapter not found")
        return await asyncio.to_thread(adapter.set_color_hsv, DeviceAddress(provider=provider, external_id=external_id), body.h, body.s, body.v)

    @app.post("/capability/{provider}/{external_id}/color/temp", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def capability_color_temp(provider: str, external_id: str, body: ColorTemp) -> Dict[str, Any]:
        if settings.proxy_capabilities_via_integrations and settings.integrations_base_url:
            async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
                r = await client.post(f"{settings.integrations_base_url}/capability/{provider}/{external_id}/color/temp", json={"mireds": body.mireds})
                return r.json() if r.status_code < 500 else {"error": r.text}
        adapter = capability_registry.get(provider, CapabilityType.COLOR_CONTROL)
        if not adapter:
            raise HTTPException(status_code=404, detail="capability adapter not found")
        return await asyncio.to_thread(adapter.set_color_temp, DeviceAddress(provider=provider, external_id=external_id), body.mireds)

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

    # Backward-compatible hazards endpoint
    @app.get("/api/hazards", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def get_hazards(lat: float, lon: float) -> Dict[str, Any]:
        quakes, alerts = await asyncio.gather(
            asyncio.to_thread(usgs_adapter.fetch_quakes, lat, lon),
            asyncio.to_thread(nws_adapter.fetch_alerts, lat, lon),
        )
        hazards: List[Dict[str, Any]] = []
        for q in quakes:
            item = dict(q)
            item.setdefault("category", "seismic")
            hazards.append(item)
        for a in alerts:
            item = dict(a)
            item.setdefault("category", "weather")
            hazards.append(item)
        return {"count": len(hazards), "hazards": hazards}

    # Dynamic registry (in-memory, non-persistent)
    app.state.dynamic_registry: Dict[str, Dict[str, Any]] = {}

    @app.post("/discover/ingest", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def discover_ingest(spec: Dict[str, Any]) -> Dict[str, Any]:
        manufacturer = str(spec.get("manufacturer", "")).lower()
        if not manufacturer:
            raise HTTPException(status_code=400, detail="missing manufacturer")
        app.state.dynamic_registry[manufacturer] = spec
        return {"ok": True}

    @app.get("/integrations/dynamic/providers", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def dynamic_providers() -> Dict[str, Any]:
        return {"providers": sorted(list(app.state.dynamic_registry.keys()))}

    @app.post("/integrations/dynamic/{provider}/call", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def dynamic_call(provider: str, body: Dict[str, Any]) -> Dict[str, Any]:
        import requests as _rq

        ep = (body or {}).get("endpoint", {})
        url = ep.get("url") or ep.get("path")
        method = (ep.get("method") or "GET").upper()
        if not url:
            raise HTTPException(status_code=400, detail="missing endpoint url")
        try:
            def _do():
                if method == "GET":
                    resp = _rq.get(url, timeout=settings.request_timeout_seconds)
                else:
                    resp = _rq.request(method=method, url=url, timeout=settings.request_timeout_seconds)
                data: Any
                try:
                    data = resp.json()
                except Exception:
                    data = resp.text
                return {"ok": resp.ok, "status": resp.status_code, "data": data}

            return await asyncio.to_thread(_do)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    # Hubitat Maker API minimal endpoints
    @app.get("/integrations/hubitat/devices", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def hubitat_devices() -> Dict[str, Any]:
        base = settings.hubitat_maker_base_url
        token = settings.hubitat_maker_token or ""
        if not base or not token:
            return {"count": 0, "devices": []}
        items = await asyncio.to_thread(hubitat_tools.list_devices_maker, base, token)
        return {"count": len(items), "devices": items}

    class HubitatCmdBody(BaseModel):
        device_id: str
        command: str
        args: List[Any] | None = None

    @app.post("/integrations/hubitat/command", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def hubitat_command(body: HubitatCmdBody) -> Dict[str, Any]:
        base = settings.hubitat_maker_base_url
        token = settings.hubitat_maker_token or ""
        if not base or not token:
            return {"ok": False, "error": "missing hubitat settings"}
        return await asyncio.to_thread(hubitat_tools.device_command_maker, base, token, body.device_id, body.command, body.args or [])

    # Importers: Home Assistant components
    @app.get("/importers/home_assistant/components", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def ha_import_components() -> Dict[str, Any]:
        try:
            items = await asyncio.to_thread(ha_importer.list_components, settings.github_token)
            return {"count": len(items), "components": items}
        except Exception as exc:
            return {"count": 0, "components": [], "error": str(exc)}

    # LLM routine generator (fallback heuristic if no key)
    @app.post("/automation/routines/generate_llm", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def generate_routine_llm(body: Dict[str, Any], request: Request) -> Dict[str, Any]:
        # Fallback: return a trivial rule heuristic regardless of key presence
        org_id = request.headers.get(settings.org_id_header, "default")
        prompt_raw = str((body or {}).get("prompt") or "")
        prompt = llm_guard.pii_scrub(prompt_raw)
        # Budget check (assume cost proportional to length)
        cost = max(1, len(prompt) // 50)
        if not llm_guard.check_and_consume(org_id, cost):
            raise HTTPException(status_code=402, detail="LLM budget exceeded")
        text = prompt.lower()
        action: Dict[str, Any] = {"type": "switch", "service": "on" if "on" in text else "off"}
        rule = {"id": "generated", "trigger": {"type": "time"}, "conditions": [], "actions": [action]}
        llm_guard.log_audit(org_id, {"ts": int(time.time()), "prompt_len": len(prompt_raw), "cost": cost, "rule": rule})
        return {"rule": rule, "deterministic": settings.llm_deterministic}

    # Importers: Home Assistant manifest
    @app.get("/importers/home_assistant/manifest", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def ha_manifest(component: str) -> Dict[str, Any]:
        try:
            m = await asyncio.to_thread(ha_importer.fetch_manifest, component, settings.github_token)
            return {"manifest": (m or {})}
        except Exception as exc:
            return {"error": str(exc)}

    # Wearables: Oura OAuth URL (400 if missing)
    @app.get("/integrations/oura/oauth/url", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def oura_oauth_url() -> Dict[str, Any]:
        if not (settings.oura_client_id and settings.oura_redirect_uri):
            raise HTTPException(status_code=400, detail="missing oura client_id/redirect_uri")
        return {"url": oura_tools.build_auth_url(settings.oura_client_id, settings.oura_redirect_uri)}

    # Wearables: Terra daily (200 with error if missing api key)
    @app.get("/integrations/terra/daily", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def terra_daily(user_id: str) -> Dict[str, Any]:
        api_key = settings.terra_api_key or ""
        if not api_key:
            return {"error": "missing api key"}
        return await asyncio.to_thread(terra_tools.daily_summary, api_key, user_id)

    # UI schema and mapping suggestion endpoints (in-memory/Redis only)
    @app.get("/ui/device/{provider}/{external_id}", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def ui_schema(provider: str, external_id: str) -> Dict[str, Any]:
        twin = twin_store.get(provider, external_id)
        if not twin:
            raise HTTPException(status_code=404, detail="device not found")
        # Grouped by capability with simple control templates
        caps = set(twin.get("capabilities", []) or [])
        groups: Dict[str, Any] = {}
        if any(c in caps for c in ("switch", "light")):
            groups["switchable"] = {
                "controls": [
                    {
                        "type": "toggle",
                        "action": {"capability": "switch"},
                        "actions": [
                            {"method": "POST", "path": f"/capability/{provider}/{external_id}/switch/on"},
                            {"method": "POST", "path": f"/capability/{provider}/{external_id}/switch/off"}
                        ]
                    }
                ]
            }
        if any(c in caps for c in ("switchLevel", "dimmer")):
            groups["dimmable"] = {
                "controls": [
                    {
                        "type": "slider",
                        "min": 0,
                        "max": 100,
                        "action": {"capability": "dimmer"},
                        "actions": [
                            {
                                "method": "POST",
                                "path": f"/capability/{provider}/{external_id}/dimmer/set",
                                "body": {"level": "<0-100>"}
                            }
                        ]
                    }
                ]
            }
        if any(c in caps for c in ("colorControl", "colorTemperature")):
            groups["color"] = {
                "controls": [
                    {
                        "type": "color",
                        "action": {"capability": "colorControl"},
                        "actions": [
                            {
                                "method": "POST",
                                "path": f"/capability/{provider}/{external_id}/color/hsv",
                                "body": {"h": "<0-360>", "s": "<0-100>", "v": "<0-100>"}
                            }
                        ]
                    },
                    {
                        "type": "slider",
                        "min": 153,
                        "max": 500,
                        "action": {"capability": "colorTemperature"},
                        "actions": [
                            {
                                "method": "POST",
                                "path": f"/capability/{provider}/{external_id}/color/temp",
                                "body": {"mireds": "<153-500>"}
                            }
                        ]
                    }
                ]
            }
        # Thermostat (best-effort templates)
        if any(c in caps for c in ("thermostat", "temperature", "thermostatMode", "coolingSetpoint", "heatingSetpoint")):
            groups["thermostat"] = {
                "controls": [
                    {
                        "type": "select",
                        "id": "hvac_mode",
                        "label": "Mode",
                        "options": ["off", "heat", "cool", "auto"],
                        "actions": [
                            {"method": "POST", "path": f"/capability/{provider}/{external_id}/thermostat/mode", "body": {"mode": "<off|heat|cool|auto>"}}
                        ]
                    },
                    {
                        "type": "slider",
                        "id": "cool_setpoint",
                        "label": "Cool to",
                        "min": 16,
                        "max": 30,
                        "actions": [
                            {"method": "POST", "path": f"/capability/{provider}/{external_id}/thermostat/cooling_setpoint", "body": {"celsius": "<16-30>"}}
                        ]
                    },
                    {
                        "type": "slider",
                        "id": "heat_setpoint",
                        "label": "Heat to",
                        "min": 10,
                        "max": 25,
                        "actions": [
                            {"method": "POST", "path": f"/capability/{provider}/{external_id}/thermostat/heating_setpoint", "body": {"celsius": "<10-25>"}}
                        ]
                    }
                ]
            }
        # Cover
        if any(c in caps for c in ("cover", "windowShade", "position")):
            groups["cover"] = {
                "controls": [
                    {"type": "button", "id": "open", "label": "Open", "actions": [{"method": "POST", "path": f"/capability/{provider}/{external_id}/cover/open"}]},
                    {"type": "button", "id": "close", "label": "Close", "actions": [{"method": "POST", "path": f"/capability/{provider}/{external_id}/cover/close"}]},
                    {
                        "type": "slider",
                        "id": "position",
                        "label": "Position",
                        "min": 0,
                        "max": 100,
                        "actions": [
                            {"method": "POST", "path": f"/capability/{provider}/{external_id}/cover/position", "body": {"percent": "<0-100>"}}
                        ]
                    }
                ]
            }
        # Fan
        if any(c in caps for c in ("fan", "fanSpeed", "fanControl")):
            groups["fan"] = {
                "controls": [
                    {
                        "type": "slider",
                        "id": "speed",
                        "label": "Speed",
                        "min": 0,
                        "max": 100,
                        "actions": [
                            {"method": "POST", "path": f"/capability/{provider}/{external_id}/fan/speed", "body": {"percent": "<0-100>"}}
                        ]
                    }
                ]
            }
        # Media
        if any(c in caps for c in ("media", "mediaPlayback", "audioVolume")):
            groups["media"] = {
                "controls": [
                    {"type": "button", "id": "play", "label": "Play", "actions": [{"method": "POST", "path": f"/capability/{provider}/{external_id}/media/play"}]},
                    {"type": "button", "id": "pause", "label": "Pause", "actions": [{"method": "POST", "path": f"/capability/{provider}/{external_id}/media/pause"}]},
                    {
                        "type": "slider",
                        "id": "volume",
                        "label": "Volume",
                        "min": 0,
                        "max": 100,
                        "actions": [
                            {"method": "POST", "path": f"/capability/{provider}/{external_id}/media/volume", "body": {"percent": "<0-100>"}}
                        ]
                    }
                ]
            }
        return {"provider": provider, "external_id": external_id, "name": twin.get("name"), "groups": groups}

    # Mapping suggestions store (signal-based, no persistence beyond Redis/memory)
    @app.post("/mapping/suggestions", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def add_mapping_suggestions(body: Dict[str, Any]) -> Dict[str, Any]:
        try:
            import json as _j
            key = "mapping:suggestions"
            if settings.redis_url:
                import redis  # type: ignore
                rds = redis.Redis.from_url(settings.redis_url)
                rds.set(key, _j.dumps(body))
            else:
                app.state.mapping_suggestions = body
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    @app.get("/mapping/suggestions", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def get_mapping_suggestions() -> Dict[str, Any]:
        try:
            import json as _j
            key = "mapping:suggestions"
            if settings.redis_url:
                import redis  # type: ignore
                rds = redis.Redis.from_url(settings.redis_url)
                v = rds.get(key)
                data = _j.loads(v) if v else {}
            else:
                data = getattr(app.state, "mapping_suggestions", {})
            return {"suggestions": data}
        except Exception as exc:
            return {"suggestions": {}, "error": str(exc)}

    # Home Assistant local (re-added after extended endpoints)
    @app.get("/integrations/home_assistant/entities", dependencies=[Depends(rate_limiter), Depends(require_api_key)])
    async def home_assistant_entities() -> Dict[str, Any]:
        if not (settings.home_assistant_base_url and settings.home_assistant_token):
            return {"count": 0, "entities": []}
        items = await asyncio.to_thread(ha_list, settings.home_assistant_base_url, settings.home_assistant_token)
        return {"count": len(items), "entities": items}

    return app


app = create_app()

