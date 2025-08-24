"""
Mobile API endpoints for the Suggestion Engine

Provides REST API endpoints specifically designed for mobile client interactions,
including device registration, personalized suggestions, and push notifications.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from .mobile_client import MobileClientService, MobileDevice, DeviceType, NotificationPriority
from .models import SuggestionRequest, SuggestionResponse, RecommendationCard

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mobile", tags=["mobile"])

# Global mobile client service instance
_mobile_client: Optional[MobileClientService] = None


def get_mobile_client() -> MobileClientService:
    """Dependency to get the mobile client service instance."""
    if _mobile_client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mobile client service not initialized"
        )
    return _mobile_client


# Pydantic models for API requests/responses
class DeviceRegistrationRequest(BaseModel):
    device_id: str = Field(..., description="Unique device identifier")
    user_id: str = Field(..., description="User identifier")
    device_type: str = Field(..., description="Device type (android, ios, web)")
    push_token: Optional[str] = Field(None, description="Push notification token")
    app_version: str = Field("", description="Mobile app version")
    os_version: str = Field("", description="Operating system version")
    capabilities: Dict[str, Any] = Field(default_factory=dict, description="Device capabilities")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences")


class DeviceRegistrationResponse(BaseModel):
    success: bool
    device_id: str
    message: str


class SuggestionRequestModel(BaseModel):
    context_hints: Dict[str, Any] = Field(default_factory=dict, description="Context information")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences")


class SuggestionResponseModel(BaseModel):
    success: bool
    request_id: str
    recommendations: List[Dict[str, Any]]
    what_if_items: List[Dict[str, Any]]
    generated_at: datetime
    expires_at: Optional[datetime] = None


class FeedbackRequestModel(BaseModel):
    recommendation_id: str = Field(..., description="Recommendation identifier")
    feedback_type: str = Field(..., description="Type of feedback (accept, reject, snooze, edit)")
    feedback_data: Optional[Dict[str, Any]] = Field(None, description="Additional feedback data")


class FeedbackResponseModel(BaseModel):
    success: bool
    message: str


class NotificationRequestModel(BaseModel):
    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body")
    data: Dict[str, Any] = Field(default_factory=dict, description="Additional data")
    priority: str = Field("normal", description="Notification priority")
    scheduled_at: Optional[datetime] = Field(None, description="Scheduled delivery time")


class NotificationResponseModel(BaseModel):
    success: bool
    message: str


class DeviceStatusResponse(BaseModel):
    device_id: str
    user_id: str
    device_type: str
    is_active: bool
    last_seen: str
    app_version: str
    os_version: str
    has_push_token: bool
    capabilities: Dict[str, Any]
    preferences: Dict[str, Any]


# API endpoints
@router.post("/devices/register", response_model=DeviceRegistrationResponse)
async def register_device(
    request: DeviceRegistrationRequest,
    mobile_client: MobileClientService = Depends(get_mobile_client)
):
    """Register a mobile device for suggestions and notifications."""
    try:
        # Validate device type
        try:
            device_type = DeviceType(request.device_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid device type: {request.device_type}"
            )
        
        # Create device object
        device = MobileDevice(
            device_id=request.device_id,
            user_id=request.user_id,
            device_type=device_type,
            push_token=request.push_token,
            app_version=request.app_version,
            os_version=request.os_version,
            capabilities=request.capabilities,
            preferences=request.preferences
        )
        
        # Register device
        success = await mobile_client.register_device(device)
        
        if success:
            return DeviceRegistrationResponse(
                success=True,
                device_id=request.device_id,
                message="Device registered successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to register device"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering device: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete("/devices/{device_id}", response_model=DeviceRegistrationResponse)
async def unregister_device(
    device_id: str,
    mobile_client: MobileClientService = Depends(get_mobile_client)
):
    """Unregister a mobile device."""
    try:
        success = await mobile_client.unregister_device(device_id)
        
        if success:
            return DeviceRegistrationResponse(
                success=True,
                device_id=device_id,
                message="Device unregistered successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unregistering device: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/devices/{device_id}/suggestions", response_model=SuggestionResponseModel)
async def get_device_suggestions(
    device_id: str,
    request: SuggestionRequestModel,
    mobile_client: MobileClientService = Depends(get_mobile_client)
):
    """Get personalized suggestions for a specific device."""
    try:
        response = await mobile_client.get_device_suggestions(
            device_id=device_id,
            context_hints=request.context_hints,
            preferences=request.preferences
        )
        
        if response is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found or inactive"
            )
        
        # Convert recommendations to dict format
        recommendations = []
        for rec in response.recommendations:
            rec_dict = {
                "recommendation_id": rec.recommendation_id,
                "title": rec.title,
                "description": rec.description,
                "rationale": rec.rationale,
                "category": rec.category,
                "confidence": rec.confidence,
                "privacy_badge": rec.privacy_badge.value,
                "safety_badge": rec.safety_badge.value,
                "effort_rating": rec.effort_rating.value,
                "tunable_controls": rec.tunable_controls,
                "storyboard_preview": rec.storyboard_preview
            }
            recommendations.append(rec_dict)
        
        return SuggestionResponseModel(
            success=True,
            request_id=response.request_id,
            recommendations=recommendations,
            what_if_items=response.what_if_items,
            generated_at=response.generated_at,
            expires_at=response.expires_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting suggestions for device {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/devices/{device_id}/feedback", response_model=FeedbackResponseModel)
async def record_device_feedback(
    device_id: str,
    request: FeedbackRequestModel,
    mobile_client: MobileClientService = Depends(get_mobile_client)
):
    """Record feedback from a mobile device."""
    try:
        success = await mobile_client.record_mobile_feedback(
            device_id=device_id,
            recommendation_id=request.recommendation_id,
            feedback_type=request.feedback_type,
            feedback_data=request.feedback_data
        )
        
        if success:
            return FeedbackResponseModel(
                success=True,
                message="Feedback recorded successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/devices/{device_id}/notifications", response_model=NotificationResponseModel)
async def send_device_notification(
    device_id: str,
    request: NotificationRequestModel,
    mobile_client: MobileClientService = Depends(get_mobile_client)
):
    """Send a push notification to a specific device."""
    try:
        # Validate priority
        try:
            priority = NotificationPriority(request.priority.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid priority: {request.priority}"
            )
        
        success = await mobile_client.send_push_notification(
            device_id=device_id,
            title=request.title,
            body=request.body,
            data=request.data,
            priority=priority,
            scheduled_at=request.scheduled_at
        )
        
        if success:
            return NotificationResponseModel(
                success=True,
                message="Notification sent successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found or no push token"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/devices/{device_id}/status", response_model=DeviceStatusResponse)
async def get_device_status(
    device_id: str,
    mobile_client: MobileClientService = Depends(get_mobile_client)
):
    """Get status information for a device."""
    try:
        status_info = await mobile_client.get_device_status(device_id)
        
        if status_info is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )
        
        return DeviceStatusResponse(**status_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/devices/{device_id}/execute/{recommendation_id}")
async def execute_recommendation(
    device_id: str,
    recommendation_id: str,
    mobile_client: MobileClientService = Depends(get_mobile_client)
):
    """Execute a recommendation from a mobile device."""
    try:
        # Get device info
        device = mobile_client._devices.get(device_id)
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )
        
        # Execute the recommendation
        result = await mobile_client.suggestion_engine.execute_suggestion(
            user_id=device.user_id,
            recommendation_id=recommendation_id
        )
        
        return {
            "success": result.get("success", False),
            "plan_id": result.get("plan_id"),
            "message": result.get("message", "Execution completed")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing recommendation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint for mobile API."""
    return {
        "status": "healthy",
        "service": "mobile-suggestion-api",
        "timestamp": datetime.utcnow().isoformat()
    }


# Startup and shutdown events
async def startup_event():
    """Initialize the mobile client service on startup."""
    global _mobile_client
    # Note: This would need to be initialized with the actual SuggestionEngine instance
    # For now, we'll create a placeholder
    logger.info("Mobile API startup event triggered")


async def shutdown_event():
    """Cleanup the mobile client service on shutdown."""
    global _mobile_client
    if _mobile_client:
        await _mobile_client.stop()
        logger.info("Mobile API shutdown event completed")
