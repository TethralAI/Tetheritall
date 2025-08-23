"""
Event System Models
Defines data structures for event publishing and subscription.
"""

from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
import json
import uuid


class EventType(Enum):
    """Event types for device and system events."""
    # Device events
    DEVICE_DISCOVERED = "device_discovered"
    DEVICE_CONNECTED = "device_connected"
    DEVICE_DISCONNECTED = "device_disconnected"
    DEVICE_AUTHENTICATED = "device_authenticated"
    DEVICE_TRUSTED = "device_trusted"
    DEVICE_ERROR = "device_error"
    DEVICE_ONLINE = "device_online"
    DEVICE_OFFLINE = "device_offline"
    
    # Communication events
    MESSAGE_SENT = "message_sent"
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_DELIVERED = "message_delivered"
    MESSAGE_FAILED = "message_failed"
    COMMAND_SENT = "command_sent"
    COMMAND_RESPONSE = "command_response"
    
    # State events
    STATE_CHANGED = "state_changed"
    STATE_TRANSITION = "state_transition"
    CONFIGURATION_UPDATED = "configuration_updated"
    
    # Security events
    AUTHENTICATION_SUCCESS = "authentication_success"
    AUTHENTICATION_FAILED = "authentication_failed"
    TRUST_ESTABLISHED = "trust_established"
    TRUST_REVOKED = "trust_revoked"
    SECURITY_ALERT = "security_alert"
    
    # System events
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    SERVICE_STARTED = "service_started"
    SERVICE_STOPPED = "service_stopped"
    ERROR_OCCURRED = "error_occurred"
    WARNING_GENERATED = "warning_generated"
    
    # Performance events
    PERFORMANCE_METRIC = "performance_metric"
    RESOURCE_USAGE = "resource_usage"
    THROUGHPUT_UPDATE = "throughput_update"
    LATENCY_UPDATE = "latency_update"
    
    # Custom events
    CUSTOM = "custom"


class EventPriority(Enum):
    """Event priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Event:
    """Represents an event in the system."""
    
    # Core event info
    event_id: str
    event_type: EventType
    source: str
    timestamp: datetime
    
    # Event content
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Event properties
    priority: EventPriority = EventPriority.NORMAL
    ttl: Optional[int] = None  # Time to live in seconds
    
    # Delivery properties
    delivered: bool = False
    acknowledged: bool = False
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        """Initialize default values."""
        if not self.event_id:
            self.event_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.utcnow()
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data,
            'metadata': self.metadata,
            'priority': self.priority.value,
            'ttl': self.ttl,
            'delivered': self.delivered,
            'acknowledged': self.acknowledged,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create event from dictionary."""
        # Parse enums
        if 'event_type' in data and isinstance(data['event_type'], str):
            data['event_type'] = EventType(data['event_type'])
        if 'priority' in data and isinstance(data['priority'], int):
            data['priority'] = EventPriority(data['priority'])
            
        # Parse timestamp
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
            
        return cls(**data)
        
    def is_expired(self) -> bool:
        """Check if event has expired."""
        if self.ttl is None:
            return False
        age = (datetime.utcnow() - self.timestamp).total_seconds()
        return age > self.ttl
        
    def can_retry(self) -> bool:
        """Check if event can be retried."""
        return self.retry_count < self.max_retries and not self.delivered
        
    def increment_retry(self):
        """Increment retry count."""
        self.retry_count += 1
        
    def mark_delivered(self):
        """Mark event as delivered."""
        self.delivered = True
        
    def mark_acknowledged(self):
        """Mark event as acknowledged."""
        self.acknowledged = True
        
    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict())
        
    @classmethod
    def from_json(cls, json_str: str) -> 'Event':
        """Create event from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
        
    def get_age(self) -> float:
        """Get event age in seconds."""
        return (datetime.utcnow() - self.timestamp).total_seconds()
        
    def is_urgent(self) -> bool:
        """Check if event is urgent (high or critical priority)."""
        return self.priority in [EventPriority.HIGH, EventPriority.CRITICAL]
        
    def is_critical(self) -> bool:
        """Check if event is critical priority."""
        return self.priority == EventPriority.CRITICAL


@dataclass
class EventFilter:
    """Filter for event subscription."""
    
    event_types: Optional[List[EventType]] = None
    sources: Optional[List[str]] = None
    min_priority: Optional[EventPriority] = None
    max_priority: Optional[EventPriority] = None
    data_filters: Optional[Dict[str, Any]] = None
    
    def matches(self, event: Event) -> bool:
        """Check if event matches this filter."""
        # Check event type
        if self.event_types and event.event_type not in self.event_types:
            return False
            
        # Check source
        if self.sources and event.source not in self.sources:
            return False
            
        # Check priority range
        if self.min_priority and event.priority.value < self.min_priority.value:
            return False
        if self.max_priority and event.priority.value > self.max_priority.value:
            return False
            
        # Check data filters
        if self.data_filters:
            for key, value in self.data_filters.items():
                if key not in event.data or event.data[key] != value:
                    return False
                    
        return True
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert filter to dictionary."""
        return {
            'event_types': [et.value for et in self.event_types] if self.event_types else None,
            'sources': self.sources,
            'min_priority': self.min_priority.value if self.min_priority else None,
            'max_priority': self.max_priority.value if self.max_priority else None,
            'data_filters': self.data_filters
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EventFilter':
        """Create filter from dictionary."""
        # Parse event types
        if 'event_types' in data and data['event_types']:
            data['event_types'] = [EventType(et) for et in data['event_types']]
            
        # Parse priorities
        if 'min_priority' in data and data['min_priority'] is not None:
            data['min_priority'] = EventPriority(data['min_priority'])
        if 'max_priority' in data and data['max_priority'] is not None:
            data['max_priority'] = EventPriority(data['max_priority'])
            
        return cls(**data)


@dataclass
class EventSubscription:
    """Represents an event subscription."""
    
    subscription_id: str
    subscriber_id: str
    filter: EventFilter
    callback: Optional[Any] = None  # Callable or async callable
    created_at: datetime = field(default_factory=datetime.utcnow)
    active: bool = True
    
    def __post_init__(self):
        """Initialize default values."""
        if not self.subscription_id:
            self.subscription_id = str(uuid.uuid4())
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert subscription to dictionary."""
        return {
            'subscription_id': self.subscription_id,
            'subscriber_id': self.subscriber_id,
            'filter': self.filter.to_dict(),
            'created_at': self.created_at.isoformat(),
            'active': self.active
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EventSubscription':
        """Create subscription from dictionary."""
        # Parse filter
        if 'filter' in data:
            data['filter'] = EventFilter.from_dict(data['filter'])
            
        # Parse timestamp
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
            
        return cls(**data)
