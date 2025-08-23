"""
Device State Management Models
Defines data structures for device state management.
"""

from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
import json
import uuid


class StateType(Enum):
    """Device state types."""
    # Operational states
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    
    # Connection states
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    
    # Authentication states
    UNAUTHENTICATED = "unauthenticated"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    
    # Trust states
    UNTRUSTED = "untrusted"
    TRUSTING = "trusting"
    TRUSTED = "trusted"
    
    # Functional states
    IDLE = "idle"
    ACTIVE = "active"
    BUSY = "busy"
    SLEEPING = "sleeping"
    
    # Configuration states
    CONFIGURING = "configuring"
    CONFIGURED = "configured"
    UPDATING = "updating"


@dataclass
class StateChange:
    """Represents a state change event."""
    
    change_id: str
    device_id: str
    old_state: StateType
    new_state: StateType
    timestamp: datetime
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize default values."""
        if not self.change_id:
            self.change_id = str(uuid.uuid4())
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert state change to dictionary."""
        return {
            'change_id': self.change_id,
            'device_id': self.device_id,
            'old_state': self.old_state.value,
            'new_state': self.new_state.value,
            'timestamp': self.timestamp.isoformat(),
            'reason': self.reason,
            'metadata': self.metadata
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StateChange':
        """Create state change from dictionary."""
        # Parse enums
        if 'old_state' in data and isinstance(data['old_state'], str):
            data['old_state'] = StateType(data['old_state'])
        if 'new_state' in data and isinstance(data['new_state'], str):
            data['new_state'] = StateType(data['new_state'])
            
        # Parse timestamp
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
            
        return cls(**data)


@dataclass
class DeviceState:
    """Represents the current state of a device."""
    
    device_id: str
    current_state: StateType
    last_updated: datetime
    state_history: List[StateChange] = field(default_factory=list)
    configuration: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize default values."""
        if not self.last_updated:
            self.last_updated = datetime.utcnow()
            
    def update_state(self, new_state: StateType, reason: Optional[str] = None, metadata: Dict[str, Any] = None) -> StateChange:
        """Update device state and create state change record."""
        old_state = self.current_state
        self.current_state = new_state
        self.last_updated = datetime.utcnow()
        
        # Create state change record
        state_change = StateChange(
            change_id=str(uuid.uuid4()),
            device_id=self.device_id,
            old_state=old_state,
            new_state=new_state,
            timestamp=self.last_updated,
            reason=reason,
            metadata=metadata or {}
        )
        
        # Add to history
        self.state_history.append(state_change)
        
        # Keep only last 100 state changes
        if len(self.state_history) > 100:
            self.state_history = self.state_history[-100:]
            
        return state_change
        
    def get_state_duration(self) -> float:
        """Get duration of current state in seconds."""
        return (datetime.utcnow() - self.last_updated).total_seconds()
        
    def is_online(self) -> bool:
        """Check if device is online."""
        return self.current_state in [StateType.ONLINE, StateType.CONNECTED, StateType.AUTHENTICATED, StateType.TRUSTED, StateType.ACTIVE]
        
    def is_connected(self) -> bool:
        """Check if device is connected."""
        return self.current_state in [StateType.CONNECTED, StateType.AUTHENTICATED, StateType.TRUSTED]
        
    def is_authenticated(self) -> bool:
        """Check if device is authenticated."""
        return self.current_state in [StateType.AUTHENTICATED, StateType.TRUSTED]
        
    def is_trusted(self) -> bool:
        """Check if device is trusted."""
        return self.current_state == StateType.TRUSTED
        
    def is_error(self) -> bool:
        """Check if device is in error state."""
        return self.current_state == StateType.ERROR
        
    def get_recent_changes(self, limit: int = 10) -> List[StateChange]:
        """Get recent state changes."""
        return self.state_history[-limit:] if self.state_history else []
        
    def get_state_transitions(self, from_state: StateType, to_state: StateType) -> List[StateChange]:
        """Get state changes from one state to another."""
        return [
            change for change in self.state_history
            if change.old_state == from_state and change.new_state == to_state
        ]
        
    def get_state_frequency(self) -> Dict[StateType, int]:
        """Get frequency of each state in history."""
        frequency = {}
        for change in self.state_history:
            state = change.new_state
            frequency[state] = frequency.get(state, 0) + 1
        return frequency
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert device state to dictionary."""
        return {
            'device_id': self.device_id,
            'current_state': self.current_state.value,
            'last_updated': self.last_updated.isoformat(),
            'state_history': [change.to_dict() for change in self.state_history],
            'configuration': self.configuration,
            'metadata': self.metadata
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeviceState':
        """Create device state from dictionary."""
        # Parse current state enum
        if 'current_state' in data and isinstance(data['current_state'], str):
            data['current_state'] = StateType(data['current_state'])
            
        # Parse timestamp
        if 'last_updated' in data and isinstance(data['last_updated'], str):
            data['last_updated'] = datetime.fromisoformat(data['last_updated'])
            
        # Parse state history
        if 'state_history' in data and isinstance(data['state_history'], list):
            data['state_history'] = [StateChange.from_dict(change) for change in data['state_history']]
            
        return cls(**data)
        
    def update_configuration(self, config: Dict[str, Any]):
        """Update device configuration."""
        self.configuration.update(config)
        self.last_updated = datetime.utcnow()
        
    def get_configuration(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.configuration.get(key, default)
        
    def set_configuration(self, key: str, value: Any):
        """Set configuration value."""
        self.configuration[key] = value
        self.last_updated = datetime.utcnow()
        
    def remove_configuration(self, key: str):
        """Remove configuration value."""
        if key in self.configuration:
            del self.configuration[key]
            self.last_updated = datetime.utcnow()
            
    def update_metadata(self, metadata: Dict[str, Any]):
        """Update device metadata."""
        self.metadata.update(metadata)
        self.last_updated = datetime.utcnow()
        
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value."""
        return self.metadata.get(key, default)
        
    def set_metadata(self, key: str, value: Any):
        """Set metadata value."""
        self.metadata[key] = value
        self.last_updated = datetime.utcnow()
        
    def remove_metadata(self, key: str):
        """Remove metadata value."""
        if key in self.metadata:
            del self.metadata[key]
            self.last_updated = datetime.utcnow()
