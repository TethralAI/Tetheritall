"""
Base IoT Hub Class
Abstract base class for all IoT hub integrations.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid

logger = logging.getLogger(__name__)


class HubStatus(Enum):
    """IoT Hub connection status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    ERROR = "error"


class DeviceType(Enum):
    """IoT device types."""
    LIGHT = "light"
    SWITCH = "switch"
    SENSOR = "sensor"
    THERMOSTAT = "thermostat"
    CAMERA = "camera"
    LOCK = "lock"
    FAN = "fan"
    BLINDS = "blinds"
    APPLIANCE = "appliance"
    MEDIA_PLAYER = "media_player"
    CLIMATE = "climate"
    BINARY_SENSOR = "binary_sensor"
    COVER = "cover"
    VACUUM = "vacuum"
    GARAGE_DOOR = "garage_door"
    IRRIGATION = "irrigation"
    ALARM = "alarm"
    BUTTON = "button"
    REMOTE = "remote"
    UNKNOWN = "unknown"


class DeviceCapability(Enum):
    """Device capabilities."""
    ON_OFF = "on_off"
    DIMMING = "dimming"
    COLOR = "color"
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    MOTION = "motion"
    CONTACT = "contact"
    SMOKE = "smoke"
    WATER_LEAK = "water_leak"
    LOCK_UNLOCK = "lock_unlock"
    OPEN_CLOSE = "open_close"
    PLAY_PAUSE = "play_pause"
    VOLUME = "volume"
    THERMOSTAT_CONTROL = "thermostat_control"
    CAMERA_STREAM = "camera_stream"
    VACUUM_CONTROL = "vacuum_control"
    GARAGE_DOOR_CONTROL = "garage_door_control"
    IRRIGATION_CONTROL = "irrigation_control"
    ALARM_CONTROL = "alarm_control"


@dataclass
class IoTDevice:
    """IoT device information."""
    device_id: str
    name: str
    device_type: DeviceType
    hub_id: str
    hub_name: str
    capabilities: List[DeviceCapability]
    attributes: Dict[str, Any]
    state: Dict[str, Any]
    location: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    firmware_version: Optional[str] = None
    last_seen: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class HubConfig:
    """IoT Hub configuration."""
    hub_id: str
    hub_type: str
    name: str
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    token: Optional[str] = None
    ssl_verify: bool = True
    timeout: int = 30
    retry_attempts: int = 3
    custom_config: Dict[str, Any] = field(default_factory=dict)


class BaseIoTHub(ABC):
    """Abstract base class for IoT hub integrations."""
    
    def __init__(self, config: HubConfig):
        self.config = config
        self.status = HubStatus.DISCONNECTED
        self.devices: Dict[str, IoTDevice] = {}
        self._callbacks: List[Callable] = []
        self._running = False
        self._connection_task: Optional[asyncio.Task] = None
        self._discovery_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the IoT hub."""
        pass
        
    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from the IoT hub."""
        pass
        
    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the IoT hub."""
        pass
        
    @abstractmethod
    async def discover_devices(self) -> List[IoTDevice]:
        """Discover devices on the hub."""
        pass
        
    @abstractmethod
    async def get_device_state(self, device_id: str) -> Dict[str, Any]:
        """Get current state of a device."""
        pass
        
    @abstractmethod
    async def set_device_state(self, device_id: str, state: Dict[str, Any]) -> bool:
        """Set state of a device."""
        pass
        
    @abstractmethod
    async def subscribe_to_events(self) -> bool:
        """Subscribe to device events."""
        pass
        
    async def start(self):
        """Start the IoT hub connection."""
        self._running = True
        
        # Connect to hub
        if await self.connect():
            # Authenticate
            if await self.authenticate():
                self.status = HubStatus.AUTHENTICATED
                
                # Start background tasks
                self._discovery_task = asyncio.create_task(self._device_discovery_loop())
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                
                # Subscribe to events
                await self.subscribe_to_events()
                
                logger.info(f"Started IoT Hub: {self.config.name}")
            else:
                self.status = HubStatus.ERROR
                logger.error(f"Failed to authenticate with hub: {self.config.name}")
        else:
            self.status = HubStatus.ERROR
            logger.error(f"Failed to connect to hub: {self.config.name}")
            
    async def stop(self):
        """Stop the IoT hub connection."""
        self._running = False
        
        # Cancel background tasks
        if self._connection_task:
            self._connection_task.cancel()
        if self._discovery_task:
            self._discovery_task.cancel()
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            
        # Disconnect
        await self.disconnect()
        
        logger.info(f"Stopped IoT Hub: {self.config.name}")
        
    def add_callback(self, callback: Callable):
        """Add event callback."""
        self._callbacks.append(callback)
        
    async def _notify_callbacks(self, event_type: str, data: Any):
        """Notify all callbacks of an event."""
        for callback in self._callbacks:
            try:
                await callback(event_type, data)
            except Exception as e:
                logger.error(f"Error in callback: {e}")
                
    async def _device_discovery_loop(self):
        """Background task for device discovery."""
        while self._running:
            try:
                devices = await self.discover_devices()
                for device in devices:
                    if device.device_id not in self.devices:
                        self.devices[device.device_id] = device
                        await self._notify_callbacks('device_discovered', device)
                    else:
                        # Update existing device
                        old_device = self.devices[device.device_id]
                        self.devices[device.device_id] = device
                        if old_device.state != device.state:
                            await self._notify_callbacks('device_state_changed', device)
                            
            except Exception as e:
                logger.error(f"Error in device discovery loop: {e}")
                
            await asyncio.sleep(60)  # Discover every minute
            
    async def _heartbeat_loop(self):
        """Background task for connection heartbeat."""
        while self._running:
            try:
                # Simple ping to keep connection alive
                if self.status == HubStatus.AUTHENTICATED:
                    # Hub-specific heartbeat logic can be implemented in subclasses
                    pass
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                self.status = HubStatus.ERROR
                
            await asyncio.sleep(30)  # Heartbeat every 30 seconds
            
    def get_devices(self) -> List[IoTDevice]:
        """Get all discovered devices."""
        return list(self.devices.values())
        
    def get_device(self, device_id: str) -> Optional[IoTDevice]:
        """Get a specific device."""
        return self.devices.get(device_id)
        
    def is_connected(self) -> bool:
        """Check if hub is connected."""
        return self.status in [HubStatus.CONNECTED, HubStatus.AUTHENTICATED]
        
    def get_status(self) -> Dict[str, Any]:
        """Get hub status information."""
        return {
            'hub_id': self.config.hub_id,
            'hub_type': self.config.hub_type,
            'name': self.config.name,
            'status': self.status.value,
            'device_count': len(self.devices),
            'connected': self.is_connected(),
            'running': self._running
        }
    
    async def get_recent_events(self) -> List[Dict[str, Any]]:
        """Get recent events from the hub."""
        # Default implementation - subclasses can override
        return []
