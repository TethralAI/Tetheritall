"""
Cache Data Models

Defines data structures for caching and offline support.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta
import json
import uuid


class CacheType(Enum):
    """Types of cached data."""
    DEVICE_STATE = "device_state"
    HUB_STATUS = "hub_status"
    USER_PREFERENCES = "user_preferences"
    API_RESPONSE = "api_response"
    COMMAND_QUEUE = "command_queue"
    OFFLINE_ACTION = "offline_action"
    SYNC_DATA = "sync_data"
    METADATA = "metadata"


class ExpirationPolicy(Enum):
    """Cache expiration policies."""
    NEVER = "never"
    TTL = "ttl"  # Time to live
    LRU = "lru"  # Least recently used
    LFU = "lfu"  # Least frequently used
    SLIDING = "sliding"  # Sliding expiration


class SyncStatus(Enum):
    """Synchronization status."""
    PENDING = "pending"
    SYNCING = "syncing"
    SYNCED = "synced"
    FAILED = "failed"
    CONFLICT = "conflict"


@dataclass
class CacheEntry:
    """Cache entry data structure."""
    key: str
    value: Any
    cache_type: CacheType
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    accessed_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    access_count: int = 0
    priority: int = 0  # Higher priority = kept longer
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def update_access(self):
        """Update access time and count."""
        self.accessed_at = datetime.utcnow()
        self.access_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert cache entry to dictionary."""
        return {
            "key": self.key,
            "value": self.value,
            "cache_type": self.cache_type.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "access_count": self.access_count,
            "priority": self.priority,
            "tags": self.tags,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CacheEntry':
        """Create cache entry from dictionary."""
        return cls(
            key=data["key"],
            value=data["value"],
            cache_type=CacheType(data["cache_type"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            accessed_at=datetime.fromisoformat(data["accessed_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data["expires_at"] else None,
            access_count=data.get("access_count", 0),
            priority=data.get("priority", 0),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {})
        )


@dataclass
class OfflineAction:
    """Offline action data structure."""
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_type: str = "device_control"
    target_id: str = ""  # Device ID, Hub ID, etc.
    command: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    priority: int = 0
    retry_count: int = 0
    max_retries: int = 3
    sync_status: SyncStatus = SyncStatus.PENDING
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert offline action to dictionary."""
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "target_id": self.target_id,
            "command": self.command,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "sync_status": self.sync_status.value,
            "error_message": self.error_message,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OfflineAction':
        """Create offline action from dictionary."""
        return cls(
            action_id=data["action_id"],
            action_type=data["action_type"],
            target_id=data["target_id"],
            command=data["command"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            priority=data.get("priority", 0),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            sync_status=SyncStatus(data.get("sync_status", "pending")),
            error_message=data.get("error_message"),
            metadata=data.get("metadata", {})
        )


@dataclass
class SyncConflict:
    """Synchronization conflict data structure."""
    conflict_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    resource_type: str = ""
    resource_id: str = ""
    local_value: Any = None
    remote_value: Any = None
    local_timestamp: datetime = field(default_factory=datetime.utcnow)
    remote_timestamp: datetime = field(default_factory=datetime.utcnow)
    resolution_strategy: str = "manual"  # manual, local_wins, remote_wins, merge
    resolved: bool = False
    resolved_value: Any = None
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert sync conflict to dictionary."""
        return {
            "conflict_id": self.conflict_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "local_value": self.local_value,
            "remote_value": self.remote_value,
            "local_timestamp": self.local_timestamp.isoformat(),
            "remote_timestamp": self.remote_timestamp.isoformat(),
            "resolution_strategy": self.resolution_strategy,
            "resolved": self.resolved,
            "resolved_value": self.resolved_value,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "metadata": self.metadata
        }


def create_device_state_cache_entry(
    device_id: str,
    state: Dict[str, Any],
    ttl_seconds: int = 300
) -> CacheEntry:
    """Create a device state cache entry."""
    return CacheEntry(
        key=f"device_state:{device_id}",
        value=state,
        cache_type=CacheType.DEVICE_STATE,
        expires_at=datetime.utcnow() + timedelta(seconds=ttl_seconds),
        tags=["device", device_id],
        metadata={"device_id": device_id}
    )


def create_api_response_cache_entry(
    endpoint: str,
    response_data: Any,
    ttl_seconds: int = 60
) -> CacheEntry:
    """Create an API response cache entry."""
    return CacheEntry(
        key=f"api_response:{endpoint}",
        value=response_data,
        cache_type=CacheType.API_RESPONSE,
        expires_at=datetime.utcnow() + timedelta(seconds=ttl_seconds),
        tags=["api", "response"],
        metadata={"endpoint": endpoint}
    )


def create_offline_device_action(
    device_id: str,
    command: Dict[str, Any],
    priority: int = 0
) -> OfflineAction:
    """Create an offline device control action."""
    return OfflineAction(
        action_type="device_control",
        target_id=device_id,
        command=command,
        priority=priority,
        metadata={"device_id": device_id}
    )
