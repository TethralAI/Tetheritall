"""
Tetheritall Core API Server
Main entry point for the Tetheritall orchestration platform.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from starlette_exporter import PrometheusMiddleware, handle_metrics
import time
import yaml
from pydantic import BaseModel

# Shared imports
from shared.config.settings import settings
from shared.database.api_database import create_all, get_session_factory
from shared.database.models import Base

# Service imports
from services.connection.agent import ConnectionAgent
from services.ml.orchestrator import MLOrchestrator
from services.orchestration.engine import OrchestrationEngine
from services.security.guard import SecurityGuard
from services.edge.computing import EdgeComputing
from services.iot import IoTHubManager
from services.realtime import WebSocketManager, RealtimeEvent, EventType
from services.realtime.websocket_manager import ClientType, SubscriptionType
from services.notifications import NotificationManager
from services.cache import CacheManager, OfflineManager
from services.voice import VoiceManager
from services.device_mapping import DeviceMapper

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

# Set up logging
logger = logging.getLogger(__name__)


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
        
        # Instrument FastAPI
        FastAPIInstrumentor.instrument()
        HTTPXClientInstrumentor.instrument()
        SQLAlchemyInstrumentor.instrument()
        RedisInstrumentor.instrument()
    except Exception:
        pass


# Global service instances
connection_agent: Optional[ConnectionAgent] = None
ml_orchestrator: Optional[MLOrchestrator] = None
orchestration_engine: Optional[OrchestrationEngine] = None
security_guard: Optional[SecurityGuard] = None
edge_computing: Optional[EdgeComputing] = None
iot_hub_manager: Optional[IoTHubManager] = None
websocket_manager: Optional[WebSocketManager] = None
notification_manager: Optional[NotificationManager] = None
cache_manager: Optional[CacheManager] = None
offline_manager: Optional[OfflineManager] = None
voice_manager: Optional[VoiceManager] = None
device_mapper: Optional[DeviceMapper] = None

# Phase 2 service instances
device_registry = None
communication_manager = None
state_manager = None
event_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    global connection_agent, ml_orchestrator, orchestration_engine, security_guard, edge_computing, iot_hub_manager, websocket_manager
    global notification_manager, cache_manager, offline_manager, voice_manager, device_mapper
    global device_registry, communication_manager, state_manager, event_manager
    
    # Initialize database (tables already created manually)
    # create_all(settings.database_url)  # Skipped due to CockroachDB version parsing issue
    
    # Initialize services
    connection_agent = ConnectionAgent()
    ml_orchestrator = MLOrchestrator()
    orchestration_engine = OrchestrationEngine()
    security_guard = SecurityGuard()
    edge_computing = EdgeComputing()
    iot_hub_manager = IoTHubManager()
    websocket_manager = WebSocketManager()
    cache_manager = CacheManager(redis_url=settings.redis_url)
    notification_manager = NotificationManager()
    offline_manager = OfflineManager(cache_manager)
    voice_manager = VoiceManager()
    device_mapper = DeviceMapper()
    
    # Start background tasks
    asyncio.create_task(connection_agent.start())
    asyncio.create_task(ml_orchestrator.start())
    asyncio.create_task(orchestration_engine.start())
    asyncio.create_task(security_guard.start())
    asyncio.create_task(edge_computing.start())
    asyncio.create_task(iot_hub_manager.start())
    asyncio.create_task(websocket_manager.start())
    asyncio.create_task(cache_manager.start())
    asyncio.create_task(notification_manager.start())
    asyncio.create_task(offline_manager.start())
    asyncio.create_task(voice_manager.start())
    asyncio.create_task(device_mapper.start())
    
    # Initialize Phase 2 services from connection agent
    if connection_agent:
        device_registry = connection_agent._device_registry
        communication_manager = connection_agent._communication_manager
        state_manager = connection_agent._state_manager
        event_manager = connection_agent._event_manager
    
    yield
    
    # Shutdown
    if connection_agent:
        await connection_agent.stop()
    if ml_orchestrator:
        await ml_orchestrator.stop()
    if orchestration_engine:
        await orchestration_engine.stop()
    if security_guard:
        await security_guard.stop()
    if edge_computing:
        await edge_computing.stop()
    if iot_hub_manager:
        await iot_hub_manager.stop()
    if websocket_manager:
        await websocket_manager.stop()
    if notification_manager:
        await notification_manager.stop()
    if cache_manager:
        await cache_manager.stop()
    if offline_manager:
        await offline_manager.stop()
    if voice_manager:
        await voice_manager.stop()
    if device_mapper:
        await device_mapper.stop()


# Initialize tracing
_init_tracing("tetheritall-api")

# Create FastAPI app
app = FastAPI(
    title="Tetheritall Core API",
    description="Orchestration platform for IoT discovery, ML processing, and distributed edge computing",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(PrometheusMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key security
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(api_key: str = Depends(api_key_header)) -> str:
    """Validate API key."""
    # For testing, always accept test-api-key
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    if api_key == "test-api-key":
        return api_key
    if settings.api_token and api_key == settings.api_token:
        return api_key
    raise HTTPException(status_code=401, detail="Invalid API key")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "trace_id": _current_trace_id(),
        "services": {
            "connection": connection_agent.is_running() if connection_agent else False,
            "ml_orchestrator": ml_orchestrator.is_running() if ml_orchestrator else False,
            "orchestration": orchestration_engine.is_running() if orchestration_engine else False,
            "security": security_guard.is_running() if security_guard else False,
            "edge_computing": edge_computing.is_running() if edge_computing else False,
            "iot_hub_manager": iot_hub_manager.is_running() if iot_hub_manager else False,
            "websocket_manager": websocket_manager.get_connection_stats()["running"] if websocket_manager else False,
            "notification_manager": notification_manager.stats["running"] if notification_manager else False,
            "cache_manager": cache_manager.get_statistics()["running"] if cache_manager else False,
            "offline_manager": offline_manager.get_statistics()["running"] if offline_manager else False,
            "voice_manager": voice_manager.get_statistics()["running"] if voice_manager else False,
            "device_mapper": device_mapper.is_running() if device_mapper else False,
            "device_registry": device_registry is not None,
            "communication_manager": communication_manager is not None,
            "state_manager": state_manager is not None,
            "event_manager": event_manager is not None,
        }
    }


# Metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return handle_metrics()


# Discovery endpoints
@app.get("/discovery/devices")
async def list_devices(api_key: str = Depends(get_api_key)):
    """List discovered devices."""
    if not connection_agent:
        raise HTTPException(status_code=503, detail="Connection service not available")
    return await connection_agent.list_devices()


@app.post("/discovery/scan")
async def start_scan(api_key: str = Depends(get_api_key)):
    """Start a new discovery scan."""
    if not connection_agent:
        raise HTTPException(status_code=503, detail="Connection service not available")
    return await connection_agent.start_scan()


# ML Orchestration endpoints
@app.get("/ml/models")
async def list_models(api_key: str = Depends(get_api_key)):
    """List available ML models."""
    if not ml_orchestrator:
        raise HTTPException(status_code=503, detail="ML orchestrator not available")
    return await ml_orchestrator.list_models()


@app.post("/ml/inference")
async def run_inference(request: Dict[str, Any], api_key: str = Depends(get_api_key)):
    """Run ML inference."""
    if not ml_orchestrator:
        raise HTTPException(status_code=503, detail="ML orchestrator not available")
    return await ml_orchestrator.run_inference(request)


# Orchestration endpoints
@app.get("/orchestration/workflows")
async def list_workflows(api_key: str = Depends(get_api_key)):
    """List orchestration workflows."""
    if not orchestration_engine:
        raise HTTPException(status_code=503, detail="Orchestration engine not available")
    return await orchestration_engine.list_workflows()


@app.post("/orchestration/workflows")
async def create_workflow(workflow: Dict[str, Any], api_key: str = Depends(get_api_key)):
    """Create a new orchestration workflow."""
    if not orchestration_engine:
        raise HTTPException(status_code=503, detail="Orchestration engine not available")
    return await orchestration_engine.create_workflow(workflow)


# Security endpoints
@app.get("/security/audit")
async def get_audit_logs(api_key: str = Depends(get_api_key)):
    """Get security audit logs."""
    if not security_guard:
        raise HTTPException(status_code=503, detail="Security guard not available")
    return await security_guard.get_audit_logs()


# Phase 2 endpoints

# Device Registry endpoints
@app.get("/devices")
async def get_devices(api_key: str = Depends(get_api_key)):
    """Get all registered devices."""
    if not device_registry:
        raise HTTPException(status_code=503, detail="Device registry not available")
    return await device_registry.get_devices()


@app.get("/devices/{device_id}")
async def get_device(device_id: str, api_key: str = Depends(get_api_key)):
    """Get a specific device."""
    if not device_registry:
        raise HTTPException(status_code=503, detail="Device registry not available")
    device = await device_registry.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@app.get("/devices/statistics")
async def get_device_statistics(api_key: str = Depends(get_api_key)):
    """Get device registry statistics."""
    if not device_registry:
        raise HTTPException(status_code=503, detail="Device registry not available")
    return await device_registry.get_device_statistics()


# State Management endpoints
@app.get("/devices/{device_id}/state")
async def get_device_state(device_id: str, api_key: str = Depends(get_api_key)):
    """Get device state."""
    if not state_manager:
        raise HTTPException(status_code=503, detail="State manager not available")
    state = await state_manager.get_device_state(device_id)
    if not state:
        raise HTTPException(status_code=404, detail="Device state not found")
    return state


@app.get("/devices/states")
async def get_device_states(api_key: str = Depends(get_api_key)):
    """Get all device states."""
    if not state_manager:
        raise HTTPException(status_code=503, detail="State manager not available")
    return await state_manager.get_device_states()


@app.get("/devices/states/statistics")
async def get_state_statistics(api_key: str = Depends(get_api_key)):
    """Get state management statistics."""
    if not state_manager:
        raise HTTPException(status_code=503, detail="State manager not available")
    return await state_manager.get_state_statistics()


# Communication endpoints
@app.post("/devices/{device_id}/command")
async def send_command(device_id: str, command: Dict[str, Any], api_key: str = Depends(get_api_key)):
    """Send a command to a device."""
    if not communication_manager:
        raise HTTPException(status_code=503, detail="Communication manager not available")
    return await communication_manager.send_command(device_id, command.get("type", ""), command.get("parameters", {}))


@app.get("/communication/statistics")
async def get_communication_statistics(api_key: str = Depends(get_api_key)):
    """Get communication statistics."""
    if not communication_manager:
        raise HTTPException(status_code=503, detail="Communication manager not available")
    return await communication_manager.get_message_statistics()


# Event System endpoints
@app.get("/events")
async def get_events(api_key: str = Depends(get_api_key)):
    """Get recent events."""
    if not event_manager:
        raise HTTPException(status_code=503, detail="Event manager not available")
    return await event_manager.get_event_history(limit=100)


@app.get("/events/statistics")
async def get_event_statistics(api_key: str = Depends(get_api_key)):
    """Get event system statistics."""
    if not event_manager:
        raise HTTPException(status_code=503, detail="Event manager not available")
    return await event_manager.get_event_statistics()


# Phase 3: ML Orchestration endpoints
@app.get("/ml/models")
async def list_ml_models(api_key: str = Depends(get_api_key)):
    """List all ML models."""
    if not ml_orchestrator:
        raise HTTPException(status_code=503, detail="ML Orchestrator not available")
    models = await ml_orchestrator.list_models()
    return [{"model_id": model.model_id, "name": model.name, "type": model.model_type.value, 
             "status": model.status.value, "version": model.version} for model in models]


@app.post("/ml/models/{model_id}/load")
async def load_ml_model(model_id: str, api_key: str = Depends(get_api_key)):
    """Load an ML model."""
    if not ml_orchestrator:
        raise HTTPException(status_code=503, detail="ML Orchestrator not available")
    success = await ml_orchestrator.load_model(model_id)
    return {"success": success, "model_id": model_id}


@app.post("/ml/inference")
async def run_inference(request: Dict[str, Any], api_key: str = Depends(get_api_key)):
    """Run ML inference."""
    if not ml_orchestrator:
        raise HTTPException(status_code=503, detail="ML Orchestrator not available")
    request_id = await ml_orchestrator.run_inference(
        model_id=request["model_id"],
        input_data=request["input_data"],
        priority=request.get("priority", "normal"),
        use_quantum=request.get("use_quantum", False),
        quantum_backend=request.get("quantum_backend")
    )
    return {"request_id": request_id, "status": "submitted"}


@app.get("/ml/inference/{request_id}")
async def get_inference_result(request_id: str, api_key: str = Depends(get_api_key)):
    """Get inference result."""
    if not ml_orchestrator:
        raise HTTPException(status_code=503, detail="ML Orchestrator not available")
    result = await ml_orchestrator.get_inference_result(request_id)
    if not result:
        raise HTTPException(status_code=404, detail="Inference result not found")
    return {
        "request_id": result.request_id,
        "model_id": result.model_id,
        "output_data": result.output_data,
        "confidence": result.confidence,
        "processing_time": result.processing_time,
        "timestamp": result.timestamp.isoformat()
    }


@app.get("/ml/statistics")
async def get_ml_statistics(api_key: str = Depends(get_api_key)):
    """Get ML orchestrator statistics."""
    if not ml_orchestrator:
        raise HTTPException(status_code=503, detail="ML Orchestrator not available")
    return await ml_orchestrator.get_orchestrator_statistics()


# Phase 3: Security endpoints
@app.post("/security/authenticate")
async def authenticate_user(request: Dict[str, Any], api_key: str = Depends(get_api_key)):
    """Authenticate a user."""
    if not security_guard:
        raise HTTPException(status_code=503, detail="Security Guard not available")
    return await security_guard.authenticate_user(
        user_id=request["user_id"],
        credentials=request["credentials"],
        source_ip=request.get("source_ip", "unknown")
    )


@app.post("/security/authorize")
async def authorize_access(request: Dict[str, Any], api_key: str = Depends(get_api_key)):
    """Authorize access to a resource."""
    if not security_guard:
        raise HTTPException(status_code=503, detail="Security Guard not available")
    return await security_guard.authorize_access(
        user_id=request["user_id"],
        resource=request["resource"],
        action=request["action"],
        source_ip=request.get("source_ip", "unknown")
    )


@app.post("/security/encrypt")
async def encrypt_data(request: Dict[str, Any], api_key: str = Depends(get_api_key)):
    """Encrypt data."""
    if not security_guard:
        raise HTTPException(status_code=503, detail="Security Guard not available")
    encrypted_data = await security_guard.encrypt_data(
        data=request["data"],
        key_id=request.get("key_id", "default"),
        use_quantum_resistant=request.get("use_quantum_resistant", False)
    )
    return {"encrypted_data": encrypted_data}


@app.post("/security/decrypt")
async def decrypt_data(request: Dict[str, Any], api_key: str = Depends(get_api_key)):
    """Decrypt data."""
    if not security_guard:
        raise HTTPException(status_code=503, detail="Security Guard not available")
    decrypted_data = await security_guard.decrypt_data(
        encrypted_data=request["encrypted_data"],
        key_id=request.get("key_id", "default"),
        use_quantum_resistant=request.get("use_quantum_resistant", False)
    )
    return {"decrypted_data": decrypted_data}


@app.get("/security/events")
async def get_security_events(limit: int = 100, api_key: str = Depends(get_api_key)):
    """Get security events."""
    if not security_guard:
        raise HTTPException(status_code=503, detail="Security Guard not available")
    events = await security_guard.get_security_events(limit)
    return [{"event_id": event.event_id, "event_type": event.event_type.value,
             "timestamp": event.timestamp.isoformat(), "threat_level": event.threat_level.value,
             "source_ip": event.source_ip, "user_id": event.user_id} for event in events]


@app.get("/security/threats")
async def get_threat_alerts(status: str = "active", api_key: str = Depends(get_api_key)):
    """Get threat alerts."""
    if not security_guard:
        raise HTTPException(status_code=503, detail="Security Guard not available")
    alerts = await security_guard.get_threat_alerts(status)
    return [{"alert_id": alert.alert_id, "threat_type": alert.threat_type,
             "threat_level": alert.threat_level.value, "description": alert.description,
             "timestamp": alert.timestamp.isoformat(), "status": alert.status} for alert in alerts]


@app.get("/security/statistics")
async def get_security_statistics(api_key: str = Depends(get_api_key)):
    """Get security statistics."""
    if not security_guard:
        raise HTTPException(status_code=503, detail="Security Guard not available")
    return await security_guard.get_security_statistics()


# Phase 3: Quantum Security endpoints
@app.post("/security/quantum/key-exchange")
async def perform_quantum_key_exchange(request: Dict[str, Any], api_key: str = Depends(get_api_key)):
    """Perform quantum key exchange."""
    if not security_guard:
        raise HTTPException(status_code=503, detail="Security Guard not available")
    return await security_guard.perform_quantum_key_exchange(
        protocol=request.get("protocol", "bb84")
    )


@app.get("/security/quantum/algorithms")
async def get_quantum_resistant_algorithms(api_key: str = Depends(get_api_key)):
    """Get available quantum-resistant algorithms."""
    if not security_guard:
        raise HTTPException(status_code=503, detail="Security Guard not available")
    return await security_guard.get_quantum_resistant_algorithms()


@app.get("/security/quantum/protocols")
async def get_quantum_key_exchange_protocols(api_key: str = Depends(get_api_key)):
    """Get available quantum key exchange protocols."""
    if not security_guard:
        raise HTTPException(status_code=503, detail="Security Guard not available")
    return await security_guard.get_quantum_key_exchange_protocols()


# Phase 3: Quantum ML endpoints
@app.get("/ml/quantum/backends")
async def get_quantum_backends(api_key: str = Depends(get_api_key)):
    """Get available quantum backends."""
    if not ml_orchestrator:
        raise HTTPException(status_code=503, detail="ML Orchestrator not available")
    return await ml_orchestrator.get_quantum_backends()


@app.get("/ml/quantum/algorithms")
async def get_quantum_resistant_algorithms_ml(api_key: str = Depends(get_api_key)):
    """Get available quantum-resistant algorithms for ML."""
    if not ml_orchestrator:
        raise HTTPException(status_code=503, detail="ML Orchestrator not available")
    return await ml_orchestrator.get_quantum_resistant_algorithms()


# Phase 3: Edge Computing endpoints
@app.get("/edge/nodes")
async def list_edge_nodes(api_key: str = Depends(get_api_key)):
    """List all edge nodes."""
    if not edge_computing:
        raise HTTPException(status_code=503, detail="Edge Computing not available")
    nodes = await edge_computing.list_edge_nodes()
    return [{"node_id": node.node_id, "name": node.name, "location": node.location,
             "status": node.status.value, "capabilities": node.capabilities,
             "last_heartbeat": node.last_heartbeat.isoformat()} for node in nodes]


@app.post("/edge/nodes")
async def register_edge_node(request: Dict[str, Any], api_key: str = Depends(get_api_key)):
    """Register a new edge node."""
    if not edge_computing:
        raise HTTPException(status_code=503, detail="Edge Computing not available")
    node_id = await edge_computing.register_edge_node(request)
    return {"node_id": node_id, "status": "registered"}


@app.delete("/edge/nodes/{node_id}")
async def unregister_edge_node(node_id: str, api_key: str = Depends(get_api_key)):
    """Unregister an edge node."""
    if not edge_computing:
        raise HTTPException(status_code=503, detail="Edge Computing not available")
    success = await edge_computing.unregister_edge_node(node_id)
    return {"success": success, "node_id": node_id}


@app.post("/edge/workloads")
async def submit_workload(request: Dict[str, Any], api_key: str = Depends(get_api_key)):
    """Submit a workload for execution."""
    if not edge_computing:
        raise HTTPException(status_code=503, detail="Edge Computing not available")
    workload_id = await edge_computing.submit_workload(request)
    return {"workload_id": workload_id, "status": "submitted"}


@app.get("/edge/workloads/{workload_id}")
async def get_workload_status(workload_id: str, api_key: str = Depends(get_api_key)):
    """Get workload status."""
    if not edge_computing:
        raise HTTPException(status_code=503, detail="Edge Computing not available")
    status = await edge_computing.get_workload_status(workload_id)
    if not status:
        raise HTTPException(status_code=404, detail="Workload not found")
    return status


@app.delete("/edge/workloads/{workload_id}")
async def stop_workload(workload_id: str, api_key: str = Depends(get_api_key)):
    """Stop a workload."""
    if not edge_computing:
        raise HTTPException(status_code=503, detail="Edge Computing not available")
    success = await edge_computing.stop_workload(workload_id)
    return {"success": success, "workload_id": workload_id}


@app.get("/edge/statistics")
async def get_edge_statistics(api_key: str = Depends(get_api_key)):
    """Get edge computing statistics."""
    if not edge_computing:
        raise HTTPException(status_code=503, detail="Edge Computing not available")
    return await edge_computing.get_edge_computing_statistics()


# IoT Hub Management endpoints
@app.get("/iot/hubs")
async def list_iot_hubs(api_key: str = Depends(get_api_key)):
    """List all connected IoT hubs."""
    if not iot_hub_manager:
        raise HTTPException(status_code=503, detail="IoT Hub Manager not available")
    hubs = await iot_hub_manager.list_hubs()
    return [{"hub_id": hub_id, "name": hub.config.name, "type": hub.config.hub_type,
             "status": hub.status.value, "device_count": len(hub.devices)}
            for hub_id, hub in hubs.items()]


@app.post("/iot/hubs")
async def add_iot_hub(config: Dict[str, Any], api_key: str = Depends(get_api_key)):
    """Add a new IoT hub."""
    if not iot_hub_manager:
        raise HTTPException(status_code=503, detail="IoT Hub Manager not available")
    
    # Convert dict to HubConfig
    from services.iot.hubs.base import HubConfig
    from urllib.parse import urlparse
    
    # Parse base_url if provided, otherwise use host/port
    host = "localhost"
    port = 80
    if config.get("base_url"):
        parsed_url = urlparse(config.get("base_url"))
        host = parsed_url.hostname or "localhost"
        port = parsed_url.port or (443 if parsed_url.scheme == "https" else 80)
    else:
        host = config.get("host", "localhost")
        port = config.get("port", 80)
    
    hub_config = HubConfig(
        hub_id=config.get("hub_id"),
        name=config.get("name"),
        hub_type=config.get("hub_type"),
        host=host,
        port=port,
        username=config.get("username"),
        password=config.get("password"),
        api_key=config.get("api_key"),
        token=config.get("token"),
        ssl_verify=config.get("ssl_verify", True),
        timeout=config.get("timeout", 30),
        retry_attempts=config.get("retry_attempts", 3),
        custom_config=config.get("custom_config", {})
    )
    
    hub_id = await iot_hub_manager.add_hub(hub_config)
    return {"hub_id": hub_id, "status": "added"}


@app.delete("/iot/hubs/{hub_id}")
async def remove_iot_hub(hub_id: str, api_key: str = Depends(get_api_key)):
    """Remove an IoT hub."""
    if not iot_hub_manager:
        raise HTTPException(status_code=503, detail="IoT Hub Manager not available")
    success = await iot_hub_manager.remove_hub(hub_id)
    return {"success": success, "hub_id": hub_id}


@app.get("/iot/devices")
async def list_iot_devices(api_key: str = Depends(get_api_key)):
    """List all IoT devices across all hubs."""
    if not iot_hub_manager:
        raise HTTPException(status_code=503, detail="IoT Hub Manager not available")
    devices = await iot_hub_manager.get_all_devices()
    return [{"device_id": device.device_id, "name": device.name, "type": device.device_type.value,
             "hub_id": device.hub_id, "capabilities": [cap.value for cap in device.capabilities],
             "status": device.status.value} for device in devices.values()]


@app.get("/iot/devices/{device_id}")
async def get_iot_device(device_id: str, api_key: str = Depends(get_api_key)):
    """Get a specific IoT device."""
    if not iot_hub_manager:
        raise HTTPException(status_code=503, detail="IoT Hub Manager not available")
    device = await iot_hub_manager.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"device_id": device.device_id, "name": device.name, "type": device.device_type.value,
            "hub_id": device.hub_id, "capabilities": [cap.value for cap in device.capabilities],
            "status": device.status.value, "state": device.state}


@app.post("/iot/devices/{device_id}/control")
async def control_iot_device(device_id: str, command: Dict[str, Any], api_key: str = Depends(get_api_key)):
    """Control an IoT device."""
    if not iot_hub_manager:
        raise HTTPException(status_code=503, detail="IoT Hub Manager not available")
    result = await iot_hub_manager.control_device(device_id, command)
    return {"device_id": device_id, "result": result}


@app.get("/iot/statistics")
async def get_iot_statistics(api_key: str = Depends(get_api_key)):
    """Get IoT hub manager statistics."""
    if not iot_hub_manager:
        raise HTTPException(status_code=503, detail="IoT Hub Manager not available")
    return await iot_hub_manager.get_statistics()


@app.post("/iot/discovery")
async def start_iot_discovery(api_key: str = Depends(get_api_key)):
    """Start IoT device discovery across all hubs."""
    if not iot_hub_manager:
        raise HTTPException(status_code=503, detail="IoT Hub Manager not available")
    await iot_hub_manager.start_discovery()
    return {"status": "discovery_started"}


@app.get("/iot/events")
async def get_iot_events(api_key: str = Depends(get_api_key)):
    """Get recent IoT events."""
    if not iot_hub_manager:
        raise HTTPException(status_code=503, detail="IoT Hub Manager not available")
    events = await iot_hub_manager.get_recent_events()
    return {"events": events}


# Notification endpoints
@app.post("/notifications/send")
async def send_notification(notification_data: Dict[str, Any], api_key: str = Depends(get_api_key)):
    """Send a notification to users."""
    if not notification_manager:
        raise HTTPException(status_code=503, detail="Notification Manager not available")
    
    try:
        from services.notifications.models import Notification
        notification = Notification.from_dict(notification_data)
        result = await notification_manager.send_notification(notification)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid notification data: {e}")


@app.get("/notifications/statistics")
async def get_notification_stats(api_key: str = Depends(get_api_key)):
    """Get notification statistics."""
    if not notification_manager:
        raise HTTPException(status_code=503, detail="Notification Manager not available")
    return notification_manager.get_statistics()


# Cache endpoints
@app.get("/cache/statistics")
async def get_cache_stats(api_key: str = Depends(get_api_key)):
    """Get cache statistics."""
    if not cache_manager:
        raise HTTPException(status_code=503, detail="Cache Manager not available")
    return cache_manager.get_statistics()


@app.post("/cache/clear")
async def clear_cache(cache_type: Optional[str] = None, api_key: str = Depends(get_api_key)):
    """Clear cache entries."""
    if not cache_manager:
        raise HTTPException(status_code=503, detail="Cache Manager not available")
    
    from services.cache.models import CacheType
    cache_type_enum = None
    if cache_type:
        try:
            cache_type_enum = CacheType(cache_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid cache type: {cache_type}")
    
    cleared = await cache_manager.clear(cache_type_enum)
    return {"success": True, "cleared_entries": cleared}


# Offline support endpoints
@app.get("/offline/statistics")
async def get_offline_stats(api_key: str = Depends(get_api_key)):
    """Get offline manager statistics."""
    if not offline_manager:
        raise HTTPException(status_code=503, detail="Offline Manager not available")
    return offline_manager.get_statistics()


@app.post("/offline/device-command")
async def execute_offline_device_command(
    command_data: Dict[str, Any], 
    api_key: str = Depends(get_api_key)
):
    """Execute device command with offline support."""
    if not offline_manager:
        raise HTTPException(status_code=503, detail="Offline Manager not available")
    
    device_id = command_data.get("device_id")
    command = command_data.get("command", {})
    priority = command_data.get("priority", 0)
    
    if not device_id:
        raise HTTPException(status_code=400, detail="device_id is required")
    
    result = await offline_manager.execute_device_command(device_id, command, priority)
    return result


@app.get("/offline/action/{action_id}")
async def get_offline_action_status(action_id: str, api_key: str = Depends(get_api_key)):
    """Get status of an offline action."""
    if not offline_manager:
        raise HTTPException(status_code=503, detail="Offline Manager not available")
    
    status = await offline_manager.get_offline_action_status(action_id)
    if not status:
        raise HTTPException(status_code=404, detail="Action not found")
    
    return status


# Voice control endpoints
@app.post("/voice/command")
async def process_voice_command(
    command_data: Dict[str, Any], 
    api_key: str = Depends(get_api_key)
):
    """Process a voice command."""
    if not voice_manager:
        raise HTTPException(status_code=503, detail="Voice Manager not available")
    
    text = command_data.get("text", "")
    assistant = command_data.get("assistant", "custom")
    user_id = command_data.get("user_id")
    session_id = command_data.get("session_id")
    context = command_data.get("context", {})
    
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    
    try:
        from services.voice.models import VoiceAssistant
        assistant_enum = VoiceAssistant(assistant)
    except ValueError:
        assistant_enum = VoiceAssistant.CUSTOM
    
    response = await voice_manager.process_voice_command(
        raw_text=text,
        assistant=assistant_enum,
        user_id=user_id,
        session_id=session_id,
        context=context
    )
    
    return response.to_dict()


@app.post("/voice/device-mapping")
async def add_voice_device_mapping(
    mapping_data: Dict[str, Any], 
    api_key: str = Depends(get_api_key)
):
    """Add device voice mapping."""
    if not voice_manager:
        raise HTTPException(status_code=503, detail="Voice Manager not available")
    
    device_id = mapping_data.get("device_id")
    voice_names = mapping_data.get("voice_names", [])
    aliases = mapping_data.get("aliases", [])
    room = mapping_data.get("room")
    device_type = mapping_data.get("device_type")
    capabilities = mapping_data.get("capabilities", [])
    
    if not device_id or not voice_names:
        raise HTTPException(status_code=400, detail="device_id and voice_names are required")
    
    success = await voice_manager.add_device_mapping(
        device_id=device_id,
        voice_names=voice_names,
        aliases=aliases,
        room=room,
        device_type=device_type,
        capabilities=capabilities
    )
    
    return {"success": success}


@app.get("/voice/statistics")
async def get_voice_stats(api_key: str = Depends(get_api_key)):
    """Get voice control statistics."""
    if not voice_manager:
        raise HTTPException(status_code=503, detail="Voice Manager not available")
    return voice_manager.get_statistics()


# WebSocket Real-time endpoints
@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    api_key: str = None,
    client_type: str = "web_app",
    user_id: str = None
):
    """WebSocket endpoint for real-time communication."""
    if not websocket_manager:
        await websocket.close(code=1011, reason="WebSocket Manager not available")
        return
    
    # Validate API key
    if not api_key or api_key != "test-api-key":
        await websocket.close(code=1008, reason="Invalid API key")
        return
    
    try:
        # Parse client type
        try:
            client_type_enum = ClientType(client_type)
        except ValueError:
            client_type_enum = ClientType.WEB_APP
        
        # Connect client
        client_id = await websocket_manager.connect_client(
            websocket=websocket,
            client_type=client_type_enum,
            user_id=user_id
        )
        
        # Keep connection alive and handle disconnection
        try:
            while True:
                # Wait for client messages (if any)
                try:
                    message = await websocket.receive_text()
                    # Handle client messages (subscription updates, etc.)
                    try:
                        data = json.loads(message)
                        if data.get("action") == "update_subscriptions":
                            subscriptions = {SubscriptionType(s) for s in data.get("subscriptions", ["all"])}
                            device_filters = set(data.get("device_filters", []))
                            hub_filters = set(data.get("hub_filters", []))
                            await websocket_manager.update_client_subscriptions(
                                client_id, subscriptions, device_filters, hub_filters
                            )
                    except Exception as e:
                        logger.error(f"Error processing client message: {e}")
                except WebSocketDisconnect:
                    break
                    
        except WebSocketDisconnect:
            pass
        finally:
            await websocket_manager.disconnect_client(client_id)
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=1011, reason="Internal error")


@app.get("/realtime/stats")
async def get_realtime_stats(api_key: str = Depends(get_api_key)):
    """Get WebSocket connection statistics."""
    if not websocket_manager:
        raise HTTPException(status_code=503, detail="WebSocket Manager not available")
    return websocket_manager.get_connection_stats()


@app.post("/realtime/broadcast")
async def broadcast_event(event_data: Dict[str, Any], api_key: str = Depends(get_api_key)):
    """Broadcast an event to all connected clients."""
    if not websocket_manager:
        raise HTTPException(status_code=503, detail="WebSocket Manager not available")
    
    try:
        event = RealtimeEvent.from_dict(event_data)
        await websocket_manager.broadcast_event(event)
        return {"success": True, "event_id": event.event_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid event data: {e}")


@app.post("/realtime/send/{user_id}")
async def send_to_user(user_id: str, event_data: Dict[str, Any], api_key: str = Depends(get_api_key)):
    """Send an event to a specific user."""
    if not websocket_manager:
        raise HTTPException(status_code=503, detail="WebSocket Manager not available")
    
    try:
        event = RealtimeEvent.from_dict(event_data)
        event.user_id = user_id
        await websocket_manager.send_to_user(user_id, event)
        return {"success": True, "event_id": event.event_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid event data: {e}")


# Device Mapping endpoints
@app.get("/device-mapping/statistics")
async def get_device_mapping_stats(api_key: str = Depends(get_api_key)):
    """Get device mapping statistics."""
    if not device_mapper:
        raise HTTPException(status_code=503, detail="Device Mapper not available")
    return await device_mapper.get_mapper_statistics()


@app.get("/device-mapping/summary")
async def get_mapping_summary(user_id: Optional[str] = None, api_key: str = Depends(get_api_key)):
    """Get device mapping summary."""
    if not device_mapper:
        raise HTTPException(status_code=503, detail="Device Mapper not available")
    return await device_mapper.get_mapping_summary(user_id)


@app.get("/device-mapping/devices")
async def get_user_devices(user_id: str, api_key: str = Depends(get_api_key)):
    """Get all device mappings for a user."""
    if not device_mapper:
        raise HTTPException(status_code=503, detail="Device Mapper not available")
    mappings = await device_mapper.get_user_mappings(user_id)
    return [mapping.to_dict() for mapping in mappings]


@app.get("/device-mapping/devices/{mapping_id}")
async def get_device_mapping(mapping_id: str, api_key: str = Depends(get_api_key)):
    """Get a specific device mapping."""
    if not device_mapper:
        raise HTTPException(status_code=503, detail="Device Mapper not available")
    mapping = await device_mapper.get_device_mapping(mapping_id)
    if not mapping:
        raise HTTPException(status_code=404, detail="Device mapping not found")
    return mapping.to_dict()


@app.post("/device-mapping/devices")
async def create_device_mapping(mapping_data: Dict[str, Any], api_key: str = Depends(get_api_key)):
    """Create a new device mapping."""
    if not device_mapper:
        raise HTTPException(status_code=503, detail="Device Mapper not available")
    
    try:
        from services.device_mapping.models import DeviceCategory
        category = DeviceCategory(mapping_data.get("category", "other"))
        
        mapping = await device_mapper.create_device_mapping(
            device_id=mapping_data["device_id"],
            hub_id=mapping_data["hub_id"],
            user_id=mapping_data["user_id"],
            name=mapping_data["name"],
            category=category,
            room_id=mapping_data.get("room_id"),
            controls=mapping_data.get("controls", []),
            voice_aliases=mapping_data.get("voice_aliases", []),
            tags=mapping_data.get("tags", [])
        )
        return mapping.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid mapping data: {e}")


@app.post("/device-mapping/devices/standard")
async def create_standard_mapping(mapping_data: Dict[str, Any], api_key: str = Depends(get_api_key)):
    """Create a standard device mapping based on device type."""
    if not device_mapper:
        raise HTTPException(status_code=503, detail="Device Mapper not available")
    
    try:
        mapping = await device_mapper.create_standard_mapping(
            device_id=mapping_data["device_id"],
            hub_id=mapping_data["hub_id"],
            user_id=mapping_data["user_id"],
            name=mapping_data["name"],
            device_type=mapping_data["device_type"],
            room_id=mapping_data.get("room_id")
        )
        return mapping.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid mapping data: {e}")


@app.put("/device-mapping/devices/{mapping_id}")
async def update_device_mapping(mapping_id: str, updates: Dict[str, Any], api_key: str = Depends(get_api_key)):
    """Update a device mapping."""
    if not device_mapper:
        raise HTTPException(status_code=503, detail="Device Mapper not available")
    
    mapping = await device_mapper.update_device_mapping(mapping_id, updates)
    if not mapping:
        raise HTTPException(status_code=404, detail="Device mapping not found")
    return mapping.to_dict()


@app.delete("/device-mapping/devices/{mapping_id}")
async def delete_device_mapping(mapping_id: str, api_key: str = Depends(get_api_key)):
    """Delete a device mapping."""
    if not device_mapper:
        raise HTTPException(status_code=503, detail="Device Mapper not available")
    
    success = await device_mapper.delete_device_mapping(mapping_id)
    if not success:
        raise HTTPException(status_code=404, detail="Device mapping not found")
    return {"success": True, "mapping_id": mapping_id}


# Room Management endpoints
@app.get("/device-mapping/rooms")
async def get_all_rooms(api_key: str = Depends(get_api_key)):
    """Get all rooms."""
    if not device_mapper:
        raise HTTPException(status_code=503, detail="Device Mapper not available")
    rooms = await device_mapper.get_all_rooms()
    return [room.to_dict() for room in rooms]


@app.get("/device-mapping/rooms/{room_id}")
async def get_room(room_id: str, api_key: str = Depends(get_api_key)):
    """Get a specific room."""
    if not device_mapper:
        raise HTTPException(status_code=503, detail="Device Mapper not available")
    room = await device_mapper.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room.to_dict()


@app.post("/device-mapping/rooms")
async def create_room(room_data: Dict[str, Any], api_key: str = Depends(get_api_key)):
    """Create a new room."""
    if not device_mapper:
        raise HTTPException(status_code=503, detail="Device Mapper not available")
    
    try:
        room = await device_mapper.create_room(room_data)
        return room.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid room data: {e}")


@app.put("/device-mapping/rooms/{room_id}")
async def update_room(room_id: str, updates: Dict[str, Any], api_key: str = Depends(get_api_key)):
    """Update a room."""
    if not device_mapper:
        raise HTTPException(status_code=503, detail="Device Mapper not available")
    
    room = await device_mapper.update_room(room_id, updates)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room.to_dict()


@app.delete("/device-mapping/rooms/{room_id}")
async def delete_room(room_id: str, api_key: str = Depends(get_api_key)):
    """Delete a room."""
    if not device_mapper:
        raise HTTPException(status_code=503, detail="Device Mapper not available")
    
    try:
        success = await device_mapper.delete_room(room_id)
        if not success:
            raise HTTPException(status_code=404, detail="Room not found")
        return {"success": True, "room_id": room_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Device Discovery endpoints
@app.get("/device-mapping/discover/{hub_id}")
async def discover_devices(hub_id: str, user_id: str, api_key: str = Depends(get_api_key)):
    """Discover devices available for mapping from a hub."""
    if not device_mapper:
        raise HTTPException(status_code=503, detail="Device Mapper not available")
    
    devices = await device_mapper.discover_devices_for_mapping(hub_id, user_id)
    return {"hub_id": hub_id, "devices": devices}


@app.get("/device-mapping/search")
async def search_devices(query: str, user_id: Optional[str] = None, api_key: str = Depends(get_api_key)):
    """Search for devices by name, alias, or tag."""
    if not device_mapper:
        raise HTTPException(status_code=503, detail="Device Mapper not available")
    
    mappings = await device_mapper.search_devices(query, user_id)
    return [mapping.to_dict() for mapping in mappings]


# Voice Integration endpoints
@app.get("/device-mapping/voice/aliases")
async def get_voice_aliases(api_key: str = Depends(get_api_key)):
    """Get all voice aliases."""
    if not device_mapper:
        raise HTTPException(status_code=503, detail="Device Mapper not available")
    return await device_mapper.get_voice_aliases()


@app.get("/device-mapping/voice/find/{alias}")
async def find_device_by_voice(alias: str, api_key: str = Depends(get_api_key)):
    """Find a device by voice alias."""
    if not device_mapper:
        raise HTTPException(status_code=503, detail="Device Mapper not available")
    
    mapping = await device_mapper.find_device_by_voice_alias(alias)
    if not mapping:
        raise HTTPException(status_code=404, detail="Device not found")
    return mapping.to_dict()


# User Preferences endpoints
@app.get("/device-mapping/preferences/{user_id}/{device_id}")
async def get_user_preferences(user_id: str, device_id: str, api_key: str = Depends(get_api_key)):
    """Get user preferences for a device."""
    if not device_mapper:
        raise HTTPException(status_code=503, detail="Device Mapper not available")
    
    preferences = await device_mapper.get_user_preferences(user_id, device_id)
    if not preferences:
        raise HTTPException(status_code=404, detail="Preferences not found")
    return preferences.to_dict()


@app.put("/device-mapping/preferences/{user_id}/{device_id}")
async def update_user_preferences(user_id: str, device_id: str, preferences: Dict[str, Any], api_key: str = Depends(get_api_key)):
    """Update user preferences for a device."""
    if not device_mapper:
        raise HTTPException(status_code=503, detail="Device Mapper not available")
    
    success = await device_mapper.update_user_preferences(user_id, device_id, preferences)
    if not success:
        raise HTTPException(status_code=404, detail="Device mapping not found")
    return {"success": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
