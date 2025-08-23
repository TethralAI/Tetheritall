"""
Notification Data Models

Defines data structures for notifications, delivery status, and configurations.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid


class NotificationType(Enum):
    """Types of notifications."""
    DEVICE_STATE_CHANGE = "device_state_change"
    DEVICE_OFFLINE = "device_offline"
    DEVICE_ONLINE = "device_online"
    HUB_DISCONNECTED = "hub_disconnected"
    HUB_CONNECTED = "hub_connected"
    SECURITY_ALERT = "security_alert"
    SYSTEM_ALERT = "system_alert"
    WORKFLOW_COMPLETE = "workflow_complete"
    WORKFLOW_FAILED = "workflow_failed"
    ML_INFERENCE_COMPLETE = "ml_inference_complete"
    ENERGY_ALERT = "energy_alert"
    MAINTENANCE_REMINDER = "maintenance_reminder"
    CUSTOM = "custom"


class Priority(Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class DeliveryStatus(Enum):
    """Notification delivery status."""
    PENDING = "pending"
    SENDING = "sending"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Platform(Enum):
    """Notification platforms."""
    FCM = "fcm"  # Firebase Cloud Messaging
    APNS = "apns"  # Apple Push Notification Service
    WEB_PUSH = "web_push"
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"


@dataclass
class NotificationTarget:
    """Notification delivery target."""
    platform: Platform
    token: str  # Device token, email, phone number, etc.
    user_id: Optional[str] = None
    device_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationContent:
    """Notification content structure."""
    title: str
    body: str
    icon: Optional[str] = None
    image: Optional[str] = None
    sound: Optional[str] = "default"
    badge: Optional[int] = None
    click_action: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    actions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Notification:
    """Notification data structure."""
    notification_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    notification_type: NotificationType = NotificationType.CUSTOM
    priority: Priority = Priority.NORMAL
    content: NotificationContent = None
    targets: List[NotificationTarget] = field(default_factory=list)
    schedule_time: Optional[datetime] = None
    expire_time: Optional[datetime] = None
    user_id: Optional[str] = None
    device_id: Optional[str] = None
    hub_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert notification to dictionary."""
        return {
            "notification_id": self.notification_id,
            "notification_type": self.notification_type.value,
            "priority": self.priority.value,
            "content": {
                "title": self.content.title,
                "body": self.content.body,
                "icon": self.content.icon,
                "image": self.content.image,
                "sound": self.content.sound,
                "badge": self.content.badge,
                "click_action": self.content.click_action,
                "data": self.content.data,
                "actions": self.content.actions
            } if self.content else None,
            "targets": [
                {
                    "platform": target.platform.value,
                    "token": target.token,
                    "user_id": target.user_id,
                    "device_id": target.device_id,
                    "metadata": target.metadata
                } for target in self.targets
            ],
            "schedule_time": self.schedule_time.isoformat() if self.schedule_time else None,
            "expire_time": self.expire_time.isoformat() if self.expire_time else None,
            "user_id": self.user_id,
            "device_id": self.device_id,
            "hub_id": self.hub_id,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class DeliveryResult:
    """Notification delivery result."""
    notification_id: str
    target: NotificationTarget
    status: DeliveryStatus
    message: Optional[str] = None
    error_code: Optional[str] = None
    delivered_at: Optional[datetime] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert delivery result to dictionary."""
        return {
            "notification_id": self.notification_id,
            "target": {
                "platform": self.target.platform.value,
                "token": self.target.token,
                "user_id": self.target.user_id,
                "device_id": self.target.device_id,
                "metadata": self.target.metadata
            },
            "status": self.status.value,
            "message": self.message,
            "error_code": self.error_code,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "retry_count": self.retry_count,
            "metadata": self.metadata
        }


def create_device_state_notification(
    device_id: str,
    device_name: str,
    state_change: str,
    user_id: str,
    priority: Priority = Priority.NORMAL
) -> Notification:
    """Create a device state change notification."""
    content = NotificationContent(
        title=f"Device {device_name}",
        body=f"State changed: {state_change}",
        icon="device_icon",
        data={
            "device_id": device_id,
            "state_change": state_change,
            "action": "device_state_change"
        }
    )
    
    return Notification(
        notification_type=NotificationType.DEVICE_STATE_CHANGE,
        priority=priority,
        content=content,
        user_id=user_id,
        device_id=device_id,
        tags=["device", "state_change"]
    )


def create_security_alert_notification(
    alert_message: str,
    alert_type: str,
    user_id: str,
    priority: Priority = Priority.HIGH
) -> Notification:
    """Create a security alert notification."""
    content = NotificationContent(
        title="Security Alert",
        body=alert_message,
        icon="security_icon",
        sound="alert",
        data={
            "alert_type": alert_type,
            "action": "security_alert"
        },
        actions=[
            {"action": "view", "title": "View Details"},
            {"action": "dismiss", "title": "Dismiss"}
        ]
    )
    
    return Notification(
        notification_type=NotificationType.SECURITY_ALERT,
        priority=priority,
        content=content,
        user_id=user_id,
        tags=["security", "alert"]
    )


def create_hub_status_notification(
    hub_id: str,
    hub_name: str,
    status: str,
    user_id: str,
    priority: Priority = Priority.NORMAL
) -> Notification:
    """Create a hub status change notification."""
    notification_type = (
        NotificationType.HUB_CONNECTED if status == "connected" 
        else NotificationType.HUB_DISCONNECTED
    )
    
    content = NotificationContent(
        title=f"Hub {hub_name}",
        body=f"Status: {status}",
        icon="hub_icon",
        data={
            "hub_id": hub_id,
            "status": status,
            "action": "hub_status_change"
        }
    )
    
    return Notification(
        notification_type=notification_type,
        priority=priority,
        content=content,
        user_id=user_id,
        hub_id=hub_id,
        tags=["hub", "status_change"]
    )
