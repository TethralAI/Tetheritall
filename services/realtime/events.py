"""
Real-time Event System

Defines event types and data structures for real-time communication.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
from datetime import datetime
import json
import uuid


class EventType(Enum):
    """Real-time event types."""
    DEVICE_STATE_CHANGED = "device_state_changed"
    DEVICE_DISCOVERED = "device_discovered"
    DEVICE_DISCONNECTED = "device_disconnected"
    HUB_STATUS_CHANGED = "hub_status_changed"
    HUB_CONNECTED = "hub_connected"
    HUB_DISCONNECTED = "hub_disconnected"
    SYSTEM_ALERT = "system_alert"
    SECURITY_EVENT = "security_event"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    ML_INFERENCE_COMPLETED = "ml_inference_completed"
    USER_ACTION = "user_action"
    HEARTBEAT = "heartbeat"
    ERROR = "error"


class Priority(Enum):
    """Event priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RealtimeEvent:
    """Real-time event data structure."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.HEARTBEAT
    priority: Priority = Priority.NORMAL
    source: str = "system"
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    device_id: Optional[str] = None
    hub_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for JSON serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "priority": self.priority.value,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "device_id": self.device_id,
            "hub_id": self.hub_id,
            "tags": self.tags,
            "metadata": self.metadata
        }
    
    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RealtimeEvent':
        """Create event from dictionary."""
        timestamp = datetime.fromisoformat(data["timestamp"]) if isinstance(data.get("timestamp"), str) else datetime.utcnow()
        
        return cls(
            event_id=data.get("event_id", str(uuid.uuid4())),
            event_type=EventType(data.get("event_type", EventType.HEARTBEAT.value)),
            priority=Priority(data.get("priority", Priority.NORMAL.value)),
            source=data.get("source", "system"),
            data=data.get("data", {}),
            timestamp=timestamp,
            user_id=data.get("user_id"),
            device_id=data.get("device_id"),
            hub_id=data.get("hub_id"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {})
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'RealtimeEvent':
        """Create event from JSON string."""
        return cls.from_dict(json.loads(json_str))


def create_device_state_event(device_id: str, hub_id: str, state: Dict[str, Any], user_id: Optional[str] = None) -> RealtimeEvent:
    """Create a device state changed event."""
    return RealtimeEvent(
        event_type=EventType.DEVICE_STATE_CHANGED,
        priority=Priority.NORMAL,
        source="device_manager",
        data={
            "device_id": device_id,
            "hub_id": hub_id,
            "new_state": state,
            "changed_fields": list(state.keys())
        },
        user_id=user_id,
        device_id=device_id,
        hub_id=hub_id,
        tags=["device", "state_change"]
    )


def create_hub_status_event(hub_id: str, status: str, previous_status: str) -> RealtimeEvent:
    """Create a hub status changed event."""
    return RealtimeEvent(
        event_type=EventType.HUB_STATUS_CHANGED,
        priority=Priority.HIGH if status == "error" else Priority.NORMAL,
        source="hub_manager",
        data={
            "hub_id": hub_id,
            "new_status": status,
            "previous_status": previous_status
        },
        hub_id=hub_id,
        tags=["hub", "status_change"]
    )


def create_security_event(event_data: Dict[str, Any], priority: Priority = Priority.HIGH) -> RealtimeEvent:
    """Create a security event."""
    return RealtimeEvent(
        event_type=EventType.SECURITY_EVENT,
        priority=priority,
        source="security_guard",
        data=event_data,
        tags=["security", "alert"]
    )


def create_system_alert(message: str, alert_type: str = "info", priority: Priority = Priority.NORMAL) -> RealtimeEvent:
    """Create a system alert event."""
    return RealtimeEvent(
        event_type=EventType.SYSTEM_ALERT,
        priority=priority,
        source="system",
        data={
            "message": message,
            "alert_type": alert_type
        },
        tags=["system", "alert"]
    )
