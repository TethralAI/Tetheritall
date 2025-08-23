"""
Device Registry Models
Defines data structures for device registration and management.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
import uuid


class DeviceStatus(Enum):
    """Device status enumeration."""
    UNREGISTERED = "unregistered"
    REGISTERED = "registered"
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    DISCOVERED = "discovered"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    TRUSTED = "trusted"
    FAILED = "failed"


class DeviceCapability(Enum):
    """Device capability enumeration."""
    # Communication capabilities
    WIFI = "wifi"
    BLUETOOTH = "bluetooth"
    ZIGBEE = "zigbee"
    ZWAVE = "zwave"
    MATTER = "matter"
    API = "api"
    
    # Functional capabilities
    LIGHTING = "lighting"
    TEMPERATURE_CONTROL = "temperature_control"
    SECURITY = "security"
    AUDIO = "audio"
    VIDEO = "video"
    SENSING = "sensing"
    ACTUATION = "actuation"
    ENERGY_MONITORING = "energy_monitoring"
    HEALTH_MONITORING = "health_monitoring"
    ACCESS_CONTROL = "access_control"
    PROTOCOL_BRIDGE = "protocol_bridge"
    
    # Network capabilities
    NETWORK = "network"
    ROUTING = "routing"
    GATEWAY = "gateway"
    HUB = "hub"


@dataclass
class DeviceRecord:
    """Represents a device record in the registry."""
    
    # Core identification
    device_id: str
    name: str
    model: str
    manufacturer: str
    
    # Protocol and connection info
    protocol: str
    endpoints: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    
    # Status and lifecycle
    status: DeviceStatus = DeviceStatus.UNREGISTERED
    trust_level: float = 0.0
    last_seen: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    
    # Metadata
    firmware_version: Optional[str] = None
    hardware_version: Optional[str] = None
    serial_number: Optional[str] = None
    mac_address: Optional[str] = None
    ip_address: Optional[str] = None
    
    # Registration info
    registered_at: Optional[datetime] = None
    registered_by: Optional[str] = None
    
    # Configuration
    configuration: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Performance metrics
    uptime: float = 0.0
    response_time: float = 0.0
    error_count: int = 0
    
    def __post_init__(self):
        """Initialize default values after object creation."""
        if not self.registered_at:
            self.registered_at = datetime.utcnow()
        if not self.last_seen:
            self.last_seen = datetime.utcnow()
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert device record to dictionary."""
        return {
            'device_id': self.device_id,
            'name': self.name,
            'model': self.model,
            'manufacturer': self.manufacturer,
            'protocol': self.protocol,
            'endpoints': self.endpoints,
            'capabilities': self.capabilities,
            'status': self.status.value,
            'trust_level': self.trust_level,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'firmware_version': self.firmware_version,
            'hardware_version': self.hardware_version,
            'serial_number': self.serial_number,
            'mac_address': self.mac_address,
            'ip_address': self.ip_address,
            'registered_at': self.registered_at.isoformat() if self.registered_at else None,
            'registered_by': self.registered_by,
            'configuration': self.configuration,
            'metadata': self.metadata,
            'uptime': self.uptime,
            'response_time': self.response_time,
            'error_count': self.error_count
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeviceRecord':
        """Create device record from dictionary."""
        # Parse datetime fields
        for field in ['last_seen', 'last_heartbeat', 'registered_at']:
            if data.get(field) and isinstance(data[field], str):
                data[field] = datetime.fromisoformat(data[field])
                
        # Parse status enum
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = DeviceStatus(data['status'])
            
        return cls(**data)
        
    def update_heartbeat(self):
        """Update device heartbeat timestamp."""
        self.last_heartbeat = datetime.utcnow()
        self.last_seen = datetime.utcnow()
        
    def update_status(self, status: DeviceStatus):
        """Update device status."""
        self.status = status
        self.last_seen = datetime.utcnow()
        
    def add_capability(self, capability: str):
        """Add a capability to the device."""
        if capability not in self.capabilities:
            self.capabilities.append(capability)
            
    def remove_capability(self, capability: str):
        """Remove a capability from the device."""
        if capability in self.capabilities:
            self.capabilities.remove(capability)
            
    def add_endpoint(self, endpoint: str):
        """Add an endpoint to the device."""
        if endpoint not in self.endpoints:
            self.endpoints.append(endpoint)
            
    def remove_endpoint(self, endpoint: str):
        """Remove an endpoint from the device."""
        if endpoint in self.endpoints:
            self.endpoints.remove(endpoint)
            
    def is_online(self) -> bool:
        """Check if device is online."""
        return self.status in [DeviceStatus.ONLINE, DeviceStatus.CONNECTED, DeviceStatus.AUTHENTICATED, DeviceStatus.TRUSTED]
        
    def is_trusted(self) -> bool:
        """Check if device is trusted."""
        return self.trust_level >= 0.7
        
    def get_age(self) -> float:
        """Get device age in seconds."""
        if self.registered_at:
            return (datetime.utcnow() - self.registered_at).total_seconds()
        return 0.0
        
    def get_uptime_percentage(self) -> float:
        """Get device uptime percentage."""
        if self.uptime > 0:
            age = self.get_age()
            if age > 0:
                return min(100.0, (self.uptime / age) * 100)
        return 0.0
