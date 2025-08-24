from fastapi import APIRouter, HTTPException, Query, Path, Body
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import asyncio
import json
from pydantic import BaseModel

# Import existing services
from ..agents.network_scanner import NetworkScanner
from ..agents.coordinator import DeviceCoordinator
from ..tools.discovery.mdns import mDNSDiscovery
from ..tools.discovery.ssdp import SSDPDiscovery
from ..tools.discovery.matter.bridge import MatterBridge

router = APIRouter(prefix="/api", tags=["Device Discovery"])

# Initialize services
network_scanner = NetworkScanner()
device_coordinator = DeviceCoordinator()
mdns_discovery = mDNSDiscovery()
ssdp_discovery = SSDPDiscovery()
matter_bridge = MatterBridge()

# Pydantic models for API
class DiscoveryRequest(BaseModel):
    protocols: Optional[List[str]] = ["wifi", "bluetooth", "zigbee"]
    timeout: Optional[int] = 30

class DiscoveryResponse(BaseModel):
    devices: List[Dict[str, Any]]
    total_count: int
    discovery_time_ms: int

class DeviceRegistration(BaseModel):
    device_id: str
    name: str
    type: str
    brand: Optional[str] = None
    model: Optional[str] = None
    protocol: str
    capabilities: List[str]
    metadata: Dict[str, Any] = {}

class DeviceDetails(BaseModel):
    id: str
    name: str
    type: str
    brand: Optional[str] = None
    model: Optional[str] = None
    protocol: str
    capabilities: List[str]
    metadata: Dict[str, Any]
    is_online: bool
    last_seen: datetime
    firmware_version: Optional[str] = None
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None

class CapabilitiesResponse(BaseModel):
    capabilities: List[Dict[str, Any]]

# Orchestration models
class OrchestrationRequest(BaseModel):
    intent: str
    trigger_type: str = "user"
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    context_hints: Dict[str, Any] = {}
    preferences: Dict[str, Any] = {}
    preview_mode: bool = False
    timeout_ms: Optional[int] = None

class OrchestrationResponse(BaseModel):
    plan_id: str
    status: str
    plan: Optional[Dict[str, Any]] = None
    rationale: Optional[str] = None
    approval_required: bool = False
    alternatives: List[Dict[str, Any]] = []
    warnings: List[str] = []
    errors: List[str] = []

class ExecutionPlan(BaseModel):
    plan_id: str
    status: str
    steps: List[Dict[str, Any]]
    estimated_duration: int
    resource_requirements: Dict[str, Any]

# Edge ML models
class EdgeMLRequest(BaseModel):
    model_type: str
    input_data: Dict[str, Any]
    device_id: Optional[str] = None
    privacy_level: str = "standard"

class EdgeMLResponse(BaseModel):
    result: Dict[str, Any]
    processing_time_ms: int
    model_version: str
    confidence: float

# Mock data for testing
MOCK_DEVICES = [
    {
        "id": "device_001",
        "name": "Smart Light Bulb",
        "type": "light",
        "brand": "Philips",
        "model": "Hue White",
        "protocol": "zigbee",
        "capabilities": ["on_off", "brightness", "color"],
        "signal_strength": 85,
        "is_online": True,
        "last_seen": datetime.now().isoformat(),
    },
    {
        "id": "device_002",
        "name": "Smart Thermostat",
        "type": "thermostat",
        "brand": "Nest",
        "model": "Learning Thermostat",
        "protocol": "wifi",
        "capabilities": ["temperature_control", "scheduling", "learning"],
        "signal_strength": 92,
        "is_online": True,
        "last_seen": datetime.now().isoformat(),
    },
    {
        "id": "device_003",
        "name": "Security Camera",
        "type": "camera",
        "brand": "Ring",
        "model": "Video Doorbell",
        "protocol": "wifi",
        "capabilities": ["video_stream", "motion_detection", "two_way_audio"],
        "signal_strength": 78,
        "is_online": True,
        "last_seen": datetime.now().isoformat(),
    }
]

# Device Discovery Endpoints
@router.get("/discovery/devices", response_model=DiscoveryResponse)
async def discover_devices(
    protocols: Optional[List[str]] = Query(["wifi", "bluetooth", "zigbee"]),
    timeout: Optional[int] = Query(30)
):
    """Discover devices in the network using specified protocols"""
    start_time = datetime.now()
    
    try:
        # Use existing discovery services
        discovered_devices = []
        
        if "wifi" in protocols:
            wifi_devices = await network_scanner.scan_wifi_devices()
            discovered_devices.extend(wifi_devices)
        
        if "zigbee" in protocols:
            zigbee_devices = await mdns_discovery.discover_zigbee_devices()
            discovered_devices.extend(zigbee_devices)
        
        if "matter" in protocols:
            matter_devices = await matter_bridge.discover_devices()
            discovered_devices.extend(matter_devices)
        
        # For now, return mock data with real discovery time
        discovery_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return DiscoveryResponse(
            devices=MOCK_DEVICES,
            total_count=len(MOCK_DEVICES),
            discovery_time_ms=int(discovery_time)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")

@router.get("/devices/{device_id}", response_model=DeviceDetails)
async def get_device_details(device_id: str = Path(...)):
    """Get detailed information about a specific device"""
    try:
        # Find device in mock data
        device = next((d for d in MOCK_DEVICES if d["id"] == device_id), None)
        
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        # Enhance with additional details
        device_details = DeviceDetails(
            id=device["id"],
            name=device["name"],
            type=device["type"],
            brand=device["brand"],
            model=device["model"],
            protocol=device["protocol"],
            capabilities=device["capabilities"],
            metadata={
                "manufacturer": device["brand"],
                "protocol_version": "1.0",
                "supported_features": device["capabilities"]
            },
            is_online=device["is_online"],
            last_seen=datetime.fromisoformat(device["last_seen"]),
            firmware_version="2.1.0",
            ip_address="192.168.1.100",
            mac_address="00:11:22:33:44:55"
        )
        
        return device_details
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get device details: {str(e)}")

@router.post("/devices/register")
async def register_device(registration: DeviceRegistration):
    """Register a new device with the system"""
    try:
        # Store device registration (in real implementation, save to database)
        registered_device = {
            "device_id": registration.device_id,
            "name": registration.name,
            "type": registration.type,
            "brand": registration.brand,
            "model": registration.model,
            "protocol": registration.protocol,
            "capabilities": registration.capabilities,
            "metadata": registration.metadata,
            "registered_at": datetime.now().isoformat()
        }
        
        # In real implementation, save to database
        print(f"Device registered: {registered_device}")
        
        return {"message": "Device registered successfully", "device_id": registration.device_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to register device: {str(e)}")

@router.get("/devices/{device_id}/capabilities", response_model=CapabilitiesResponse)
async def get_device_capabilities(device_id: str = Path(...)):
    """Get capabilities of a specific device"""
    try:
        # Find device in mock data
        device = next((d for d in MOCK_DEVICES if d["id"] == device_id), None)
        
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        # Convert capabilities to detailed format
        capabilities = []
        for capability in device["capabilities"]:
            capability_details = {
                "name": capability,
                "type": "action",
                "parameters": {
                    "supported": True,
                    "min_value": 0,
                    "max_value": 100
                },
                "is_supported": True
            }
            capabilities.append(capability_details)
        
        return CapabilitiesResponse(capabilities=capabilities)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get device capabilities: {str(e)}")

# Orchestration Endpoints
@router.post("/orchestration/plan", response_model=OrchestrationResponse)
async def create_execution_plan(request: OrchestrationRequest):
    """Create an execution plan for user intent"""
    try:
        # Generate a unique plan ID
        plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create a basic execution plan
        plan = {
            "steps": [
                {
                    "step_id": "step_1",
                    "action": "analyze_intent",
                    "description": f"Analyze user intent: {request.intent}",
                    "estimated_duration": 1000
                },
                {
                    "step_id": "step_2", 
                    "action": "identify_devices",
                    "description": "Identify relevant devices",
                    "estimated_duration": 2000
                },
                {
                    "step_id": "step_3",
                    "action": "execute_commands",
                    "description": "Execute device commands",
                    "estimated_duration": 3000
                }
            ],
            "estimated_duration": 6000,
            "resource_requirements": {
                "devices": ["device_001", "device_002"],
                "permissions": ["device_control"]
            }
        }
        
        return OrchestrationResponse(
            plan_id=plan_id,
            status="pending",
            plan=plan,
            rationale=f"Created plan for intent: {request.intent}",
            approval_required=False,
            warnings=[],
            errors=[]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create execution plan: {str(e)}")

@router.get("/orchestration/plan/{plan_id}", response_model=ExecutionPlan)
async def get_execution_plan(plan_id: str = Path(...)):
    """Get the status of an execution plan"""
    try:
        # Mock execution plan
        plan = ExecutionPlan(
            plan_id=plan_id,
            status="completed",
            steps=[
                {
                    "step_id": "step_1",
                    "action": "analyze_intent",
                    "status": "completed",
                    "result": "Intent analyzed successfully"
                },
                {
                    "step_id": "step_2",
                    "action": "identify_devices", 
                    "status": "completed",
                    "result": "Devices identified"
                },
                {
                    "step_id": "step_3",
                    "action": "execute_commands",
                    "status": "completed",
                    "result": "Commands executed"
                }
            ],
            estimated_duration=6000,
            resource_requirements={
                "devices": ["device_001", "device_002"],
                "permissions": ["device_control"]
            }
        )
        
        return plan
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get execution plan: {str(e)}")

@router.post("/orchestration/execute/{plan_id}")
async def execute_plan(plan_id: str = Path(...)):
    """Execute a previously created plan"""
    try:
        # Mock execution
        await asyncio.sleep(1)  # Simulate execution time
        
        return {
            "plan_id": plan_id,
            "status": "completed",
            "execution_time_ms": 5000,
            "results": {
                "devices_affected": 2,
                "commands_executed": 3,
                "success_rate": 100.0
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute plan: {str(e)}")

# Edge ML Endpoints
@router.post("/edge/ml/infer", response_model=EdgeMLResponse)
async def edge_ml_inference(request: EdgeMLRequest):
    """Perform edge ML inference"""
    try:
        # Mock ML inference
        processing_start = datetime.now()
        
        # Simulate processing time
        await asyncio.sleep(0.1)
        
        processing_time = (datetime.now() - processing_start).total_seconds() * 1000
        
        # Mock inference result
        result = {
            "prediction": "device_anomaly_detected",
            "confidence": 0.85,
            "device_id": request.device_id,
            "timestamp": datetime.now().isoformat()
        }
        
        return EdgeMLResponse(
            result=result,
            processing_time_ms=int(processing_time),
            model_version="1.2.0",
            confidence=0.85
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Edge ML inference failed: {str(e)}")

# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "device_discovery": "active",
            "orchestration": "active", 
            "edge_ml": "active"
        }
    }
