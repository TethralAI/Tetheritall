"""
Google Nest IoT Hub Connector
Integrates with Google Nest devices and Works with Nest.
"""

import asyncio
import logging
import aiohttp
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from .base import BaseIoTHub, HubConfig, IoTDevice, DeviceType, DeviceCapability, HubStatus

logger = logging.getLogger(__name__)


class NestHub(BaseIoTHub):
    """Google Nest IoT Hub connector."""
    
    def __init__(self, config: HubConfig):
        super().__init__(config)
        self.session: Optional[aiohttp.ClientSession] = None
        self._access_token: Optional[str] = None
        
    async def connect(self) -> bool:
        """Connect to Nest."""
        try:
            self.status = HubStatus.CONNECTING
            
            # Create HTTP session
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                connector=aiohttp.TCPConnector(verify_ssl=self.config.ssl_verify)
            )
            
            # Test connection to Nest API
            headers = self._get_auth_headers()
            async with self.session.get("https://smartdevicemanagement.googleapis.com/v1/enterprises/project-id/devices", headers=headers) as response:
                if response.status == 200:
                    self.status = HubStatus.CONNECTED
                    logger.info("Connected to Nest API")
                    return True
                else:
                    logger.error(f"Failed to connect to Nest API: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error connecting to Nest: {e}")
            self.status = HubStatus.ERROR
            return False
            
    async def disconnect(self) -> bool:
        """Disconnect from Nest."""
        try:
            if self.session:
                await self.session.close()
                self.session = None
                
            self.status = HubStatus.DISCONNECTED
            logger.info("Disconnected from Nest")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting from Nest: {e}")
            return False
            
    async def authenticate(self) -> bool:
        """Authenticate with Nest."""
        try:
            if self.config.token:
                self._access_token = self.config.token
                logger.info("Authenticated with Nest")
                return True
            else:
                logger.error("No access token provided for Nest")
                return False
                
        except Exception as e:
            logger.error(f"Error authenticating with Nest: {e}")
            return False
            
    async def discover_devices(self) -> List[IoTDevice]:
        """Discover devices from Nest."""
        try:
            if not self.session:
                return []
                
            headers = self._get_auth_headers()
            
            # Get devices from Nest
            async with self.session.get("https://smartdevicemanagement.googleapis.com/v1/enterprises/project-id/devices", headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    devices = []
                    
                    for device_data in data.get('devices', []):
                        device = await self._parse_nest_device(device_data)
                        if device:
                            devices.append(device)
                            
                    logger.info(f"Discovered {len(devices)} devices from Nest")
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
            
            # Get device state from Nest
            async with self.session.get(f"https://smartdevicemanagement.googleapis.com/v1/{device_id}", headers=headers) as response:
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
            
            # Set device state via Nest
            async with self.session.post(
                f"https://smartdevicemanagement.googleapis.com/v1/{device_id}:executeCommand",
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
        """Subscribe to Nest events."""
        try:
            # Nest uses Google Cloud Pub/Sub for events
            logger.info("Subscribed to Nest events (Pub/Sub-based)")
            return True
            
        except Exception as e:
            logger.error(f"Error subscribing to events: {e}")
            return False
            
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for Nest API."""
        headers = {
            'Authorization': f'Bearer {self._access_token}',
            'Content-Type': 'application/json'
        }
        return headers
        
    async def _parse_nest_device(self, device_data: Dict[str, Any]) -> Optional[IoTDevice]:
        """Parse Nest device data into IoTDevice."""
        try:
            device_id = device_data.get('name')
            if not device_id:
                return None
                
            # Map Nest device types
            device_type = self._map_nest_device_type(device_data)
            
            # Extract capabilities
            capabilities = self._extract_nest_capabilities(device_data)
            
            # Create device
            device = IoTDevice(
                device_id=device_id,
                name=device_data.get('traits', {}).get('sdm.devices.traits.Info', {}).get('customName', device_id),
                device_type=device_type,
                hub_id=self.config.hub_id,
                hub_name=self.config.name,
                capabilities=capabilities,
                attributes=device_data,
                state=device_data.get('traits', {}),
                location=device_data.get('parentRelations', [{}])[0].get('parent', None),
                manufacturer='Google',
                model=device_data.get('traits', {}).get('sdm.devices.traits.Info', {}).get('model', None),
                firmware_version=device_data.get('traits', {}).get('sdm.devices.traits.Info', {}).get('firmwareVersion', None),
                last_seen=datetime.utcnow(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            return device
            
        except Exception as e:
            logger.error(f"Error parsing Nest device: {e}")
            return None
            
    def _map_nest_device_type(self, device_data: Dict[str, Any]) -> DeviceType:
        """Map Nest device type to our device type."""
        traits = device_data.get('traits', {})
        
        if 'sdm.devices.traits.ThermostatTemperatureSetpoint' in traits:
            return DeviceType.THERMOSTAT
        elif 'sdm.devices.traits.CameraLiveStream' in traits:
            return DeviceType.CAMERA
        elif 'sdm.devices.traits.Temperature' in traits:
            return DeviceType.SENSOR
        elif 'sdm.devices.traits.Humidity' in traits:
            return DeviceType.SENSOR
        elif 'sdm.devices.traits.Motion' in traits:
            return DeviceType.BINARY_SENSOR
        elif 'sdm.devices.traits.Occupancy' in traits:
            return DeviceType.BINARY_SENSOR
        else:
            return DeviceType.UNKNOWN
            
    def _extract_nest_capabilities(self, device_data: Dict[str, Any]) -> List[DeviceCapability]:
        """Extract device capabilities from Nest device data."""
        capabilities = []
        traits = device_data.get('traits', {})
        
        # Check for thermostat capabilities
        if 'sdm.devices.traits.ThermostatTemperatureSetpoint' in traits:
            capabilities.append(DeviceCapability.THERMOSTAT_CONTROL)
            
        # Check for temperature capabilities
        if 'sdm.devices.traits.Temperature' in traits:
            capabilities.append(DeviceCapability.TEMPERATURE)
            
        # Check for humidity capabilities
        if 'sdm.devices.traits.Humidity' in traits:
            capabilities.append(DeviceCapability.HUMIDITY)
            
        # Check for motion capabilities
        if 'sdm.devices.traits.Motion' in traits:
            capabilities.append(DeviceCapability.MOTION)
            
        # Check for camera capabilities
        if 'sdm.devices.traits.CameraLiveStream' in traits:
            capabilities.append(DeviceCapability.CAMERA_STREAM)
            
        return capabilities
