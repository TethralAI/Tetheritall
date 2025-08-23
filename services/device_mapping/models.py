"""
Device Mapping Data Models

Defines data structures for device mapping, categorization, and user preferences.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List, Set
from datetime import datetime
import json
import uuid


class DeviceCategory(Enum):
    """Device categories for organization."""
    LIGHTING = "lighting"
    CLIMATE = "climate"
    SECURITY = "security"
    ENTERTAINMENT = "entertainment"
    APPLIANCE = "appliance"
    SENSOR = "sensor"
    CAMERA = "camera"
    LOCK = "lock"
    SWITCH = "switch"
    OUTLET = "outlet"
    THERMOSTAT = "thermostat"
    FAN = "fan"
    BLIND = "blind"
    GARAGE_DOOR = "garage_door"
    IRRIGATION = "irrigation"
    OTHER = "other"


class ControlType(Enum):
    """Types of device controls."""
    TOGGLE = "toggle"
    DIMMER = "dimmer"
    COLOR = "color"
    TEMPERATURE = "temperature"
    FAN_SPEED = "fan_speed"
    LOCK_UNLOCK = "lock_unlock"
    OPEN_CLOSE = "open_close"
    VOLUME = "volume"
    CHANNEL = "channel"
    CUSTOM = "custom"


class MappingStatus(Enum):
    """Device mapping status."""
    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    CONFIGURING = "configuring"


@dataclass
class ControlMapping:
    """Mapping for device controls."""
    control_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    control_type: ControlType = ControlType.TOGGLE
    name: str = ""
    description: str = ""
    icon: str = ""
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: Optional[float] = None
    unit: str = ""
    options: List[str] = field(default_factory=list)
    default_value: Any = None
    required: bool = False
    read_only: bool = False
    custom_parameters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "control_id": self.control_id,
            "control_type": self.control_type.value,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "step": self.step,
            "unit": self.unit,
            "options": self.options,
            "default_value": self.default_value,
            "required": self.required,
            "read_only": self.read_only,
            "custom_parameters": self.custom_parameters
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ControlMapping':
        """Create from dictionary."""
        return cls(
            control_id=data.get("control_id", str(uuid.uuid4())),
            control_type=ControlType(data.get("control_type", "toggle")),
            name=data.get("name", ""),
            description=data.get("description", ""),
            icon=data.get("icon", ""),
            min_value=data.get("min_value"),
            max_value=data.get("max_value"),
            step=data.get("step"),
            unit=data.get("unit", ""),
            options=data.get("options", []),
            default_value=data.get("default_value"),
            required=data.get("required", False),
            read_only=data.get("read_only", False),
            custom_parameters=data.get("custom_parameters", {})
        )


@dataclass
class RoomMapping:
    """Room mapping for devices."""
    room_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    floor: str = ""
    area: Optional[float] = None
    icon: str = ""
    color: str = "#007bff"
    coordinates: Optional[Dict[str, float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "room_id": self.room_id,
            "name": self.name,
            "description": self.description,
            "floor": self.floor,
            "area": self.area,
            "icon": self.icon,
            "color": self.color,
            "coordinates": self.coordinates,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RoomMapping':
        """Create from dictionary."""
        return cls(
            room_id=data.get("room_id", str(uuid.uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            floor=data.get("floor", ""),
            area=data.get("area"),
            icon=data.get("icon", ""),
            color=data.get("color", "#007bff"),
            coordinates=data.get("coordinates"),
            metadata=data.get("metadata", {})
        )


@dataclass
class UserPreference:
    """User preferences for device mapping."""
    user_id: str = ""
    device_id: str = ""
    favorite: bool = False
    auto_control: bool = False
    notifications_enabled: bool = True
    voice_control_enabled: bool = True
    custom_name: Optional[str] = None
    custom_icon: Optional[str] = None
    control_order: List[str] = field(default_factory=list)
    automation_rules: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "device_id": self.device_id,
            "favorite": self.favorite,
            "auto_control": self.auto_control,
            "notifications_enabled": self.notifications_enabled,
            "voice_control_enabled": self.voice_control_enabled,
            "custom_name": self.custom_name,
            "custom_icon": self.custom_icon,
            "control_order": self.control_order,
            "automation_rules": self.automation_rules,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserPreference':
        """Create from dictionary."""
        return cls(
            user_id=data.get("user_id", ""),
            device_id=data.get("device_id", ""),
            favorite=data.get("favorite", False),
            auto_control=data.get("auto_control", False),
            notifications_enabled=data.get("notifications_enabled", True),
            voice_control_enabled=data.get("voice_control_enabled", True),
            custom_name=data.get("custom_name"),
            custom_icon=data.get("custom_icon"),
            control_order=data.get("control_order", []),
            automation_rules=data.get("automation_rules", []),
            metadata=data.get("metadata", {})
        )


@dataclass
class DeviceMapping:
    """Complete device mapping for app connection."""
    mapping_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    device_id: str = ""
    hub_id: str = ""
    user_id: str = ""
    name: str = ""
    display_name: str = ""
    category: DeviceCategory = DeviceCategory.OTHER
    room_id: Optional[str] = None
    status: MappingStatus = MappingStatus.PENDING
    controls: List[ControlMapping] = field(default_factory=list)
    user_preferences: UserPreference = field(default_factory=UserPreference)
    voice_aliases: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "mapping_id": self.mapping_id,
            "device_id": self.device_id,
            "hub_id": self.hub_id,
            "user_id": self.user_id,
            "name": self.name,
            "display_name": self.display_name,
            "category": self.category.value,
            "room_id": self.room_id,
            "status": self.status.value,
            "controls": [control.to_dict() for control in self.controls],
            "user_preferences": self.user_preferences.to_dict(),
            "voice_aliases": self.voice_aliases,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeviceMapping':
        """Create from dictionary."""
        created_at = datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else datetime.utcnow()
        updated_at = datetime.fromisoformat(data["updated_at"]) if isinstance(data.get("updated_at"), str) else datetime.utcnow()
        last_used = datetime.fromisoformat(data["last_used"]) if isinstance(data.get("last_used"), str) else None
        
        return cls(
            mapping_id=data.get("mapping_id", str(uuid.uuid4())),
            device_id=data.get("device_id", ""),
            hub_id=data.get("hub_id", ""),
            user_id=data.get("user_id", ""),
            name=data.get("name", ""),
            display_name=data.get("display_name", ""),
            category=DeviceCategory(data.get("category", "other")),
            room_id=data.get("room_id"),
            status=MappingStatus(data.get("status", "pending")),
            controls=[ControlMapping.from_dict(c) for c in data.get("controls", [])],
            user_preferences=UserPreference.from_dict(data.get("user_preferences", {})),
            voice_aliases=data.get("voice_aliases", []),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            created_at=created_at,
            updated_at=updated_at,
            last_used=last_used
        )


def create_light_mapping(device_id: str, hub_id: str, user_id: str, name: str, room_id: Optional[str] = None) -> DeviceMapping:
    """Create a light device mapping with standard controls."""
    controls = [
        ControlMapping(
            control_type=ControlType.TOGGLE,
            name="Power",
            description="Turn the light on or off",
            icon="lightbulb",
            default_value=False
        ),
        ControlMapping(
            control_type=ControlType.DIMMER,
            name="Brightness",
            description="Adjust light brightness",
            icon="brightness-6",
            min_value=0,
            max_value=100,
            step=1,
            unit="%",
            default_value=100
        ),
        ControlMapping(
            control_type=ControlType.COLOR,
            name="Color",
            description="Change light color",
            icon="palette",
            default_value="#ffffff"
        )
    ]
    
    return DeviceMapping(
        device_id=device_id,
        hub_id=hub_id,
        user_id=user_id,
        name=name,
        display_name=name,
        category=DeviceCategory.LIGHTING,
        room_id=room_id,
        status=MappingStatus.ACTIVE,
        controls=controls,
        voice_aliases=[name.lower(), f"the {name.lower()}", f"{name.lower()} light"],
        tags=["lighting", "smart"]
    )


def create_thermostat_mapping(device_id: str, hub_id: str, user_id: str, name: str, room_id: Optional[str] = None) -> DeviceMapping:
    """Create a thermostat device mapping with standard controls."""
    controls = [
        ControlMapping(
            control_type=ControlType.TEMPERATURE,
            name="Temperature",
            description="Set target temperature",
            icon="thermostat",
            min_value=10,
            max_value=35,
            step=0.5,
            unit="°C",
            default_value=22
        ),
        ControlMapping(
            control_type=ControlType.TOGGLE,
            name="Power",
            description="Turn the thermostat on or off",
            icon="power",
            default_value=True
        ),
        ControlMapping(
            control_type=ControlType.CUSTOM,
            name="Mode",
            description="Set heating/cooling mode",
            icon="mode",
            options=["heat", "cool", "auto", "off"],
            default_value="auto"
        )
    ]
    
    return DeviceMapping(
        device_id=device_id,
        hub_id=hub_id,
        user_id=user_id,
        name=name,
        display_name=name,
        category=DeviceCategory.THERMOSTAT,
        room_id=room_id,
        status=MappingStatus.ACTIVE,
        controls=controls,
        voice_aliases=[name.lower(), f"the {name.lower()}", f"{name.lower()} thermostat"],
        tags=["climate", "thermostat", "smart"]
    )


def create_switch_mapping(device_id: str, hub_id: str, user_id: str, name: str, room_id: Optional[str] = None) -> DeviceMapping:
    """Create a switch device mapping with standard controls."""
    controls = [
        ControlMapping(
            control_type=ControlType.TOGGLE,
            name="Power",
            description="Turn the switch on or off",
            icon="power",
            default_value=False
        )
    ]
    
    return DeviceMapping(
        device_id=device_id,
        hub_id=hub_id,
        user_id=user_id,
        name=name,
        display_name=name,
        category=DeviceCategory.SWITCH,
        room_id=room_id,
        status=MappingStatus.ACTIVE,
        controls=controls,
        voice_aliases=[name.lower(), f"the {name.lower()}", f"{name.lower()} switch"],
        tags=["switch", "smart"]
    )
