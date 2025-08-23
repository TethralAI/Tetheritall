"""
SMS Provider

Handles SMS notifications via Twilio or other SMS services.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
import aiohttp
import json
from datetime import datetime
import base64

from .base import BaseNotificationProvider
from ..models import Notification, NotificationTarget, DeliveryResult, DeliveryStatus, Platform

logger = logging.getLogger(__name__)


class SMSProvider(BaseNotificationProvider):
    """SMS notification provider using Twilio."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.account_sid = config.get("account_sid")
        self.auth_token = config.get("auth_token")
        self.from_number = config.get("from_number")
        self.service_provider = config.get("service_provider", "twilio")
        
        # Twilio API endpoint
        self.twilio_url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        
        if not all([self.account_sid, self.auth_token, self.from_number]):
            logger.error("SMS configuration incomplete")
            self.enabled = False
            
    async def send_notification(
        self,
        notification: Notification,
        target: NotificationTarget
    ) -> DeliveryResult:
        """Send notification via SMS."""
        if not self.enabled:
            return self._create_failure_result(
                notification, target, "SMS provider not enabled"
            )
            
        if not self.validate_target(target):
            return self._create_failure_result(
                notification, target, "Invalid SMS target"
            )
            
        try:
            # Build SMS content
            message_body = self._build_sms_content(notification)
            
            # Send SMS
            if self.service_provider == "twilio":
                result = await self._send_twilio_sms(message_body, target.token)
            else:
                raise ValueError(f"Unsupported SMS provider: {self.service_provider}")
                
            if result:
                return self._create_success_result(
                    notification, target, "SMS notification sent successfully"
                )
            else:
                return self._create_failure_result(
                    notification, target, "SMS send failed"
                )
                
        except Exception as e:
            logger.error(f"Error sending SMS notification: {e}")
            return self._create_failure_result(
                notification, target, f"SMS send error: {str(e)}"
            )
            
    async def send_bulk_notifications(
        self,
        notification: Notification,
        targets: List[NotificationTarget]
    ) -> List[DeliveryResult]:
        """Send bulk notifications via SMS."""
        if not self.enabled:
            return [
                self._create_failure_result(notification, target, "SMS provider not enabled")
                for target in targets
            ]
            
        # Filter valid SMS targets
        sms_targets = [target for target in targets if self.validate_target(target)]
        
        if not sms_targets:
            return [
                self._create_failure_result(notification, target, "Invalid SMS target")
                for target in targets
            ]
            
        # Send SMS messages concurrently
        tasks = [
            self.send_notification(notification, target)
            for target in sms_targets
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(self._create_failure_result(
                    notification, sms_targets[i], f"SMS bulk error: {str(result)}"
                ))
            else:
                final_results.append(result)
                
        return final_results
        
    def validate_target(self, target: NotificationTarget) -> bool:
        """Validate SMS target."""
        if target.platform != Platform.SMS or not target.token:
            return False
            
        # Basic phone number validation
        import re
        phone_pattern = r'^\+?[1-9]\d{1,14}$'  # E.164 format
        return bool(re.match(phone_pattern, target.token.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")))
        
    def _build_sms_content(self, notification: Notification) -> str:
        """Build SMS message content."""
        if not notification.content:
            return "Notification from Tetheritall IoT System"
            
        # SMS messages should be concise
        message = f"{notification.content.title}\n{notification.content.body}"
        
        # Add priority indicator for high/critical notifications
        if notification.priority.value in ["high", "critical"]:
            message = f"[{notification.priority.value.upper()}] {message}"
            
        # Truncate if too long (SMS limit is typically 160-1600 characters)
        max_length = 1500  # Leave room for metadata
        if len(message) > max_length:
            message = message[:max_length-3] + "..."
            
        return message
        
    async def _send_twilio_sms(self, message_body: str, to_number: str) -> bool:
        """Send SMS via Twilio API."""
        try:
            # Prepare authentication
            auth = base64.b64encode(f"{self.account_sid}:{self.auth_token}".encode()).decode()
            
            # Prepare payload
            payload = {
                "From": self.from_number,
                "To": to_number,
                "Body": message_body
            }
            
            # Send request
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Basic {auth}",
                    "Content-Type": "application/x-www-form-urlencoded"
                }
                
                async with session.post(
                    self.twilio_url,
                    data=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status in [200, 201]:
                        response_data = await response.json()
                        logger.info(f"SMS sent successfully: {response_data.get('sid')}")
                        return True
                    else:
                        error_data = await response.text()
                        logger.error(f"Twilio SMS error: {error_data}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error sending Twilio SMS: {e}")
            return False
            
    async def get_provider_status(self) -> Dict[str, Any]:
        """Get SMS provider status."""
        status = await super().get_provider_status()
        status.update({
            "service_provider": self.service_provider,
            "account_sid": self.account_sid,
            "from_number": self.from_number,
            "twilio_url": self.twilio_url if self.service_provider == "twilio" else None,
            "credentials_configured": bool(self.account_sid and self.auth_token)
        })
        return status
