"""
Communication Protocols
Defines base communication protocols and message types.
"""

from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
import json
import uuid


class CommunicationProtocol(Enum):
    """Supported communication protocols."""
    HTTP = "http"
    HTTPS = "https"
    MQTT = "mqtt"
    COAP = "coap"
    WEBSOCKET = "websocket"
    BLUETOOTH = "bluetooth"
    ZIGBEE = "zigbee"
    ZWAVE = "zwave"
    MATTER = "matter"
    CUSTOM = "custom"


class MessageType(Enum):
    """Message types for device communication."""
    # Control messages
    COMMAND = "command"
    RESPONSE = "response"
    ACKNOWLEDGMENT = "acknowledgment"
    
    # Data messages
    SENSOR_DATA = "sensor_data"
    STATUS_UPDATE = "status_update"
    CONFIGURATION = "configuration"
    
    # System messages
    HEARTBEAT = "heartbeat"
    DISCOVERY = "discovery"
    AUTHENTICATION = "authentication"
    ERROR = "error"
    
    # Event messages
    EVENT = "event"
    ALERT = "alert"
    NOTIFICATION = "notification"


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Message:
    """Represents a communication message."""
    
    # Core message info
    message_id: str
    message_type: MessageType
    protocol: CommunicationProtocol
    
    # Source and destination
    source_id: str
    destination_id: str
    
    # Content
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Message properties
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ttl: Optional[int] = None  # Time to live in seconds
    
    # Delivery properties
    retry_count: int = 0
    max_retries: int = 3
    delivered: bool = False
    acknowledged: bool = False
    
    def __post_init__(self):
        """Initialize default values."""
        if not self.message_id:
            self.message_id = str(uuid.uuid4())
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            'message_id': self.message_id,
            'message_type': self.message_type.value,
            'protocol': self.protocol.value,
            'source_id': self.source_id,
            'destination_id': self.destination_id,
            'payload': self.payload,
            'metadata': self.metadata,
            'priority': self.priority.value,
            'timestamp': self.timestamp.isoformat(),
            'ttl': self.ttl,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'delivered': self.delivered,
            'acknowledged': self.acknowledged
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary."""
        # Parse enums
        if 'message_type' in data and isinstance(data['message_type'], str):
            data['message_type'] = MessageType(data['message_type'])
        if 'protocol' in data and isinstance(data['protocol'], str):
            data['protocol'] = CommunicationProtocol(data['protocol'])
        if 'priority' in data and isinstance(data['priority'], int):
            data['priority'] = MessagePriority(data['priority'])
            
        # Parse timestamp
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
            
        return cls(**data)
        
    def is_expired(self) -> bool:
        """Check if message has expired."""
        if self.ttl is None:
            return False
        age = (datetime.utcnow() - self.timestamp).total_seconds()
        return age > self.ttl
        
    def can_retry(self) -> bool:
        """Check if message can be retried."""
        return self.retry_count < self.max_retries and not self.delivered
        
    def increment_retry(self):
        """Increment retry count."""
        self.retry_count += 1
        
    def mark_delivered(self):
        """Mark message as delivered."""
        self.delivered = True
        
    def mark_acknowledged(self):
        """Mark message as acknowledged."""
        self.acknowledged = True
        
    def to_json(self) -> str:
        """Convert message to JSON string."""
        return json.dumps(self.to_dict())
        
    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        """Create message from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class Command:
    """Represents a device command."""
    
    command_id: str
    device_id: str
    command_type: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    timeout: Optional[int] = None
    priority: MessagePriority = MessagePriority.NORMAL
    
    def __post_init__(self):
        """Initialize default values."""
        if not self.command_id:
            self.command_id = str(uuid.uuid4())
            
    def to_message(self, source_id: str) -> Message:
        """Convert command to message."""
        return Message(
            message_id=self.command_id,
            message_type=MessageType.COMMAND,
            protocol=CommunicationProtocol.HTTP,  # Default protocol
            source_id=source_id,
            destination_id=self.device_id,
            payload={
                'command_type': self.command_type,
                'parameters': self.parameters,
                'timeout': self.timeout
            },
            priority=self.priority
        )
        
    @classmethod
    def from_message(cls, message: Message) -> 'Command':
        """Create command from message."""
        payload = message.payload
        return cls(
            command_id=message.message_id,
            device_id=message.destination_id,
            command_type=payload.get('command_type', ''),
            parameters=payload.get('parameters', {}),
            timeout=payload.get('timeout'),
            priority=message.priority
        )


@dataclass
class Response:
    """Represents a device response."""
    
    response_id: str
    command_id: str
    device_id: str
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Initialize default values."""
        if not self.response_id:
            self.response_id = str(uuid.uuid4())
            
    def to_message(self, source_id: str) -> Message:
        """Convert response to message."""
        return Message(
            message_id=self.response_id,
            message_type=MessageType.RESPONSE,
            protocol=CommunicationProtocol.HTTP,  # Default protocol
            source_id=source_id,
            destination_id=self.device_id,
            payload={
                'command_id': self.command_id,
                'success': self.success,
                'data': self.data,
                'error': self.error
            }
        )
        
    @classmethod
    def from_message(cls, message: Message) -> 'Response':
        """Create response from message."""
        payload = message.payload
        return cls(
            response_id=message.message_id,
            command_id=payload.get('command_id', ''),
            device_id=message.source_id,
            success=payload.get('success', False),
            data=payload.get('data', {}),
            error=payload.get('error')
        )


class ProtocolHandler:
    """Base class for protocol handlers."""
    
    def __init__(self, protocol: CommunicationProtocol):
        self.protocol = protocol
        self.supported_message_types: List[MessageType] = []
        
    async def send_message(self, message: Message) -> bool:
        """Send a message using this protocol."""
        raise NotImplementedError
        
    async def receive_message(self) -> Optional[Message]:
        """Receive a message using this protocol."""
        raise NotImplementedError
        
    async def connect(self, endpoint: str) -> bool:
        """Connect to an endpoint using this protocol."""
        raise NotImplementedError
        
    async def disconnect(self):
        """Disconnect from the endpoint."""
        raise NotImplementedError
        
    def is_connected(self) -> bool:
        """Check if connected."""
        raise NotImplementedError
        
    def supports_message_type(self, message_type: MessageType) -> bool:
        """Check if protocol supports message type."""
        return message_type in self.supported_message_types
