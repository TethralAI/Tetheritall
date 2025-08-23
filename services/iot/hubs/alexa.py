"""
Alexa Echo Dot IoT Hub Connector
Integrates with Amazon Alexa devices and Smart Home Skills.
"""

import asyncio
import logging
import aiohttp
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import websockets

from .base import BaseIoTHub, HubConfig, IoTDevice, DeviceType, DeviceCapability, HubStatus

logger = logging.getLogger(__name__)


class AlexaHub(BaseIoTHub):
    """Alexa Echo Dot IoT Hub connector."""
    
    def __init__(self, config: HubConfig):
        super().__init__(config)
        self.session: Optional[aiohttp.ClientSession] = None
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        
    async def connect(self) -> bool:
        """Connect to Alexa."""
        try:
            self.status = HubStatus.CONNECTING
            
            # Create HTTP session
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                connector=aiohttp.TCPConnector(verify_ssl=self.config.ssl_verify)
            )
            
            # Test connection to Alexa API
            headers = self._get_auth_headers()
            async with self.session.get("https://alexa.amazon.com/api/devices-v2/device", headers=headers) as response:
                if response.status == 200:
                    self.status = HubStatus.CONNECTED
                    logger.info("Connected to Alexa API")
                    return True
                else:
                    logger.error(f"Failed to connect to Alexa API: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error connecting to Alexa: {e}")
            self.status = HubStatus.ERROR
            return False
            
    async def disconnect(self) -> bool:
        """Disconnect from Alexa."""
        try:
            if self.websocket:
                await self.websocket.close()
                self.websocket = None
                
            if self.session:
                await self.session.close()
                self.session = None
                
            self.status = HubStatus.DISCONNECTED
            logger.info("Disconnected from Alexa")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting from Alexa: {e}")
            return False
            
    async def authenticate(self) -> bool:
        """Authenticate with Alexa."""
        try:
            if not self.session:
                return False
                
            # Use provided token or refresh token
            if self.config.token:
                self._access_token = self.config.token
                return True
            elif self.config.custom_config.get('refresh_token'):
                # Refresh the access token
                return await self._refresh_access_token()
            else:
                logger.error("No access token or refresh token provided for Alexa")
                return False
                
        except Exception as e:
            logger.error(f"Error authenticating with Alexa: {e}")
            return False
            
    async def discover_devices(self) -> List[IoTDevice]:
        """Discover devices from Alexa."""
        try:
            if not self.session:
                return []
                
            headers = self._get_auth_headers()
            
            # Get devices from Alexa
            async with self.session.get("https://alexa.amazon.com/api/devices-v2/device", headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    devices = []
                    
                    for device_data in data.get('devices', []):
                        device = await self._parse_alexa_device(device_data)
                        if device:
                            devices.append(device)
                            
                    logger.info(f"Discovered {len(devices)} devices from Alexa")
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
            
            # Get device state from Alexa
            async with self.session.get(f"https://alexa.amazon.com/api/devices-v2/device/{device_id}/state", headers=headers) as response:
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
            
            # Set device state via Alexa
            async with self.session.post(
                f"https://alexa.amazon.com/api/devices-v2/device/{device_id}/state",
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
        """Subscribe to Alexa events."""
        try:
            # Alexa doesn't have a direct WebSocket API, so we'll poll for changes
            logger.info("Alexa events will be polled during device discovery")
            return True
            
        except Exception as e:
            logger.error(f"Error subscribing to events: {e}")
            return False
            
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for Alexa API."""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        if self._access_token:
            headers['Authorization'] = f'Bearer {self._access_token}'
            
        return headers
        
    async def _refresh_access_token(self) -> bool:
        """Refresh the access token using refresh token."""
        try:
            refresh_token = self.config.custom_config.get('refresh_token')
            if not refresh_token:
                return False
                
            data = {
                'client_id': self.config.custom_config.get('client_id'),
                'client_secret': self.config.custom_config.get('client_secret'),
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token
            }
            
            async with self.session.post('https://api.amazon.com/auth/o2/token', data=data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    self._access_token = token_data.get('access_token')
                    self._refresh_token = token_data.get('refresh_token')
                    return True
                else:
                    logger.error(f"Failed to refresh token: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error refreshing access token: {e}")
            return False
            
    async def _parse_alexa_device(self, device_data: Dict[str, Any]) -> Optional[IoTDevice]:
        """Parse Alexa device data into IoTDevice."""
        try:
            device_id = device_data.get('deviceSerialNumber')
            if not device_id:
                return None
                
            # Map Alexa device types to our device types
            device_type = self._map_alexa_device_type(device_data)
            
            # Extract capabilities
            capabilities = self._extract_alexa_capabilities(device_data)
            
            # Create device
            device = IoTDevice(
                device_id=device_id,
                name=device_data.get('accountName', device_data.get('friendlyName', device_id)),
                device_type=device_type,
                hub_id=self.config.hub_id,
                hub_name=self.config.name,
                capabilities=capabilities,
                attributes=device_data,
                state=device_data.get('state', {}),
                location=device_data.get('location', None),
                manufacturer=device_data.get('manufacturer', None),
                model=device_data.get('model', None),
                firmware_version=device_data.get('softwareVersion', None),
                last_seen=datetime.utcnow(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            return device
            
        except Exception as e:
            logger.error(f"Error parsing Alexa device: {e}")
            return None
            
    def _map_alexa_device_type(self, device_data: Dict[str, Any]) -> DeviceType:
        """Map Alexa device type to our device type."""
        device_type = device_data.get('deviceType', '').lower()
        
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
        
    def _extract_alexa_capabilities(self, device_data: Dict[str, Any]) -> List[DeviceCapability]:
        """Extract device capabilities from Alexa device data."""
        capabilities = []
        
        # Check for basic on/off capability
        if device_data.get('supportsOnOff'):
            capabilities.append(DeviceCapability.ON_OFF)
            
        # Check for dimming capability
        if device_data.get('supportsDimming'):
            capabilities.append(DeviceCapability.DIMMING)
            
        # Check for color capability
        if device_data.get('supportsColor'):
            capabilities.append(DeviceCapability.COLOR)
            
        # Check for temperature capability
        if device_data.get('supportsTemperature'):
            capabilities.append(DeviceCapability.TEMPERATURE)
            
        # Check for humidity capability
        if device_data.get('supportsHumidity'):
            capabilities.append(DeviceCapability.HUMIDITY)
            
        # Check for motion capability
        if device_data.get('supportsMotion'):
            capabilities.append(DeviceCapability.MOTION)
            
        # Check for contact capability
        if device_data.get('supportsContact'):
            capabilities.append(DeviceCapability.CONTACT)
            
        # Check for lock/unlock capability
        if device_data.get('supportsLockUnlock'):
            capabilities.append(DeviceCapability.LOCK_UNLOCK)
            
        # Check for open/close capability
        if device_data.get('supportsOpenClose'):
            capabilities.append(DeviceCapability.OPEN_CLOSE)
            
        # Check for volume capability
        if device_data.get('supportsVolume'):
            capabilities.append(DeviceCapability.VOLUME)
            
        # Check for thermostat control
        if device_data.get('supportsThermostat'):
            capabilities.append(DeviceCapability.THERMOSTAT_CONTROL)
            
        # Check for camera stream
        if device_data.get('supportsCameraStream'):
            capabilities.append(DeviceCapability.CAMERA_STREAM)
            
        # Check for vacuum control
        if device_data.get('supportsVacuum'):
            capabilities.append(DeviceCapability.VACUUM_CONTROL)
            
        # Check for garage door control
        if device_data.get('supportsGarageDoor'):
            capabilities.append(DeviceCapability.GARAGE_DOOR_CONTROL)
            
        # Check for irrigation control
        if device_data.get('supportsIrrigation'):
            capabilities.append(DeviceCapability.IRRIGATION_CONTROL)
            
        # Check for alarm control
        if device_data.get('supportsAlarm'):
            capabilities.append(DeviceCapability.ALARM_CONTROL)
            
        return capabilities
        
    async def send_voice_command(self, command: str) -> bool:
        """Send a voice command to Alexa."""
        try:
            if not self.session:
                return False
                
            headers = self._get_auth_headers()
            headers['Content-Type'] = 'application/json'
            
            data = {
                'command': command,
                'deviceSerialNumber': self.config.custom_config.get('echo_device_id')
            }
            
            async with self.session.post(
                "https://alexa.amazon.com/api/behaviors/preview",
                headers=headers,
                json=data
            ) as response:
                if response.status == 200:
                    logger.info(f"Sent voice command: {command}")
                    return True
                else:
                    logger.error(f"Failed to send voice command: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error sending voice command: {e}")
            return False
