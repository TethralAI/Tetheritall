"""
Firebase Cloud Messaging (FCM) Provider

Handles push notifications for Android and iOS devices via Firebase.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
import aiohttp
import json
from datetime import datetime

from .base import BaseNotificationProvider
from ..models import Notification, NotificationTarget, DeliveryResult, DeliveryStatus, Platform

logger = logging.getLogger(__name__)


class FCMProvider(BaseNotificationProvider):
    """Firebase Cloud Messaging notification provider."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.server_key = config.get("server_key")
        self.project_id = config.get("project_id")
        self.fcm_url = "https://fcm.googleapis.com/fcm/send"
        
        if not self.server_key:
            logger.error("FCM server key not configured")
            self.enabled = False
            
    async def send_notification(
        self,
        notification: Notification,
        target: NotificationTarget
    ) -> DeliveryResult:
        """Send notification via FCM."""
        if not self.enabled:
            return self._create_failure_result(
                notification, target, "FCM provider not enabled"
            )
            
        if not self.validate_target(target):
            return self._create_failure_result(
                notification, target, "Invalid FCM target"
            )
            
        try:
            # Build FCM payload
            payload = self._build_fcm_payload(notification, target)
            
            # Send notification
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"key={self.server_key}",
                    "Content-Type": "application/json"
                }
                
                async with session.post(
                    self.fcm_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    response_data = await response.json()
                    
                    if response.status == 200 and response_data.get("success", 0) > 0:
                        return self._create_success_result(
                            notification, target, "FCM notification sent successfully"
                        )
                    else:
                        error_msg = response_data.get("results", [{}])[0].get("error", "Unknown FCM error")
                        return self._create_failure_result(
                            notification, target, f"FCM error: {error_msg}"
                        )
                        
        except Exception as e:
            logger.error(f"Error sending FCM notification: {e}")
            return self._create_failure_result(
                notification, target, f"FCM send error: {str(e)}"
            )
            
    async def send_bulk_notifications(
        self,
        notification: Notification,
        targets: List[NotificationTarget]
    ) -> List[DeliveryResult]:
        """Send bulk notifications via FCM."""
        if not self.enabled:
            return [
                self._create_failure_result(notification, target, "FCM provider not enabled")
                for target in targets
            ]
            
        # Filter valid FCM targets
        fcm_targets = [target for target in targets if self.validate_target(target)]
        
        if not fcm_targets:
            return [
                self._create_failure_result(notification, target, "Invalid FCM target")
                for target in targets
            ]
            
        try:
            # Build bulk FCM payload
            payload = self._build_bulk_fcm_payload(notification, fcm_targets)
            
            # Send bulk notification
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"key={self.server_key}",
                    "Content-Type": "application/json"
                }
                
                async with session.post(
                    self.fcm_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    response_data = await response.json()
                    
                    # Process results for each target
                    results = []
                    fcm_results = response_data.get("results", [])
                    
                    for i, target in enumerate(fcm_targets):
                        if i < len(fcm_results):
                            result = fcm_results[i]
                            if "message_id" in result:
                                results.append(self._create_success_result(
                                    notification, target, "FCM bulk notification sent"
                                ))
                            else:
                                error_msg = result.get("error", "Unknown FCM error")
                                results.append(self._create_failure_result(
                                    notification, target, f"FCM error: {error_msg}"
                                ))
                        else:
                            results.append(self._create_failure_result(
                                notification, target, "No FCM result received"
                            ))
                            
                    return results
                    
        except Exception as e:
            logger.error(f"Error sending FCM bulk notifications: {e}")
            return [
                self._create_failure_result(notification, target, f"FCM bulk error: {str(e)}")
                for target in fcm_targets
            ]
            
    def validate_target(self, target: NotificationTarget) -> bool:
        """Validate FCM target."""
        return (
            target.platform == Platform.FCM and
            target.token and
            len(target.token) > 0
        )
        
    def _build_fcm_payload(self, notification: Notification, target: NotificationTarget) -> Dict[str, Any]:
        """Build FCM payload for single notification."""
        payload = {
            "to": target.token,
            "priority": self._get_fcm_priority(notification.priority),
        }
        
        if notification.content:
            payload["notification"] = {
                "title": notification.content.title,
                "body": notification.content.body,
            }
            
            if notification.content.icon:
                payload["notification"]["icon"] = notification.content.icon
            if notification.content.sound:
                payload["notification"]["sound"] = notification.content.sound
            if notification.content.click_action:
                payload["notification"]["click_action"] = notification.content.click_action
                
            # Add data payload
            if notification.content.data:
                payload["data"] = notification.content.data.copy()
                
            # Add notification metadata
            payload["data"].update({
                "notification_id": notification.notification_id,
                "notification_type": notification.notification_type.value,
                "timestamp": notification.created_at.isoformat()
            })
            
        return payload
        
    def _build_bulk_fcm_payload(self, notification: Notification, targets: List[NotificationTarget]) -> Dict[str, Any]:
        """Build FCM payload for bulk notification."""
        payload = {
            "registration_ids": [target.token for target in targets],
            "priority": self._get_fcm_priority(notification.priority),
        }
        
        if notification.content:
            payload["notification"] = {
                "title": notification.content.title,
                "body": notification.content.body,
            }
            
            if notification.content.icon:
                payload["notification"]["icon"] = notification.content.icon
            if notification.content.sound:
                payload["notification"]["sound"] = notification.content.sound
            if notification.content.click_action:
                payload["notification"]["click_action"] = notification.content.click_action
                
            # Add data payload
            if notification.content.data:
                payload["data"] = notification.content.data.copy()
                
            # Add notification metadata
            payload["data"].update({
                "notification_id": notification.notification_id,
                "notification_type": notification.notification_type.value,
                "timestamp": notification.created_at.isoformat()
            })
            
        return payload
        
    def _get_fcm_priority(self, priority) -> str:
        """Convert notification priority to FCM priority."""
        priority_mapping = {
            "low": "normal",
            "normal": "normal", 
            "high": "high",
            "critical": "high"
        }
        return priority_mapping.get(priority.value, "normal")
        
    async def get_provider_status(self) -> Dict[str, Any]:
        """Get FCM provider status."""
        status = await super().get_provider_status()
        status.update({
            "server_key_configured": bool(self.server_key),
            "project_id": self.project_id,
            "fcm_url": self.fcm_url
        })
        return status
