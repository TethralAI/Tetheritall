"""
Base Notification Provider

Abstract base class for all notification providers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from ..models import Notification, NotificationTarget, DeliveryResult, DeliveryStatus

logger = logging.getLogger(__name__)


class BaseNotificationProvider(ABC):
    """Abstract base class for notification providers."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get("enabled", False)
        self.rate_limit = config.get("rate_limit", 100)  # requests per minute
        self.retry_attempts = config.get("retry_attempts", 3)
        self.timeout = config.get("timeout", 30)
        
    @abstractmethod
    async def send_notification(
        self,
        notification: Notification,
        target: NotificationTarget
    ) -> DeliveryResult:
        """Send a notification to a specific target."""
        pass
        
    @abstractmethod
    async def send_bulk_notifications(
        self,
        notification: Notification,
        targets: List[NotificationTarget]
    ) -> List[DeliveryResult]:
        """Send a notification to multiple targets."""
        pass
        
    @abstractmethod
    def validate_target(self, target: NotificationTarget) -> bool:
        """Validate if a target is valid for this provider."""
        pass
        
    async def get_provider_status(self) -> Dict[str, Any]:
        """Get provider status and health information."""
        return {
            "enabled": self.enabled,
            "provider": self.__class__.__name__,
            "rate_limit": self.rate_limit,
            "retry_attempts": self.retry_attempts,
            "timeout": self.timeout
        }
        
    def _create_success_result(
        self,
        notification: Notification,
        target: NotificationTarget,
        message: str = "Delivered successfully"
    ) -> DeliveryResult:
        """Create a successful delivery result."""
        return DeliveryResult(
            notification_id=notification.notification_id,
            target=target,
            status=DeliveryStatus.DELIVERED,
            message=message,
            delivered_at=datetime.utcnow()
        )
        
    def _create_failure_result(
        self,
        notification: Notification,
        target: NotificationTarget,
        error_message: str,
        error_code: Optional[str] = None
    ) -> DeliveryResult:
        """Create a failed delivery result."""
        return DeliveryResult(
            notification_id=notification.notification_id,
            target=target,
            status=DeliveryStatus.FAILED,
            message=error_message,
            error_code=error_code
        )
