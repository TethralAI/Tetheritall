"""
Home Assistant IoT Hub Connector
Integrates with Home Assistant to discover and control devices.
Supports the full Home Assistant API and device ecosystem.
"""

import asyncio
import logging
import aiohttp
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import websockets
from urllib.parse import urljoin

from .base import BaseIoTHub, HubConfig, IoTDevice, DeviceType, DeviceCapability, HubStatus

logger = logging.getLogger(__name__)


class HomeAssistantHub(BaseIoTHub):
    """Home Assistant IoT Hub connector."""
    
    def __init__(self, config: HubConfig):
        super().__init__(config)
        self.session: Optional[aiohttp.ClientSession] = None
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self._event_subscription_id: Optional[str] = None
        
    async def connect(self) -> bool:
        """Connect to Home Assistant."""
        try:
            self.status = HubStatus.CONNECTING
            
            # Create HTTP session
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                connector=aiohttp.TCPConnector(verify_ssl=self.config.ssl_verify)
            )
            
            # Test connection
            base_url = f"http://{self.config.host}:{self.config.port}"
            async with self.session.get(f"{base_url}/api/") as response:
                if response.status == 200:
                    self.status = HubStatus.CONNECTED
                    logger.info(f"Connected to Home Assistant at {base_url}")
                    return True
                else:
                    logger.error(f"Failed to connect to Home Assistant: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error connecting to Home Assistant: {e}")
            self.status = HubStatus.ERROR
            return False
            
    async def disconnect(self) -> bool:
        """Disconnect from Home Assistant."""
        try:
            if self.websocket:
                await self.websocket.close()
                self.websocket = None
                
            if self.session:
                await self.session.close()
                self.session = None
                
            self.status = HubStatus.DISCONNECTED
            logger.info("Disconnected from Home Assistant")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting from Home Assistant: {e}")
            return False
            
    async def authenticate(self) -> bool:
        """Authenticate with Home Assistant."""
        try:
            if not self.session:
                return False
                
            base_url = f"http://{self.config.host}:{self.config.port}"
            
            # Use API key or token for authentication
            headers = {}
            if self.config.api_key:
                headers['Authorization'] = f'Bearer {self.config.api_key}'
            elif self.config.token:
                headers['Authorization'] = f'Bearer {self.config.token}'
            else:
                logger.error("No API key or token provided for Home Assistant")
                return False
                
            # Test authentication
            async with self.session.get(f"{base_url}/api/", headers=headers) as response:
                if response.status == 200:
                    logger.info("Authenticated with Home Assistant")
                    return True
                else:
                    logger.error(f"Authentication failed: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error authenticating with Home Assistant: {e}")
            return False
            
    async def discover_devices(self) -> List[IoTDevice]:
        """Discover devices from Home Assistant."""
        try:
            if not self.session:
                return []
                
            base_url = f"http://{self.config.host}:{self.config.port}"
            headers = {}
            if self.config.api_key:
                headers['Authorization'] = f'Bearer {self.config.api_key}'
            elif self.config.token:
                headers['Authorization'] = f'Bearer {self.config.token}'
                
            # Get all states (devices)
            async with self.session.get(f"{base_url}/api/states", headers=headers) as response:
                if response.status == 200:
                    states = await response.json()
                    devices = []
                    
                    for state in states:
                        device = await self._parse_device_state(state)
                        if device:
                            devices.append(device)
                            
                    logger.info(f"Discovered {len(devices)} devices from Home Assistant")
                    return devices
                else:
                    logger.error(f"Failed to get states: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error discovering devices: {e}")
            return []
            
    async def get_device_state(self, device_id: str) -> Dict[str, Any]:
        """Get current state of a device."""
        try:
            if not self.session:
                return {}
                
            base_url = f"http://{self.config.host}:{self.config.port}"
            headers = {}
            if self.config.api_key:
                headers['Authorization'] = f'Bearer {self.config.api_key}'
            elif self.config.token:
                headers['Authorization'] = f'Bearer {self.config.token}'
                
            async with self.session.get(f"{base_url}/api/states/{device_id}", headers=headers) as response:
                if response.status == 200:
                    state = await response.json()
                    return state
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
                
            base_url = f"http://{self.config.host}:{self.config.port}"
            headers = {
                'Content-Type': 'application/json'
            }
            if self.config.api_key:
                headers['Authorization'] = f'Bearer {self.config.api_key}'
            elif self.config.token:
                headers['Authorization'] = f'Bearer {self.config.token}'
                
            # Call service to set state
            service_data = {
                'entity_id': device_id,
                **state
            }
            
            async with self.session.post(
                f"{base_url}/api/services/homeassistant/turn_on",
                headers=headers,
                json=service_data
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
        """Subscribe to Home Assistant events via WebSocket."""
        try:
            # Connect to WebSocket
            ws_url = f"ws://{self.config.host}:{self.config.port}/api/websocket"
            
            # Authenticate WebSocket connection
            auth_message = {
                'type': 'auth',
                'access_token': self.config.api_key or self.config.token
            }
            
            self.websocket = await websockets.connect(ws_url)
            await self.websocket.send(json.dumps(auth_message))
            
            auth_response = await self.websocket.recv()
            auth_data = json.loads(auth_response)
            
            if auth_data.get('type') == 'auth_ok':
                # Subscribe to state changes
                subscribe_message = {
                    'id': 1,
                    'type': 'subscribe_events',
                    'event_type': 'state_changed'
                }
                
                await self.websocket.send(json.dumps(subscribe_message))
                subscribe_response = await self.websocket.recv()
                subscribe_data = json.loads(subscribe_response)
                
                if subscribe_data.get('type') == 'result' and subscribe_data.get('success'):
                    self._event_subscription_id = subscribe_data.get('id')
                    
                    # Start event listener
                    asyncio.create_task(self._event_listener())
                    
                    logger.info("Subscribed to Home Assistant events")
                    return True
                    
            logger.error("Failed to subscribe to events")
            return False
            
        except Exception as e:
            logger.error(f"Error subscribing to events: {e}")
            return False
            
    async def _event_listener(self):
        """Listen for WebSocket events."""
        try:
            while self._running and self.websocket:
                message = await self.websocket.recv()
                data = json.loads(message)
                
                if data.get('type') == 'event' and data.get('event', {}).get('event_type') == 'state_changed':
                    event_data = data['event']['data']
                    entity_id = event_data.get('entity_id')
                    
                    if entity_id:
                        # Get updated state
                        new_state = await self.get_device_state(entity_id)
                        if new_state:
                            # Update device in our cache
                            device = self.devices.get(entity_id)
                            if device:
                                device.state = new_state
                                device.updated_at = datetime.utcnow()
                                
                                # Notify callbacks
                                await self._notify_callbacks('device_state_changed', device)
                                
        except Exception as e:
            logger.error(f"Error in event listener: {e}")
            
    async def _parse_device_state(self, state: Dict[str, Any]) -> Optional[IoTDevice]:
        """Parse Home Assistant state into IoTDevice."""
        try:
            entity_id = state.get('entity_id')
            if not entity_id:
                return None
                
            # Extract device type from entity_id
            domain = entity_id.split('.')[0] if '.' in entity_id else 'unknown'
            device_type = self._map_domain_to_device_type(domain)
            
            # Extract capabilities from attributes
            attributes = state.get('attributes', {})
            capabilities = self._extract_capabilities(attributes, domain)
            
            # Create device
            device = IoTDevice(
                device_id=entity_id,
                name=attributes.get('friendly_name', entity_id),
                device_type=device_type,
                hub_id=self.config.hub_id,
                hub_name=self.config.name,
                capabilities=capabilities,
                attributes=attributes,
                state=state,
                location=attributes.get('location', None),
                manufacturer=attributes.get('manufacturer', None),
                model=attributes.get('model', None),
                firmware_version=attributes.get('firmware_version', None),
                last_seen=datetime.utcnow(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            return device
            
        except Exception as e:
            logger.error(f"Error parsing device state: {e}")
            return None
            
    def _map_domain_to_device_type(self, domain: str) -> DeviceType:
        """Map Home Assistant domain to device type."""
        domain_mapping = {
            'light': DeviceType.LIGHT,
            'switch': DeviceType.SWITCH,
            'sensor': DeviceType.SENSOR,
            'climate': DeviceType.THERMOSTAT,
            'camera': DeviceType.CAMERA,
            'lock': DeviceType.LOCK,
            'fan': DeviceType.FAN,
            'cover': DeviceType.BLINDS,
            'media_player': DeviceType.MEDIA_PLAYER,
            'binary_sensor': DeviceType.BINARY_SENSOR,
            'vacuum': DeviceType.VACUUM,
            'garage_door': DeviceType.GARAGE_DOOR,
            'alarm_control_panel': DeviceType.ALARM,
            'button': DeviceType.BUTTON,
            'remote': DeviceType.REMOTE
        }
        
        return domain_mapping.get(domain, DeviceType.UNKNOWN)
        
    def _extract_capabilities(self, attributes: Dict[str, Any], domain: str) -> List[DeviceCapability]:
        """Extract device capabilities from attributes."""
        capabilities = []
        
        # Basic on/off capability
        if domain in ['light', 'switch', 'fan', 'media_player']:
            capabilities.append(DeviceCapability.ON_OFF)
            
        # Dimming capability
        if domain == 'light' and attributes.get('brightness') is not None:
            capabilities.append(DeviceCapability.DIMMING)
            
        # Color capability
        if domain == 'light' and attributes.get('rgb_color') is not None:
            capabilities.append(DeviceCapability.COLOR)
            
        # Temperature capability
        if attributes.get('temperature') is not None:
            capabilities.append(DeviceCapability.TEMPERATURE)
            
        # Humidity capability
        if attributes.get('humidity') is not None:
            capabilities.append(DeviceCapability.HUMIDITY)
            
        # Motion capability
        if domain == 'binary_sensor' and 'motion' in attributes.get('device_class', ''):
            capabilities.append(DeviceCapability.MOTION)
            
        # Contact capability
        if domain == 'binary_sensor' and 'opening' in attributes.get('device_class', ''):
            capabilities.append(DeviceCapability.CONTACT)
            
        # Lock/unlock capability
        if domain == 'lock':
            capabilities.append(DeviceCapability.LOCK_UNLOCK)
            
        # Open/close capability
        if domain in ['cover', 'garage_door']:
            capabilities.append(DeviceCapability.OPEN_CLOSE)
            
        # Volume capability
        if domain == 'media_player' and attributes.get('volume_level') is not None:
            capabilities.append(DeviceCapability.VOLUME)
            
        # Thermostat control
        if domain == 'climate':
            capabilities.append(DeviceCapability.THERMOSTAT_CONTROL)
            
        # Camera stream
        if domain == 'camera':
            capabilities.append(DeviceCapability.CAMERA_STREAM)
            
        # Vacuum control
        if domain == 'vacuum':
            capabilities.append(DeviceCapability.VACUUM_CONTROL)
            
        # Alarm control
        if domain == 'alarm_control_panel':
            capabilities.append(DeviceCapability.ALARM_CONTROL)
            
        return capabilities
        
    async def call_service(self, domain: str, service: str, data: Dict[str, Any]) -> bool:
        """Call a Home Assistant service."""
        try:
            if not self.session:
                return False
                
            base_url = f"http://{self.config.host}:{self.config.port}"
            headers = {
                'Content-Type': 'application/json'
            }
            if self.config.api_key:
                headers['Authorization'] = f'Bearer {self.config.api_key}'
            elif self.config.token:
                headers['Authorization'] = f'Bearer {self.config.token}'
                
            async with self.session.post(
                f"{base_url}/api/services/{domain}/{service}",
                headers=headers,
                json=data
            ) as response:
                if response.status == 200:
                    logger.info(f"Called service {domain}.{service}")
                    return True
                else:
                    logger.error(f"Failed to call service: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error calling service: {e}")
            return False
            
    async def get_config(self) -> Dict[str, Any]:
        """Get Home Assistant configuration."""
        try:
            if not self.session:
                return {}
                
            base_url = f"http://{self.config.host}:{self.config.port}"
            headers = {}
            if self.config.api_key:
                headers['Authorization'] = f'Bearer {self.config.api_key}'
            elif self.config.token:
                headers['Authorization'] = f'Bearer {self.config.token}'
                
            async with self.session.get(f"{base_url}/api/config", headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to get config: {response.status}")
                    return {}
                    
        except Exception as e:
            logger.error(f"Error getting config: {e}")
            return {}
