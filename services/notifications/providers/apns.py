"""
Apple Push Notification Service (APNS) Provider

Handles push notifications for iOS devices via Apple's APNS.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
import aiohttp
import json
import jwt
import time
from datetime import datetime

from .base import BaseNotificationProvider
from ..models import Notification, NotificationTarget, DeliveryResult, DeliveryStatus, Platform

logger = logging.getLogger(__name__)


class APNSProvider(BaseNotificationProvider):
    """Apple Push Notification Service provider."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.key_id = config.get("key_id")
        self.team_id = config.get("team_id")
        self.bundle_id = config.get("bundle_id")
        self.private_key = config.get("private_key")
        self.production = config.get("production", False)
        
        # APNS endpoints
        self.apns_url = (
            "https://api.push.apple.com/3/device/" if self.production
            else "https://api.sandbox.push.apple.com/3/device/"
        )
        
        if not all([self.key_id, self.team_id, self.bundle_id, self.private_key]):
            logger.error("APNS configuration incomplete")
            self.enabled = False
            
    async def send_notification(
        self,
        notification: Notification,
        target: NotificationTarget
    ) -> DeliveryResult:
        """Send notification via APNS."""
        if not self.enabled:
            return self._create_failure_result(
                notification, target, "APNS provider not enabled"
            )
            
        if not self.validate_target(target):
            return self._create_failure_result(
                notification, target, "Invalid APNS target"
            )
            
        try:
            # Build APNS payload
            payload = self._build_apns_payload(notification)
            
            # Generate JWT token
            auth_token = self._generate_jwt_token()
            
            # Send notification
            async with aiohttp.ClientSession() as session:
                headers = {
                    "authorization": f"bearer {auth_token}",
                    "apns-topic": self.bundle_id,
                    "content-type": "application/json"
                }
                
                # Add priority header
                if notification.priority.value == "critical":
                    headers["apns-priority"] = "10"
                else:
                    headers["apns-priority"] = "5"
                
                url = f"{self.apns_url}{target.token}"
                
                async with session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        return self._create_success_result(
                            notification, target, "APNS notification sent successfully"
                        )
                    else:
                        error_data = await response.text()
                        return self._create_failure_result(
                            notification, target, f"APNS error: {error_data}", str(response.status)
                        )
                        
        except Exception as e:
            logger.error(f"Error sending APNS notification: {e}")
            return self._create_failure_result(
                notification, target, f"APNS send error: {str(e)}"
            )
            
    async def send_bulk_notifications(
        self,
        notification: Notification,
        targets: List[NotificationTarget]
    ) -> List[DeliveryResult]:
        """Send bulk notifications via APNS (concurrent individual sends)."""
        if not self.enabled:
            return [
                self._create_failure_result(notification, target, "APNS provider not enabled")
                for target in targets
            ]
            
        # Filter valid APNS targets
        apns_targets = [target for target in targets if self.validate_target(target)]
        
        if not apns_targets:
            return [
                self._create_failure_result(notification, target, "Invalid APNS target")
                for target in targets
            ]
            
        # Send notifications concurrently
        tasks = [
            self.send_notification(notification, target)
            for target in apns_targets
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(self._create_failure_result(
                    notification, apns_targets[i], f"APNS bulk error: {str(result)}"
                ))
            else:
                final_results.append(result)
                
        return final_results
        
    def validate_target(self, target: NotificationTarget) -> bool:
        """Validate APNS target."""
        return (
            target.platform == Platform.APNS and
            target.token and
            len(target.token) == 64  # APNS device tokens are 64 hex characters
        )
        
    def _build_apns_payload(self, notification: Notification) -> Dict[str, Any]:
        """Build APNS payload."""
        payload = {"aps": {}}
        
        if notification.content:
            # Alert payload
            payload["aps"]["alert"] = {
                "title": notification.content.title,
                "body": notification.content.body
            }
            
            # Sound
            if notification.content.sound:
                payload["aps"]["sound"] = notification.content.sound
                
            # Badge
            if notification.content.badge is not None:
                payload["aps"]["badge"] = notification.content.badge
                
            # Custom data
            if notification.content.data:
                payload.update(notification.content.data)
                
        # Add notification metadata
        payload.update({
            "notification_id": notification.notification_id,
            "notification_type": notification.notification_type.value,
            "timestamp": notification.created_at.isoformat()
        })
        
        return payload
        
    def _generate_jwt_token(self) -> str:
        """Generate JWT token for APNS authentication."""
        headers = {
            "alg": "ES256",
            "kid": self.key_id
        }
        
        payload = {
            "iss": self.team_id,
            "iat": int(time.time())
        }
        
        # Note: In production, you would load the private key from a file or secure storage
        # For this implementation, we'll use a placeholder
        token = jwt.encode(payload, self.private_key, algorithm="ES256", headers=headers)
        return token
        
    async def get_provider_status(self) -> Dict[str, Any]:
        """Get APNS provider status."""
        status = await super().get_provider_status()
        status.update({
            "key_id": self.key_id,
            "team_id": self.team_id,
            "bundle_id": self.bundle_id,
            "production": self.production,
            "apns_url": self.apns_url,
            "private_key_configured": bool(self.private_key)
        })
        return status
