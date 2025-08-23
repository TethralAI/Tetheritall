"""
Comprehensive Commissioning API
Provides endpoints for device commissioning across multiple providers.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime

from .agent import ConnectionAgent, DeviceInfo, ConnectionStatus
from .onboarding.workflow import OnboardingWorkflow
from .onboarding.hue_workflow import HueOnboardingWorkflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/commissioning", tags=["Device Commissioning"])

# Initialize services
connection_agent = ConnectionAgent()
onboarding_workflow = OnboardingWorkflow()
hue_onboarding_workflow = HueOnboardingWorkflow()


class CommissioningRequest(BaseModel):
    device_id: str
    device_type: str
    manufacturer: str
    model: str
    ip_address: Optional[str] = None
    protocol: Optional[str] = None
    capabilities: List[str] = []
    configuration: Optional[Dict[str, Any]] = None


class HueCommissioningRequest(BaseModel):
    bridge_ip: str
    app_name: str = "iot-orchestrator"
    device_name: str = "server"


class DeviceTestRequest(BaseModel):
    device_id: str
    test_type: str = "communication"  # communication, capabilities, security


class CommissioningStatusRequest(BaseModel):
    workflow_id: str


@router.post("/start", dependencies=[Depends(require_api_key)])
async def start_commissioning(request: CommissioningRequest) -> Dict[str, Any]:
    """Start commissioning process for a device."""
    try:
        # Create device info
        device_info = DeviceInfo(
            device_id=request.device_id,
            name=request.device_id,
            model=request.model,
            manufacturer=request.manufacturer,
            ip_address=request.ip_address,
            protocol=request.protocol,
            capabilities=request.capabilities,
            endpoints=[],
            status=ConnectionStatus.DISCOVERED
        )
        
        # Start onboarding workflow
        workflow_id = await onboarding_workflow.start_onboarding(device_info)
        
        logger.info(f"Started commissioning workflow {workflow_id} for device {request.device_id}")
        
        return {
            "ok": True,
            "workflow_id": workflow_id,
            "device_id": request.device_id,
            "status": "started",
            "message": "Commissioning workflow started"
        }
        
    except Exception as e:
        logger.error(f"Error starting commissioning: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start commissioning: {str(e)}")


@router.post("/hue/start", dependencies=[Depends(require_api_key)])
async def start_hue_commissioning(request: HueCommissioningRequest) -> Dict[str, Any]:
    """Start Philips Hue specific commissioning process."""
    try:
        # Start Hue-specific onboarding workflow
        workflow_id = await hue_onboarding_workflow.start_hue_onboarding(
            request.bridge_ip,
            request.app_name,
            request.device_name
        )
        
        logger.info(f"Started Hue commissioning workflow {workflow_id} for bridge {request.bridge_ip}")
        
        return {
            "ok": True,
            "workflow_id": workflow_id,
            "bridge_ip": request.bridge_ip,
            "status": "started",
            "message": "Hue commissioning workflow started"
        }
        
    except Exception as e:
        logger.error(f"Error starting Hue commissioning: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start Hue commissioning: {str(e)}")


@router.get("/status/{workflow_id}", dependencies=[Depends(require_api_key)])
async def get_commissioning_status(workflow_id: str) -> Dict[str, Any]:
    """Get status of a commissioning workflow."""
    try:
        # Try to get Hue-specific status first
        status = hue_onboarding_workflow.get_hue_workflow_status(workflow_id)
        
        if not status:
            # Fall back to generic workflow status
            status = onboarding_workflow.get_workflow_status(workflow_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        return {
            "ok": True,
            "workflow_id": workflow_id,
            "status": status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting commissioning status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.get("/workflows", dependencies=[Depends(require_api_key)])
async def list_commissioning_workflows() -> Dict[str, Any]:
    """List all commissioning workflows."""
    try:
        # Get all workflows from both systems
        generic_workflows = onboarding_workflow.get_all_workflows()
        hue_workflows = []
        
        # Get Hue workflows
        for workflow_id in hue_onboarding_workflow._workflows.keys():
            status = hue_onboarding_workflow.get_hue_workflow_status(workflow_id)
            if status:
                hue_workflows.append(status)
        
        all_workflows = generic_workflows + hue_workflows
        
        return {
            "ok": True,
            "workflows": all_workflows,
            "total_workflows": len(all_workflows),
            "generic_workflows": len(generic_workflows),
            "hue_workflows": len(hue_workflows)
        }
        
    except Exception as e:
        logger.error(f"Error listing commissioning workflows: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list workflows: {str(e)}")


@router.post("/test", dependencies=[Depends(require_api_key)])
async def test_device(request: DeviceTestRequest) -> Dict[str, Any]:
    """Test device communication and capabilities."""
    try:
        if request.test_type == "communication":
            # Test basic communication
            result = await connection_agent.test_communication(request.device_id)
            return {
                "ok": True,
                "device_id": request.device_id,
                "test_type": request.test_type,
                "result": result
            }
        elif request.test_type == "capabilities":
            # Test device capabilities
            result = await connection_agent.test_capabilities(request.device_id)
            return {
                "ok": True,
                "device_id": request.device_id,
                "test_type": request.test_type,
                "result": result
            }
        elif request.test_type == "security":
            # Test security features
            result = await connection_agent.test_security(request.device_id)
            return {
                "ok": True,
                "device_id": request.device_id,
                "test_type": request.test_type,
                "result": result
            }
        else:
            raise HTTPException(status_code=400, detail=f"Unknown test type: {request.test_type}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing device: {e}")
        raise HTTPException(status_code=500, detail=f"Device test failed: {str(e)}")


@router.post("/cancel/{workflow_id}", dependencies=[Depends(require_api_key)])
async def cancel_commissioning(workflow_id: str) -> Dict[str, Any]:
    """Cancel a commissioning workflow."""
    try:
        # Try to cancel in both workflow systems
        generic_cancelled = onboarding_workflow.cancel_workflow(workflow_id)
        hue_cancelled = hue_onboarding_workflow.cancel_workflow(workflow_id)
        
        if generic_cancelled or hue_cancelled:
            return {
                "ok": True,
                "workflow_id": workflow_id,
                "status": "cancelled",
                "message": "Workflow cancelled successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Workflow not found or already completed")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling commissioning: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel workflow: {str(e)}")


@router.get("/providers", dependencies=[Depends(require_api_key)])
async def list_supported_providers() -> Dict[str, Any]:
    """List supported device providers and their capabilities."""
    try:
        providers = {
            "philips_hue": {
                "name": "Philips Hue",
                "description": "Philips Hue smart lighting system",
                "capabilities": ["switchable", "dimmable", "color_control", "color_temperature"],
                "protocols": ["http", "zigbee"],
                "discovery_methods": ["cloud", "network_scan"],
                "commissioning_steps": [
                    "bridge_discovery",
                    "bridge_pairing", 
                    "device_discovery",
                    "device_analysis",
                    "device_commissioning",
                    "capability_mapping"
                ]
            },
            "smartthings": {
                "name": "SmartThings",
                "description": "Samsung SmartThings platform",
                "capabilities": ["switchable", "dimmable", "color_control", "sensors"],
                "protocols": ["http", "websocket"],
                "discovery_methods": ["cloud"],
                "commissioning_steps": [
                    "oauth_authentication",
                    "device_discovery",
                    "device_commissioning"
                ]
            },
            "zigbee2mqtt": {
                "name": "Zigbee2MQTT",
                "description": "Zigbee to MQTT bridge",
                "capabilities": ["switchable", "dimmable", "color_control", "sensors"],
                "protocols": ["mqtt", "zigbee"],
                "discovery_methods": ["mqtt_broker"],
                "commissioning_steps": [
                    "broker_connection",
                    "device_discovery",
                    "device_commissioning"
                ]
            }
        }
        
        return {
            "ok": True,
            "providers": providers,
            "total_providers": len(providers)
        }
        
    except Exception as e:
        logger.error(f"Error listing providers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list providers: {str(e)}")


@router.get("/capabilities", dependencies=[Depends(require_api_key)])
async def list_supported_capabilities() -> Dict[str, Any]:
    """List supported device capabilities."""
    try:
        capabilities = {
            "switchable": {
                "name": "Switchable",
                "description": "Can be turned on/off",
                "commands": ["turn_on", "turn_off", "get_state"],
                "providers": ["philips_hue", "smartthings", "zigbee2mqtt"]
            },
            "dimmable": {
                "name": "Dimmable",
                "description": "Can adjust brightness level",
                "commands": ["set_brightness"],
                "providers": ["philips_hue", "smartthings", "zigbee2mqtt"]
            },
            "color_control": {
                "name": "Color Control",
                "description": "Can change color (HSV)",
                "commands": ["set_color_hsv", "set_color_temp"],
                "providers": ["philips_hue", "smartthings", "zigbee2mqtt"]
            },
            "color_temperature": {
                "name": "Color Temperature",
                "description": "Can adjust color temperature",
                "commands": ["set_color_temp"],
                "providers": ["philips_hue", "smartthings", "zigbee2mqtt"]
            },
            "sensors": {
                "name": "Sensors",
                "description": "Can read sensor data",
                "commands": ["get_temperature", "get_humidity", "get_motion"],
                "providers": ["smartthings", "zigbee2mqtt"]
            }
        }
        
        return {
            "ok": True,
            "capabilities": capabilities,
            "total_capabilities": len(capabilities)
        }
        
    except Exception as e:
        logger.error(f"Error listing capabilities: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list capabilities: {str(e)}")


@router.post("/cleanup", dependencies=[Depends(require_api_key)])
async def cleanup_completed_workflows() -> Dict[str, Any]:
    """Clean up completed workflows."""
    try:
        # Clean up both workflow systems
        onboarding_workflow.cleanup_completed_workflows()
        hue_onboarding_workflow.cleanup_completed_workflows()
        
        return {
            "ok": True,
            "message": "Completed workflows cleaned up successfully"
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up workflows: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup workflows: {str(e)}")


# Helper function for API key dependency (placeholder)
def require_api_key():
    """Placeholder for API key validation."""
    return True
