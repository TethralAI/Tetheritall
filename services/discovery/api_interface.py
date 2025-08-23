"""
API Interface for Unified Discovery System

Provides a simple REST API interface for the Resource Lookup Agent (RLA) and 
Connection Opportunity Agent (COA) through the Unified Discovery Coordinator.

This demonstrates how to integrate the discovery agents into a web service.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import json

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from .unified_discovery_coordinator import (
    UnifiedDiscoveryCoordinator, CoordinatorConfig, WorkflowType
)
from .resource_lookup_agent import (
    DeviceHint, AccountHint, EnvironmentContext, UserPreferences, PrivacyTier
)
from .connection_opportunity_agent import (
    UserConstraints, NetworkDiscovery, DiscoveryType
)

logger = logging.getLogger(__name__)

# Global coordinator instance
coordinator: Optional[UnifiedDiscoveryCoordinator] = None


# Pydantic models for API requests/responses
class DeviceAdditionRequest(BaseModel):
    user_id: str
    session_id: str
    device_hint: DeviceHint
    account_hint: Optional[AccountHint] = None


class FirstTimeSetupRequest(BaseModel):
    user_id: str
    session_id: str
    initial_preferences: Optional[Dict[str, Any]] = None


class OpportunityDiscoveryRequest(BaseModel):
    user_id: str
    session_id: str
    user_constraints: UserConstraints
    env_context: Dict[str, Any]


class TroubleshootingRequest(BaseModel):
    user_id: str
    session_id: str
    error_message: str
    context: Dict[str, Any]


class UserActionRequest(BaseModel):
    action: str  # accept, decline, complete, abandon
    data: Optional[Dict[str, Any]] = None


class WorkflowStatusResponse(BaseModel):
    workflow_id: str
    workflow_type: str
    current_state: str
    progress: Dict[str, Any]
    results: Dict[str, Any]
    start_time: str
    duration: float


class UserSummaryResponse(BaseModel):
    user_id: str
    active_workflows: int
    coverage_summary: Dict[str, Any]
    recent_activity: List[Dict[str, Any]]


# FastAPI app setup
app = FastAPI(
    title="IoT Discovery API",
    description="API for IoT device discovery and connection using ML-powered agents",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_coordinator() -> UnifiedDiscoveryCoordinator:
    """Dependency to get the coordinator instance."""
    if coordinator is None:
        raise HTTPException(status_code=503, detail="Discovery coordinator not initialized")
    return coordinator


@app.on_event("startup")
async def startup_event():
    """Initialize the discovery coordinator on startup."""
    global coordinator
    
    config = CoordinatorConfig(
        database_url="sqlite:///./iot_discovery.db",
        learning_enabled=True,
        privacy_by_default=True,
        gdpr_compliant=True,
    )
    
    coordinator = UnifiedDiscoveryCoordinator(config)
    await coordinator.start()
    
    logger.info("Discovery API started with coordinator")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global coordinator
    if coordinator:
        await coordinator.stop()
        logger.info("Discovery API shutdown complete")


# API Endpoints

@app.post("/workflows/first-time-setup", response_model=Dict[str, str])
async def start_first_time_setup(
    request: FirstTimeSetupRequest,
    coord: UnifiedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Start first-time setup workflow for new users."""
    try:
        workflow_id = await coord.start_first_time_setup(
            request.user_id,
            request.session_id,
            request.initial_preferences
        )
        return {"workflow_id": workflow_id, "status": "started"}
    except Exception as e:
        logger.error(f"Error starting first-time setup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/workflows/device-addition", response_model=Dict[str, str])
async def add_device(
    request: DeviceAdditionRequest,
    coord: UnifiedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Start device addition workflow."""
    try:
        workflow_id = await coord.add_device(
            request.user_id,
            request.session_id,
            request.device_hint,
            request.account_hint
        )
        return {"workflow_id": workflow_id, "status": "started"}
    except Exception as e:
        logger.error(f"Error adding device: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/workflows/opportunity-discovery", response_model=Dict[str, str])
async def start_opportunity_discovery(
    request: OpportunityDiscoveryRequest,
    coord: UnifiedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Start opportunity discovery workflow."""
    try:
        workflow_id = await coord.start_opportunity_discovery(
            request.user_id,
            request.session_id,
            request.user_constraints,
            request.env_context
        )
        return {"workflow_id": workflow_id, "status": "started"}
    except Exception as e:
        logger.error(f"Error starting opportunity discovery: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/workflows/troubleshooting", response_model=Dict[str, str])
async def start_troubleshooting(
    request: TroubleshootingRequest,
    coord: UnifiedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Start troubleshooting workflow."""
    try:
        workflow_id = await coord.troubleshoot_connection(
            request.user_id,
            request.session_id,
            request.error_message,
            request.context
        )
        return {"workflow_id": workflow_id, "status": "started"}
    except Exception as e:
        logger.error(f"Error starting troubleshooting: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/workflows/{workflow_id}/status", response_model=WorkflowStatusResponse)
async def get_workflow_status(
    workflow_id: str,
    coord: UnifiedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Get status of a specific workflow."""
    try:
        status = await coord.get_workflow_status(workflow_id)
        if status is None:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return WorkflowStatusResponse(**status)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/workflows/{workflow_id}/actions")
async def record_user_action(
    workflow_id: str,
    request: UserActionRequest,
    coord: UnifiedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Record user action for a workflow."""
    try:
        await coord.record_user_action(workflow_id, request.action, request.data)
        return {"status": "action_recorded"}
    except Exception as e:
        logger.error(f"Error recording user action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/users/{user_id}/summary", response_model=UserSummaryResponse)
async def get_user_summary(
    user_id: str,
    coord: UnifiedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Get summary of user's discovery and connection status."""
    try:
        summary = await coord.get_user_summary(user_id)
        return UserSummaryResponse(**summary)
    except Exception as e:
        logger.error(f"Error getting user summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/privacy/audit-log")
async def get_privacy_audit_log(
    user_id: Optional[str] = None,
    coord: UnifiedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Get privacy audit log."""
    try:
        audit_log = coord.get_privacy_audit_log(user_id)
        return {"audit_log": audit_log}
    except Exception as e:
        logger.error(f"Error getting privacy audit log: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Direct Agent Access (for advanced use cases)

@app.post("/rla/process-device")
async def process_device_hint(
    device_hint: DeviceHint,
    account_hint: Optional[AccountHint] = None,
    env_context: Optional[EnvironmentContext] = None,
    user_prefs: Optional[UserPreferences] = None,
    coord: UnifiedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Direct access to Resource Lookup Agent."""
    try:
        result = await coord.rla.process_device_hint(
            device_hint, account_hint, env_context, user_prefs
        )
        return result
    except Exception as e:
        logger.error(f"Error processing device hint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/coa/process-discoveries")
async def process_discoveries(
    discoveries: List[NetworkDiscovery],
    user_constraints: UserConstraints,
    env_context: Dict[str, Any],
    coord: UnifiedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Direct access to Connection Opportunity Agent."""
    try:
        result = await coord.coa.process_discoveries(
            discoveries, user_constraints, env_context
        )
        return result
    except Exception as e:
        logger.error(f"Error processing discoveries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health and monitoring endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    global coordinator
    return {
        "status": "healthy" if coordinator and coordinator._running else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "coordinator_running": coordinator._running if coordinator else False,
    }


@app.get("/metrics")
async def get_metrics(coord: UnifiedDiscoveryCoordinator = Depends(get_coordinator)):
    """Get system metrics."""
    try:
        return {
            "active_workflows": len(coord.active_workflows),
            "queue_size": coord.workflow_queue.qsize(),
            "subscribers": len(coord.state_subscribers),
            "privacy_events": len(coord.privacy_audit_log),
        }
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Example usage and documentation

@app.get("/examples")
async def get_examples():
    """Get example API usage."""
    return {
        "first_time_setup": {
            "endpoint": "POST /workflows/first-time-setup",
            "request": {
                "user_id": "user123",
                "session_id": "session456",
                "initial_preferences": {
                    "privacy_tier": "standard",
                    "quiet_hours": [22, 7]
                }
            }
        },
        "add_device": {
            "endpoint": "POST /workflows/device-addition",
            "request": {
                "user_id": "user123",
                "session_id": "session456",
                "device_hint": {
                    "brand": "Philips",
                    "model": "Hue Bulb",
                    "qr_code": "matter:123456789"
                }
            }
        },
        "opportunity_discovery": {
            "endpoint": "POST /workflows/opportunity-discovery",
            "request": {
                "user_id": "user123",
                "session_id": "session456",
                "user_constraints": {
                    "privacy_tier": "standard",
                    "time_budget_minutes": 30,
                    "noise_sensitivity": False
                },
                "env_context": {
                    "bluetooth_available": True,
                    "wifi_6_available": True
                }
            }
        }
    }


if __name__ == "__main__":
    # Run the API server
    uvicorn.run(
        "services.discovery.api_interface:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
