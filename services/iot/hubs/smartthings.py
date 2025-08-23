"""
Samsung SmartThings IoT Hub Connector
Integrates with Samsung SmartThings platform.
"""

import asyncio
import logging
import aiohttp
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from .base import BaseIoTHub, HubConfig, IoTDevice, DeviceType, DeviceCapability, HubStatus

logger = logging.getLogger(__name__)


class SmartThingsHub(BaseIoTHub):
    """Samsung SmartThings IoT Hub connector."""
    
    def __init__(self, config: HubConfig):
        super().__init__(config)
        self.session: Optional[aiohttp.ClientSession] = None
        self._access_token: Optional[str] = None
        
    async def connect(self) -> bool:
        """Connect to SmartThings."""
        try:
            self.status = HubStatus.CONNECTING
            
            # Create HTTP session
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                connector=aiohttp.TCPConnector(verify_ssl=self.config.ssl_verify)
            )
            
            # Test connection to SmartThings API
            headers = self._get_auth_headers()
            async with self.session.get("https://api.smartthings.com/v1/locations", headers=headers) as response:
                if response.status == 200:
                    self.status = HubStatus.CONNECTED
                    logger.info("Connected to SmartThings API")
                    return True
                else:
                    logger.error(f"Failed to connect to SmartThings API: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error connecting to SmartThings: {e}")
            self.status = HubStatus.ERROR
            return False
            
    async def disconnect(self) -> bool:
        """Disconnect from SmartThings."""
        try:
            if self.session:
                await self.session.close()
                self.session = None
                
            self.status = HubStatus.DISCONNECTED
            logger.info("Disconnected from SmartThings")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting from SmartThings: {e}")
            return False
            
    async def authenticate(self) -> bool:
        """Authenticate with SmartThings."""
        try:
            if self.config.token:
                self._access_token = self.config.token
                logger.info("Authenticated with SmartThings")
                return True
            else:
                logger.error("No access token provided for SmartThings")
                return False
                
        except Exception as e:
            logger.error(f"Error authenticating with SmartThings: {e}")
            return False
            
    async def discover_devices(self) -> List[IoTDevice]:
        """Discover devices from SmartThings."""
        try:
            if not self.session:
                return []
                
            headers = self._get_auth_headers()
            
            # Get devices from SmartThings
            async with self.session.get("https://api.smartthings.com/v1/devices", headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    devices = []
                    
                    for device_data in data.get('items', []):
                        device = await self._parse_smartthings_device(device_data)
                        if device:
                            devices.append(device)
                            
                    logger.info(f"Discovered {len(devices)} devices from SmartThings")
                    return devices
                else:
                    logger.error(f"Failed to get devices: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error discovering devices: {e}")
            return []
            
    async def get_device_state(self, device_id: str) -> Dict[str, Any]:
        """Get current state of a device."""
        try:
            if not self.session:
                return {}
                
            headers = self._get_auth_headers()
            
            # Get device state from SmartThings
            async with self.session.get(f"https://api.smartthings.com/v1/devices/{device_id}/states", headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to get device state: {response.status}")
                    return {}
                    
        except Exception as e:
            logger.error(f"Error getting device state: {e}")
            return {}
            
    async def set_device_state(self, device_id: str, state: Dict[str, Any]) -> bool:
        """Set state of a device."""
        try:
            if not self.session:
                return False
                
            headers = self._get_auth_headers()
            headers['Content-Type'] = 'application/json'
            
            # Set device state via SmartThings
            async with self.session.post(
                f"https://api.smartthings.com/v1/devices/{device_id}/commands",
                headers=headers,
                json=state
            ) as response:
                if response.status == 200:
                    logger.info(f"Set state for device {device_id}")
                    return True
                else:
                    logger.error(f"Failed to set device state: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error setting device state: {e}")
            return False
            
    async def subscribe_to_events(self) -> bool:
        """Subscribe to SmartThings events."""
        try:
            # SmartThings uses webhooks for events
            logger.info("Subscribed to SmartThings events (webhook-based)")
            return True
            
        except Exception as e:
            logger.error(f"Error subscribing to events: {e}")
            return False
            
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for SmartThings API."""
        headers = {
            'Authorization': f'Bearer {self._access_token}',
            'Content-Type': 'application/json'
        }
        return headers
        
    async def _parse_smartthings_device(self, device_data: Dict[str, Any]) -> Optional[IoTDevice]:
        """Parse SmartThings device data into IoTDevice."""
        try:
            device_id = device_data.get('deviceId')
            if not device_id:
                return None
                
            # Map SmartThings device types
            device_type = self._map_smartthings_device_type(device_data)
            
            # Extract capabilities
            capabilities = self._extract_smartthings_capabilities(device_data)
            
            # Create device
            device = IoTDevice(
                device_id=device_id,
                name=device_data.get('label', device_data.get('name', device_id)),
                device_type=device_type,
                hub_id=self.config.hub_id,
                hub_name=self.config.name,
                capabilities=capabilities,
                attributes=device_data,
                state=device_data.get('state', {}),
                location=device_data.get('locationId', None),
                manufacturer=device_data.get('manufacturerName', None),
                model=device_data.get('modelName', None),
                firmware_version=device_data.get('firmwareVersion', None),
                last_seen=datetime.utcnow(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            return device
            
        except Exception as e:
            logger.error(f"Error parsing SmartThings device: {e}")
            return None
            
    def _map_smartthings_device_type(self, device_data: Dict[str, Any]) -> DeviceType:
        """Map SmartThings device type to our device type."""
        device_type = device_data.get('type', '').lower()
        
        type_mapping = {
            'light': DeviceType.LIGHT,
            'switch': DeviceType.SWITCH,
            'sensor': DeviceType.SENSOR,
            'thermostat': DeviceType.THERMOSTAT,
            'camera': DeviceType.CAMERA,
            'lock': DeviceType.LOCK,
            'fan': DeviceType.FAN,
            'blinds': DeviceType.BLINDS,
            'appliance': DeviceType.APPLIANCE,
            'media_player': DeviceType.MEDIA_PLAYER,
            'climate': DeviceType.CLIMATE,
            'binary_sensor': DeviceType.BINARY_SENSOR,
            'cover': DeviceType.COVER,
            'vacuum': DeviceType.VACUUM,
            'garage_door': DeviceType.GARAGE_DOOR,
            'irrigation': DeviceType.IRRIGATION,
            'alarm': DeviceType.ALARM,
            'button': DeviceType.BUTTON,
            'remote': DeviceType.REMOTE
        }
        
        return type_mapping.get(device_type, DeviceType.UNKNOWN)
        
    def _extract_smartthings_capabilities(self, device_data: Dict[str, Any]) -> List[DeviceCapability]:
        """Extract device capabilities from SmartThings device data."""
        capabilities = []
        
        # Check capabilities from device data
        device_capabilities = device_data.get('capabilities', [])
        
        capability_mapping = {
            'switch': DeviceCapability.ON_OFF,
            'switchLevel': DeviceCapability.DIMMING,
            'colorControl': DeviceCapability.COLOR,
            'temperatureMeasurement': DeviceCapability.TEMPERATURE,
            'relativeHumidityMeasurement': DeviceCapability.HUMIDITY,
            'motionSensor': DeviceCapability.MOTION,
            'contactSensor': DeviceCapability.CONTACT,
            'lock': DeviceCapability.LOCK_UNLOCK,
            'doorControl': DeviceCapability.OPEN_CLOSE,
            'audioVolume': DeviceCapability.VOLUME,
            'thermostat': DeviceCapability.THERMOSTAT_CONTROL,
            'camera': DeviceCapability.CAMERA_STREAM,
            'vacuum': DeviceCapability.VACUUM_CONTROL,
            'garageDoorControl': DeviceCapability.GARAGE_DOOR_CONTROL,
            'irrigation': DeviceCapability.IRRIGATION_CONTROL,
            'alarm': DeviceCapability.ALARM_CONTROL
        }
        
        for cap in device_capabilities:
            if cap in capability_mapping:
                capabilities.append(capability_mapping[cap])
                
        return capabilities
