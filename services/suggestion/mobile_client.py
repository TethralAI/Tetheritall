"""
Mobile Client Integration Service

Handles communication between the central suggestion engine and mobile devices,
including push notifications, offline sync, and device-specific optimizations.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

import aiohttp
from fastapi import HTTPException

from .models import SuggestionRequest, SuggestionResponse, RecommendationCard, FeedbackRecord
from .engine import SuggestionEngine

logger = logging.getLogger(__name__)


class DeviceType(Enum):
    ANDROID = "android"
    IOS = "ios"
    WEB = "web"


class NotificationPriority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class MobileDevice:
    device_id: str
    user_id: str
    device_type: DeviceType
    push_token: Optional[str] = None
    last_seen: datetime = field(default_factory=datetime.utcnow)
    app_version: str = ""
    os_version: str = ""
    capabilities: Dict[str, Any] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True


@dataclass
class PushNotification:
    device_id: str
    title: str
    body: str
    data: Dict[str, Any] = field(default_factory=dict)
    priority: NotificationPriority = NotificationPriority.NORMAL
    ttl: int = 3600  # seconds
    scheduled_at: Optional[datetime] = None


class MobileClientService:
    """
    Service for managing mobile client interactions with the suggestion engine.
    """
    
    def __init__(self, suggestion_engine: SuggestionEngine):
        self.suggestion_engine = suggestion_engine
        self._devices: Dict[str, MobileDevice] = {}
        self._notification_queue: List[PushNotification] = []
        self._session: Optional[aiohttp.ClientSession] = None
        
    async def start(self):
        """Initialize the mobile client service."""
        self._session = aiohttp.ClientSession()
        logger.info("Mobile client service started")
        
    async def stop(self):
        """Cleanup the mobile client service."""
        if self._session:
            await self._session.close()
        logger.info("Mobile client service stopped")
    
    async def register_device(self, device: MobileDevice) -> bool:
        """Register a mobile device for suggestions and notifications."""
        try:
            self._devices[device.device_id] = device
            logger.info(f"Registered device {device.device_id} for user {device.user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to register device {device.device_id}: {e}")
            return False
    
    async def unregister_device(self, device_id: str) -> bool:
        """Unregister a mobile device."""
        try:
            if device_id in self._devices:
                del self._devices[device_id]
                logger.info(f"Unregistered device {device_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to unregister device {device_id}: {e}")
            return False
    
    async def get_device_suggestions(
        self,
        device_id: str,
        context_hints: Optional[Dict[str, Any]] = None,
        preferences: Optional[Dict[str, Any]] = None
    ) -> Optional[SuggestionResponse]:
        """Get personalized suggestions for a specific device."""
        try:
            device = self._devices.get(device_id)
            if not device or not device.is_active:
                logger.warning(f"Device {device_id} not found or inactive")
                return None
            
            # Update device preferences if provided
            if preferences:
                device.preferences.update(preferences)
            
            # Create suggestion request
            request = SuggestionRequest(
                user_id=device.user_id,
                session_id=f"mobile_{device_id}_{datetime.utcnow().isoformat()}",
                context_hints=context_hints or {},
                preferences=device.preferences
            )
            
            # Get suggestions from engine
            response = await self.suggestion_engine.generate_suggestions(request)
            
            # Update device last seen
            device.last_seen = datetime.utcnow()
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to get suggestions for device {device_id}: {e}")
            return None
    
    async def send_push_notification(
        self,
        device_id: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        scheduled_at: Optional[datetime] = None
    ) -> bool:
        """Send a push notification to a specific device."""
        try:
            device = self._devices.get(device_id)
            if not device or not device.push_token:
                logger.warning(f"Device {device_id} not found or no push token")
                return False
            
            notification = PushNotification(
                device_id=device_id,
                title=title,
                body=body,
                data=data or {},
                priority=priority,
                scheduled_at=scheduled_at
            )
            
            # Add to queue for processing
            self._notification_queue.append(notification)
            
            # Process immediately if not scheduled
            if not scheduled_at:
                await self._process_notification(notification)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send push notification to device {device_id}: {e}")
            return False
    
    async def send_suggestion_notification(
        self,
        device_id: str,
        recommendation: RecommendationCard,
        priority: NotificationPriority = NotificationPriority.NORMAL
    ) -> bool:
        """Send a notification about a new suggestion."""
        try:
            title = f"New Suggestion: {recommendation.title}"
            body = recommendation.description[:100] + "..." if len(recommendation.description) > 100 else recommendation.description
            
            data = {
                "type": "suggestion",
                "recommendation_id": recommendation.recommendation_id,
                "category": recommendation.category,
                "confidence": recommendation.confidence
            }
            
            return await self.send_push_notification(
                device_id=device_id,
                title=title,
                body=body,
                data=data,
                priority=priority
            )
            
        except Exception as e:
            logger.error(f"Failed to send suggestion notification: {e}")
            return False
    
    async def record_mobile_feedback(
        self,
        device_id: str,
        recommendation_id: str,
        feedback_type: str,
        feedback_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Record feedback from a mobile device."""
        try:
            device = self._devices.get(device_id)
            if not device:
                logger.warning(f"Device {device_id} not found")
                return False
            
            # Record feedback in suggestion engine
            await self.suggestion_engine.record_feedback(
                user_id=device.user_id,
                recommendation_id=recommendation_id,
                feedback_type=feedback_type,
                feedback_data=feedback_data
            )
            
            # Update device last seen
            device.last_seen = datetime.utcnow()
            
            logger.info(f"Recorded feedback from device {device_id} for recommendation {recommendation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to record feedback from device {device_id}: {e}")
            return False
    
    async def get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get status information for a device."""
        try:
            device = self._devices.get(device_id)
            if not device:
                return None
            
            return {
                "device_id": device.device_id,
                "user_id": device.user_id,
                "device_type": device.device_type.value,
                "is_active": device.is_active,
                "last_seen": device.last_seen.isoformat(),
                "app_version": device.app_version,
                "os_version": device.os_version,
                "has_push_token": bool(device.push_token),
                "capabilities": device.capabilities,
                "preferences": device.preferences
            }
            
        except Exception as e:
            logger.error(f"Failed to get device status for {device_id}: {e}")
            return None
    
    async def _process_notification(self, notification: PushNotification) -> bool:
        """Process a push notification by sending it to the appropriate service."""
        try:
            device = self._devices.get(notification.device_id)
            if not device or not device.push_token:
                return False
            
            # Determine push service based on device type
            if device.device_type == DeviceType.IOS:
                return await self._send_ios_notification(device, notification)
            elif device.device_type == DeviceType.ANDROID:
                return await self._send_android_notification(device, notification)
            else:
                logger.warning(f"Unsupported device type: {device.device_type}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to process notification: {e}")
            return False
    
    async def _send_ios_notification(self, device: MobileDevice, notification: PushNotification) -> bool:
        """Send notification to iOS device via APNs."""
        # This would integrate with Apple Push Notification service
        # For now, we'll simulate the notification
        logger.info(f"Would send iOS notification to {device.device_id}: {notification.title}")
        return True
    
    async def _send_android_notification(self, device: MobileDevice, notification: PushNotification) -> bool:
        """Send notification to Android device via FCM."""
        # This would integrate with Firebase Cloud Messaging
        # For now, we'll simulate the notification
        logger.info(f"Would send Android notification to {device.device_id}: {notification.title}")
        return True
    
    async def cleanup_inactive_devices(self, max_inactive_days: int = 30) -> int:
        """Remove devices that haven't been active for the specified period."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=max_inactive_days)
            inactive_devices = [
                device_id for device_id, device in self._devices.items()
                if device.last_seen < cutoff_date
            ]
            
            for device_id in inactive_devices:
                await self.unregister_device(device_id)
            
            logger.info(f"Cleaned up {len(inactive_devices)} inactive devices")
            return len(inactive_devices)
            
        except Exception as e:
            logger.error(f"Failed to cleanup inactive devices: {e}")
            return 0
