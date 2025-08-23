"""
Enhanced API Interface for IoT Discovery System

This module provides a comprehensive REST API for all 14 planned enhancements
to the IoT discovery system.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import json

from ..enhanced.core.enhanced_coordinator import EnhancedDiscoveryCoordinator, EnhancedCoordinatorConfig
from ..models.enhanced_models import (
    DeviceRecognitionResult, ProactiveDiscoveryEvent, WizardProgress,
    DeviceSuggestion, ErrorRecoveryPlan, PrivacyProfile, SecurityAlert,
    OneTapAction, SmartNotification, BulkOperation, SetupMetrics,
    DeviceGroup, CommunitySetup
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Enhanced IoT Discovery API",
    description="Comprehensive API for IoT device discovery and connection using all 14 planned enhancements",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global coordinator instance
_coordinator: Optional[EnhancedDiscoveryCoordinator] = None


def get_coordinator() -> EnhancedDiscoveryCoordinator:
    """Get the global coordinator instance."""
    global _coordinator
    if _coordinator is None:
        config = EnhancedCoordinatorConfig()
        _coordinator = EnhancedDiscoveryCoordinator(config)
    return _coordinator


# ============================================================================
# Pydantic Models for API Requests/Responses
# ============================================================================

class CameraRecognitionRequest(BaseModel):
    """Request for camera-based device recognition."""
    image_path: str = Field(..., description="Path to the image file")
    user_id: str = Field(..., description="User identifier")
    confidence_threshold: float = Field(0.7, description="Minimum confidence threshold")


class VoiceRecognitionRequest(BaseModel):
    """Request for voice-based device recognition."""
    audio_path: str = Field(..., description="Path to the audio file")
    user_id: str = Field(..., description="User identifier")
    language: str = Field("en", description="Language code")


class NFCRecognitionRequest(BaseModel):
    """Request for NFC-based device recognition."""
    tag_data: str = Field(..., description="NFC tag data in hex format")
    user_id: str = Field(..., description="User identifier")


class BrandWizardRequest(BaseModel):
    """Request to start a brand-specific wizard."""
    brand: str = Field(..., description="Device brand")
    device_type: str = Field(..., description="Type of device")
    user_id: str = Field(..., description="User identifier")


class DeviceSuggestionsRequest(BaseModel):
    """Request for device suggestions."""
    user_id: str = Field(..., description="User identifier")
    context: Dict[str, Any] = Field(default_factory=dict, description="Context information")
    max_suggestions: int = Field(5, description="Maximum number of suggestions")


class ErrorRecoveryRequest(BaseModel):
    """Request for error recovery."""
    user_id: str = Field(..., description="User identifier")
    error_context: Dict[str, Any] = Field(..., description="Error context information")


class PrivacyProfileRequest(BaseModel):
    """Request to create a privacy profile."""
    user_id: str = Field(..., description="User identifier")
    preferences: Dict[str, Any] = Field(..., description="Privacy preferences")


class SecurityCheckRequest(BaseModel):
    """Request for security check."""
    device_id: str = Field(..., description="Device identifier")


class OneTapActionRequest(BaseModel):
    """Request for one-tap actions."""
    user_id: str = Field(..., description="User identifier")
    context: Dict[str, Any] = Field(default_factory=dict, description="Context information")


class ExecuteActionRequest(BaseModel):
    """Request to execute a one-tap action."""
    action_id: str = Field(..., description="Action identifier")
    user_id: str = Field(..., description="User identifier")


class VoiceAssistantRequest(BaseModel):
    """Request to connect voice assistant."""
    assistant_type: str = Field(..., description="Type of voice assistant")
    user_id: str = Field(..., description="User identifier")


class DeviceGroupRequest(BaseModel):
    """Request to create a device group."""
    name: str = Field(..., description="Group name")
    device_ids: List[str] = Field(..., description="List of device IDs")
    group_type: str = Field(..., description="Type of group")
    user_id: str = Field(..., description="User identifier")


class CommunityShareRequest(BaseModel):
    """Request to share setup experience."""
    device_brand: str = Field(..., description="Device brand")
    device_model: str = Field(..., description="Device model")
    setup_steps: List[str] = Field(..., description="Setup steps")
    tips: List[str] = Field(default_factory=list, description="Tips and tricks")
    user_id: str = Field(..., description="User identifier")


class NotificationResponse(BaseModel):
    """Response for notifications."""
    notification_id: str
    notification_type: str
    title: str
    message: str
    priority: int
    timestamp: datetime
    read: bool = False


class StatusResponse(BaseModel):
    """Response for system status."""
    running: bool
    enhancements_enabled: int
    active_sessions: int
    background_tasks: int
    cache_size: int
    config: Dict[str, bool]


# ============================================================================
# ENHANCEMENT 1: Smart Device Recognition & Auto-Detection
# ============================================================================

@app.post("/recognition/camera", response_model=DeviceRecognitionResult)
async def recognize_device_camera(
    request: CameraRecognitionRequest,
    coord: EnhancedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Recognize device using camera image."""
    try:
        result = await coord.recognize_device_camera(
            image_path=request.image_path,
            user_id=request.user_id
        )
        
        # Filter by confidence threshold
        if result.confidence < request.confidence_threshold:
            raise HTTPException(
                status_code=400,
                detail=f"Recognition confidence {result.confidence} below threshold {request.confidence_threshold}"
            )
        
        return result
    except Exception as e:
        logger.error(f"Camera recognition error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/recognition/voice", response_model=DeviceRecognitionResult)
async def recognize_device_voice(
    request: VoiceRecognitionRequest,
    coord: EnhancedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Recognize device using voice input."""
    try:
        result = await coord.recognize_device_voice(
            audio_path=request.audio_path,
            user_id=request.user_id
        )
        return result
    except Exception as e:
        logger.error(f"Voice recognition error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/recognition/nfc", response_model=DeviceRecognitionResult)
async def recognize_device_nfc(
    request: NFCRecognitionRequest,
    coord: EnhancedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Recognize device using NFC tag."""
    try:
        # Convert hex string to bytes
        tag_data = bytes.fromhex(request.tag_data)
        result = await coord.recognize_device_nfc(
            tag_data=tag_data,
            user_id=request.user_id
        )
        return result
    except Exception as e:
        logger.error(f"NFC recognition error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENHANCEMENT 2: Proactive Discovery Intelligence
# ============================================================================

@app.get("/proactive/events", response_model=List[ProactiveDiscoveryEvent])
async def get_proactive_events(
    user_id: str,
    limit: int = 10,
    coord: EnhancedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Get recent proactive discovery events for a user."""
    # This would typically query a database for stored events
    # For now, return simulated events
    events = [
        ProactiveDiscoveryEvent(
            source="network_scan",
            device_hints=[{"ip": "192.168.1.100", "mac": "00:11:22:33:44:55"}],
            confidence=0.7
        ),
        ProactiveDiscoveryEvent(
            source="bluetooth_beacon",
            device_hints=[{"ble_address": "AA:BB:CC:DD:EE:FF", "rssi": -45}],
            confidence=0.6
        )
    ]
    return events[:limit]


# ============================================================================
# ENHANCEMENT 3: Guided Onboarding Wizards
# ============================================================================

@app.post("/wizards/start", response_model=Dict[str, str])
async def start_brand_wizard(
    request: BrandWizardRequest,
    coord: EnhancedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Start a brand-specific onboarding wizard."""
    try:
        wizard_id = await coord.start_brand_wizard(
            brand=request.brand,
            device_type=request.device_type,
            user_id=request.user_id
        )
        return {"wizard_id": wizard_id, "status": "started"}
    except Exception as e:
        logger.error(f"Wizard start error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/wizards/{wizard_id}/progress", response_model=WizardProgress)
async def get_wizard_progress(
    wizard_id: str,
    coord: EnhancedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Get progress for a specific wizard."""
    try:
        progress = await coord.get_wizard_progress(wizard_id)
        if progress is None:
            raise HTTPException(status_code=404, detail="Wizard not found")
        return progress
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Wizard progress error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/wizards/{wizard_id}/complete-step")
async def complete_wizard_step(
    wizard_id: str,
    step_id: str,
    coord: EnhancedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Complete a step in the wizard."""
    try:
        # This would update the wizard progress
        return {"status": "step_completed", "step_id": step_id}
    except Exception as e:
        logger.error(f"Wizard step completion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENHANCEMENT 4: Predictive Device Suggestions
# ============================================================================

@app.post("/suggestions/devices", response_model=List[DeviceSuggestion])
async def get_device_suggestions(
    request: DeviceSuggestionsRequest,
    coord: EnhancedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Get predictive device suggestions for a user."""
    try:
        suggestions = await coord.get_device_suggestions(
            user_id=request.user_id,
            context=request.context
        )
        return suggestions[:request.max_suggestions]
    except Exception as e:
        logger.error(f"Device suggestions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENHANCEMENT 5: Intelligent Error Recovery
# ============================================================================

@app.post("/error-recovery/plan", response_model=ErrorRecoveryPlan)
async def get_error_recovery_plan(
    request: ErrorRecoveryRequest,
    coord: EnhancedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Get an error recovery plan."""
    try:
        recovery_plan = await coord.handle_setup_error(
            error_context=request.error_context,
            user_id=request.user_id
        )
        return recovery_plan
    except Exception as e:
        logger.error(f"Error recovery error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/error-recovery/execute/{action_id}")
async def execute_recovery_action(
    action_id: str,
    user_id: str,
    coord: EnhancedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Execute a recovery action."""
    try:
        # This would execute the specific recovery action
        return {"status": "action_executed", "action_id": action_id}
    except Exception as e:
        logger.error(f"Recovery action execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENHANCEMENT 6: Granular Privacy Controls
# ============================================================================

@app.post("/privacy/profile", response_model=PrivacyProfile)
async def create_privacy_profile(
    request: PrivacyProfileRequest,
    coord: EnhancedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Create a privacy profile for a user."""
    try:
        profile = await coord.create_privacy_profile(
            user_id=request.user_id,
            preferences=request.preferences
        )
        return profile
    except Exception as e:
        logger.error(f"Privacy profile creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/privacy/profile/{user_id}", response_model=PrivacyProfile)
async def get_privacy_profile(
    user_id: str,
    coord: EnhancedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Get privacy profile for a user."""
    try:
        if user_id in coord.privacy_profiles:
            return coord.privacy_profiles[user_id]
        else:
            raise HTTPException(status_code=404, detail="Privacy profile not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Privacy profile retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENHANCEMENT 7: Security Hardening
# ============================================================================

@app.post("/security/check", response_model=SecurityAlert)
async def check_device_security(
    request: SecurityCheckRequest,
    coord: EnhancedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Check security status of a device."""
    try:
        alert = await coord.check_device_security(
            device_id=request.device_id
        )
        return alert
    except Exception as e:
        logger.error(f"Security check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/security/alerts/{user_id}", response_model=List[SecurityAlert])
async def get_security_alerts(
    user_id: str,
    limit: int = 10,
    coord: EnhancedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Get security alerts for a user."""
    # This would typically query a database for stored alerts
    # For now, return simulated alerts
    alerts = [
        SecurityAlert(
            device_id="device_123",
            threat_type="outdated_firmware",
            threat_level="medium",
            description="Device firmware is outdated",
            recommended_actions=["Update firmware"]
        )
    ]
    return alerts[:limit]


# ============================================================================
# ENHANCEMENT 8: Simplified Interface
# ============================================================================

@app.post("/interface/one-tap-actions", response_model=List[OneTapAction])
async def get_one_tap_actions(
    request: OneTapActionRequest,
    coord: EnhancedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Get one-tap actions for simplified setup."""
    try:
        actions = await coord.get_one_tap_actions(
            user_id=request.user_id,
            context=request.context
        )
        return actions
    except Exception as e:
        logger.error(f"One-tap actions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/interface/execute-action")
async def execute_one_tap_action(
    request: ExecuteActionRequest,
    coord: EnhancedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Execute a one-tap action."""
    try:
        success = await coord.execute_one_tap_action(
            action_id=request.action_id,
            user_id=request.user_id
        )
        return {"status": "success" if success else "failed", "action_id": request.action_id}
    except Exception as e:
        logger.error(f"Action execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/interface/bulk-operation", response_model=BulkOperation)
async def start_bulk_operation(
    operation_type: str,
    device_ids: List[str],
    user_id: str,
    coord: EnhancedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Start a bulk operation for multiple devices."""
    try:
        operation = BulkOperation(
            operation_id=f"bulk_{operation_type}_{datetime.utcnow().timestamp()}",
            operation_type=operation_type,
            device_ids=device_ids,
            total_devices=len(device_ids),
            completed_devices=0,
            estimated_completion=datetime.utcnow()
        )
        return operation
    except Exception as e:
        logger.error(f"Bulk operation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENHANCEMENT 9: Smart Notifications
# ============================================================================

@app.get("/notifications/{user_id}", response_model=List[NotificationResponse])
async def get_user_notifications(
    user_id: str,
    limit: int = 20,
    coord: EnhancedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Get notifications for a user."""
    try:
        if user_id in coord.user_preferences:
            notifications = coord.user_preferences[user_id].get("notifications", [])
            return notifications[:limit]
        else:
            return []
    except Exception as e:
        logger.error(f"Notifications retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/notifications/{user_id}/mark-read")
async def mark_notification_read(
    user_id: str,
    notification_id: str,
    coord: EnhancedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Mark a notification as read."""
    try:
        if user_id in coord.user_preferences:
            notifications = coord.user_preferences[user_id].get("notifications", [])
            for notification in notifications:
                if notification.notification_id == notification_id:
                    notification.read = True
                    break
        return {"status": "marked_read", "notification_id": notification_id}
    except Exception as e:
        logger.error(f"Mark notification read error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENHANCEMENT 10: Performance Optimizations
# ============================================================================

@app.get("/performance/cache-stats")
async def get_cache_stats(
    coord: EnhancedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Get cache statistics."""
    try:
        return {
            "cache_size": len(coord.device_cache),
            "cache_ttl": coord.config.cache_ttl,
            "max_concurrent_operations": coord.config.max_concurrent_operations
        }
    except Exception as e:
        logger.error(f"Cache stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/performance/clear-cache")
async def clear_cache(
    coord: EnhancedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Clear the device cache."""
    try:
        coord.device_cache.clear()
        return {"status": "cache_cleared", "cache_size": 0}
    except Exception as e:
        logger.error(f"Clear cache error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENHANCEMENT 11: Integration Ecosystem
# ============================================================================

@app.post("/integrations/voice-assistant")
async def connect_voice_assistant(
    request: VoiceAssistantRequest,
    coord: EnhancedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Connect to a voice assistant."""
    try:
        success = await coord.connect_voice_assistant(
            assistant_type=request.assistant_type,
            user_id=request.user_id
        )
        return {"status": "connected" if success else "failed", "assistant_type": request.assistant_type}
    except Exception as e:
        logger.error(f"Voice assistant connection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/integrations/available")
async def get_available_integrations():
    """Get list of available integrations."""
    return {
        "voice_assistants": ["alexa", "google_assistant", "siri"],
        "smart_home_hubs": ["homekit", "smartthings", "hubitat"],
        "cloud_services": ["google_home", "amazon_smart_home", "ifttt"]
    }


# ============================================================================
# ENHANCEMENT 12: Setup Analytics
# ============================================================================

@app.get("/analytics/setup-metrics/{user_id}", response_model=List[SetupMetrics])
async def get_setup_metrics(
    user_id: str,
    limit: int = 10,
    coord: EnhancedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Get setup metrics for a user."""
    # This would typically query a database for stored metrics
    # For now, return simulated metrics
    metrics = [
        SetupMetrics(
            setup_id="setup_123",
            device_id="device_123",
            start_time=datetime.utcnow(),
            completion_time=datetime.utcnow(),
            total_duration=120,
            steps_completed=5,
            total_steps=5,
            errors_encountered=0,
            success=True
        )
    ]
    return metrics[:limit]


@app.get("/analytics/user-behavior/{user_id}")
async def get_user_behavior(
    user_id: str,
    coord: EnhancedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Get user behavior analytics."""
    try:
        if "analytics_events" in coord.user_preferences:
            events = coord.user_preferences["analytics_events"]
            return {"events": events, "total_events": len(events)}
        else:
            return {"events": [], "total_events": 0}
    except Exception as e:
        logger.error(f"User behavior analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENHANCEMENT 13: Device Management
# ============================================================================

@app.post("/management/device-groups", response_model=DeviceGroup)
async def create_device_group(
    request: DeviceGroupRequest,
    coord: EnhancedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Create a device group."""
    try:
        group = await coord.create_device_group(
            name=request.name,
            device_ids=request.device_ids,
            group_type=request.group_type,
            user_id=request.user_id
        )
        return group
    except Exception as e:
        logger.error(f"Device group creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/management/device-groups/{user_id}", response_model=List[DeviceGroup])
async def get_device_groups(
    user_id: str,
    coord: EnhancedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Get device groups for a user."""
    # This would typically query a database for stored groups
    # For now, return simulated groups
    groups = [
        DeviceGroup(
            group_id="group_123",
            name="Living Room",
            description="Devices in the living room",
            device_ids=["device_1", "device_2"],
            group_type="room"
        )
    ]
    return groups


# ============================================================================
# ENHANCEMENT 14: Community Features
# ============================================================================

@app.post("/community/share-setup", response_model=CommunitySetup)
async def share_setup_experience(
    request: CommunityShareRequest,
    coord: EnhancedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Share a setup experience with the community."""
    try:
        setup = await coord.share_setup_experience(
            device_brand=request.device_brand,
            device_model=request.device_model,
            setup_steps=request.setup_steps,
            tips=request.tips,
            user_id=request.user_id
        )
        return setup
    except Exception as e:
        logger.error(f"Setup sharing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/community/setups/{device_brand}/{device_model}", response_model=List[CommunitySetup])
async def get_community_setups(
    device_brand: str,
    device_model: str,
    limit: int = 10
):
    """Get community setups for a specific device."""
    # This would typically query a database for stored setups
    # For now, return simulated setups
    setups = [
        CommunitySetup(
            setup_id="setup_123",
            user_id="user_123",
            device_brand=device_brand,
            device_model=device_model,
            setup_steps=["Step 1", "Step 2", "Step 3"],
            tips=["Tip 1", "Tip 2"],
            rating=4.5,
            review_count=10
        )
    ]
    return setups[:limit]


# ============================================================================
# System Management Endpoints
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Start the enhanced coordinator on startup."""
    global _coordinator
    if _coordinator is None:
        config = EnhancedCoordinatorConfig()
        _coordinator = EnhancedDiscoveryCoordinator(config)
    
    await _coordinator.start()
    logger.info("Enhanced IoT Discovery API started")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop the enhanced coordinator on shutdown."""
    global _coordinator
    if _coordinator:
        await _coordinator.stop()
        logger.info("Enhanced IoT Discovery API stopped")


@app.get("/status", response_model=StatusResponse)
async def get_system_status(
    coord: EnhancedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Get the current system status."""
    try:
        status = coord.get_status()
        return StatusResponse(**status)
    except Exception as e:
        logger.error(f"Status retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# ============================================================================
# WebSocket Support for Real-time Updates
# ============================================================================

class ConnectionManager:
    """Manage WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove broken connections
                self.active_connections.remove(connection)


manager = ConnectionManager()


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "ping":
                await manager.send_personal_message(
                    json.dumps({"type": "pong", "timestamp": datetime.utcnow().isoformat()}),
                    websocket
                )
            elif message.get("type") == "subscribe":
                # Subscribe to specific event types
                await manager.send_personal_message(
                    json.dumps({"type": "subscribed", "events": message.get("events", [])}),
                    websocket
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# ============================================================================
# Background Tasks
# ============================================================================

@app.post("/background/start-discovery")
async def start_background_discovery(
    background_tasks: BackgroundTasks,
    coord: EnhancedDiscoveryCoordinator = Depends(get_coordinator)
):
    """Start background discovery tasks."""
    try:
        # Add background tasks
        background_tasks.add_task(coord._network_monitoring_loop)
        background_tasks.add_task(coord._beacon_scanning_loop)
        
        return {"status": "background_discovery_started"}
    except Exception as e:
        logger.error(f"Background discovery error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
