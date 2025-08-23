"""
Web Push Provider

Handles push notifications for web browsers via Web Push protocol.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
import aiohttp
import json
from datetime import datetime
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend

from .base import BaseNotificationProvider
from ..models import Notification, NotificationTarget, DeliveryResult, DeliveryStatus, Platform

logger = logging.getLogger(__name__)


class WebPushProvider(BaseNotificationProvider):
    """Web Push notification provider."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.vapid_private_key = config.get("vapid_private_key")
        self.vapid_public_key = config.get("vapid_public_key")
        self.vapid_subject = config.get("vapid_subject", "mailto:support@tetheritall.com")
        
        if not all([self.vapid_private_key, self.vapid_public_key]):
            logger.error("Web Push VAPID keys not configured")
            self.enabled = False
            
    async def send_notification(
        self,
        notification: Notification,
        target: NotificationTarget
    ) -> DeliveryResult:
        """Send notification via Web Push."""
        if not self.enabled:
            return self._create_failure_result(
                notification, target, "Web Push provider not enabled"
            )
            
        if not self.validate_target(target):
            return self._create_failure_result(
                notification, target, "Invalid Web Push target"
            )
            
        try:
            # Parse subscription info
            subscription = json.loads(target.token)
            endpoint = subscription["endpoint"]
            
            # Build Web Push payload
            payload = self._build_web_push_payload(notification)
            
            # Generate VAPID headers
            vapid_headers = self._generate_vapid_headers(endpoint)
            
            # Send notification
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json",
                    "TTL": "86400",  # 24 hours
                    **vapid_headers
                }
                
                async with session.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status in [200, 201, 204]:
                        return self._create_success_result(
                            notification, target, "Web Push notification sent successfully"
                        )
                    else:
                        error_data = await response.text()
                        return self._create_failure_result(
                            notification, target, f"Web Push error: {error_data}", str(response.status)
                        )
                        
        except Exception as e:
            logger.error(f"Error sending Web Push notification: {e}")
            return self._create_failure_result(
                notification, target, f"Web Push send error: {str(e)}"
            )
            
    async def send_bulk_notifications(
        self,
        notification: Notification,
        targets: List[NotificationTarget]
    ) -> List[DeliveryResult]:
        """Send bulk notifications via Web Push (concurrent individual sends)."""
        if not self.enabled:
            return [
                self._create_failure_result(notification, target, "Web Push provider not enabled")
                for target in targets
            ]
            
        # Filter valid Web Push targets
        web_push_targets = [target for target in targets if self.validate_target(target)]
        
        if not web_push_targets:
            return [
                self._create_failure_result(notification, target, "Invalid Web Push target")
                for target in targets
            ]
            
        # Send notifications concurrently
        tasks = [
            self.send_notification(notification, target)
            for target in web_push_targets
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(self._create_failure_result(
                    notification, web_push_targets[i], f"Web Push bulk error: {str(result)}"
                ))
            else:
                final_results.append(result)
                
        return final_results
        
    def validate_target(self, target: NotificationTarget) -> bool:
        """Validate Web Push target."""
        if target.platform != Platform.WEB_PUSH or not target.token:
            return False
            
        try:
            # Validate subscription format
            subscription = json.loads(target.token)
            required_keys = ["endpoint", "keys"]
            return all(key in subscription for key in required_keys)
        except (json.JSONDecodeError, KeyError):
            return False
            
    def _build_web_push_payload(self, notification: Notification) -> Dict[str, Any]:
        """Build Web Push payload."""
        payload = {}
        
        if notification.content:
            payload = {
                "title": notification.content.title,
                "body": notification.content.body,
                "icon": notification.content.icon or "/default-icon.png",
                "badge": "/badge-icon.png",
                "tag": notification.notification_id,
                "requireInteraction": notification.priority.value in ["high", "critical"],
                "data": {
                    "notification_id": notification.notification_id,
                    "notification_type": notification.notification_type.value,
                    "timestamp": notification.created_at.isoformat(),
                    **(notification.content.data or {})
                }
            }
            
            # Add image if provided
            if notification.content.image:
                payload["image"] = notification.content.image
                
            # Add actions
            if notification.content.actions:
                payload["actions"] = notification.content.actions
                
            # Add click action
            if notification.content.click_action:
                payload["data"]["click_action"] = notification.content.click_action
                
        return payload
        
    def _generate_vapid_headers(self, endpoint: str) -> Dict[str, str]:
        """Generate VAPID authentication headers."""
        # This is a simplified VAPID header generation
        # In production, you would use a proper VAPID library
        
        # Extract audience from endpoint
        from urllib.parse import urlparse
        parsed_url = urlparse(endpoint)
        audience = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # Create JWT claims
        import time
        import jwt
        
        claims = {
            "aud": audience,
            "exp": int(time.time()) + 86400,  # 24 hours
            "sub": self.vapid_subject
        }
        
        # Sign with VAPID private key
        # Note: This is a simplified implementation
        token = jwt.encode(claims, self.vapid_private_key, algorithm="ES256")
        
        return {
            "Authorization": f"vapid t={token}, k={self.vapid_public_key}",
            "Crypto-Key": f"p256ecdsa={self.vapid_public_key}"
        }
        
    async def get_provider_status(self) -> Dict[str, Any]:
        """Get Web Push provider status."""
        status = await super().get_provider_status()
        status.update({
            "vapid_subject": self.vapid_subject,
            "vapid_keys_configured": bool(self.vapid_private_key and self.vapid_public_key)
        })
        return status
