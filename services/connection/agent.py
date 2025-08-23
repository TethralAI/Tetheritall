"""
IoT Connection Agent
Enhanced device discovery, connection, and trust establishment.
Handles multi-protocol support, device onboarding, and secure communication.
"""

from __future__ import annotations

import asyncio
from typing import Dict, List, Any, Optional, Protocol
from datetime import datetime
import logging
from enum import Enum

from shared.config.settings import settings
from shared.database.api_database import get_session_factory, session_scope
from shared.database.models import Device, ApiEndpoint, ScanResult

# Phase 2 imports
from .registry import DeviceRegistry
from .communication import CommunicationManager
from .state import StateManager
from .events import EventManager, EventType, EventPriority

logger = logging.getLogger(__name__)


class ConnectionProtocol(Enum):
    """Supported connection protocols."""
    WIFI = "wifi"
    BLUETOOTH = "bluetooth"
    ZIGBEE = "zigbee"
    ZWAVE = "zwave"
    MATTER = "matter"
    API = "api"


class ConnectionStatus(Enum):
    """Connection status states."""
    DISCOVERED = "discovered"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    TRUSTED = "trusted"
    FAILED = "failed"


class DeviceInfo:
    """Device information container."""
    
    def __init__(self, 
                 device_id: str,
                 name: str,
                 model: str,
                 manufacturer: str,
                 protocol: ConnectionProtocol,
                 capabilities: List[str],
                 endpoints: List[str] = None):
        self.device_id = device_id
        self.name = name
        self.model = model
        self.manufacturer = manufacturer
        self.protocol = protocol
        self.capabilities = capabilities
        self.endpoints = endpoints or []
        self.status = ConnectionStatus.DISCOVERED
        self.trust_level = 0.0
        self.last_seen = datetime.utcnow()


class ConnectionAgent:
    """Enhanced IoT Device Connection Agent."""
    
    def __init__(self):
        self._running = False
        self._session_factory = get_session_factory(settings.database_url)
        self._scan_tasks: List[asyncio.Task] = []
        self._connected_devices: Dict[str, DeviceInfo] = {}
        self._protocol_handlers: Dict[ConnectionProtocol, Any] = {}
        self._trust_manager = None  # Will be initialized with trust manager
        
        # Phase 2 components
        self._device_registry: Optional[DeviceRegistry] = None
        self._communication_manager: Optional[CommunicationManager] = None
        self._state_manager: Optional[StateManager] = None
        self._event_manager: Optional[EventManager] = None
        
    async def start(self):
        """Start the connection agent."""
        self._running = True
        
        # Initialize Phase 2 components
        await self._initialize_phase2_components()
        
        # Initialize protocol handlers
        await self._initialize_protocol_handlers()
        
        logger.info("Connection agent started with protocol handlers and Phase 2 components")
        
    async def stop(self):
        """Stop the connection agent."""
        self._running = False
        
        # Stop Phase 2 components
        await self._stop_phase2_components()
        
        # Cancel all scan tasks
        for task in self._scan_tasks:
            task.cancel()
        # Disconnect all devices
        await self._disconnect_all_devices()
        logger.info("Connection agent stopped")
        
    def is_running(self) -> bool:
        """Check if the agent is running."""
        return self._running
        
    async def _initialize_protocol_handlers(self):
        """Initialize protocol handlers for different connection types."""
        try:
            # Import protocol handlers
            from .protocols.wifi import WiFiHandler
            from .protocols.bluetooth import BluetoothHandler
            from .protocols.zigbee import ZigbeeHandler
            from .protocols.zwave import ZWaveHandler
            from .protocols.matter import MatterHandler
            from .protocols.api import APIHandler
            
            # Initialize handlers
            self._protocol_handlers[ConnectionProtocol.WIFI] = WiFiHandler()
            self._protocol_handlers[ConnectionProtocol.BLUETOOTH] = BluetoothHandler()
            self._protocol_handlers[ConnectionProtocol.ZIGBEE] = ZigbeeHandler()
            self._protocol_handlers[ConnectionProtocol.ZWAVE] = ZWaveHandler()
            self._protocol_handlers[ConnectionProtocol.MATTER] = MatterHandler()
            self._protocol_handlers[ConnectionProtocol.API] = APIHandler()
            
            logger.info(f"Initialized {len(self._protocol_handlers)} protocol handlers")
            
        except ImportError as e:
            logger.warning(f"Some protocol handlers not available: {e}")
            # Create placeholder handlers for missing protocols
            for protocol in ConnectionProtocol:
                if protocol not in self._protocol_handlers:
                    self._protocol_handlers[protocol] = PlaceholderHandler(protocol)
        
    async def discover_devices(self, protocols: List[ConnectionProtocol] = None) -> List[DeviceInfo]:
        """Discover devices using specified protocols."""
        if not self._running:
            raise RuntimeError("Connection agent is not running")
            
        if protocols is None:
            protocols = list(ConnectionProtocol)
            
        discovered_devices = []
        
        for protocol in protocols:
            if protocol in self._protocol_handlers:
                try:
                    handler = self._protocol_handlers[protocol]
                    devices = await handler.discover()
                    discovered_devices.extend(devices)
                    logger.info(f"Discovered {len(devices)} devices via {protocol.value}")
                except Exception as e:
                    logger.error(f"Error discovering devices via {protocol.value}: {e}")
                    
        return discovered_devices
        
    async def connect_device(self, device_info: DeviceInfo) -> bool:
        """Connect to a specific device."""
        if not self._running:
            raise RuntimeError("Connection agent is not running")
            
        try:
            device_info.status = ConnectionStatus.CONNECTING
            
            # Get protocol handler
            handler = self._protocol_handlers.get(device_info.protocol)
            if not handler:
                raise ValueError(f"No handler for protocol {device_info.protocol}")
                
            # Attempt connection
            success = await handler.connect(device_info)
            
            if success:
                device_info.status = ConnectionStatus.CONNECTED
                self._connected_devices[device_info.device_id] = device_info
                logger.info(f"Connected to device {device_info.name} via {device_info.protocol.value}")
                return True
            else:
                device_info.status = ConnectionStatus.FAILED
                logger.error(f"Failed to connect to device {device_info.name}")
                return False
                
        except Exception as e:
            device_info.status = ConnectionStatus.FAILED
            logger.error(f"Error connecting to device {device_info.name}: {e}")
            return False
            
    async def authenticate_device(self, device_id: str) -> bool:
        """Authenticate a connected device."""
        if device_id not in self._connected_devices:
            raise ValueError(f"Device {device_id} not connected")
            
        device_info = self._connected_devices[device_id]
        
        try:
            # Get protocol handler
            handler = self._protocol_handlers.get(device_info.protocol)
            
            # Attempt authentication
            success = await handler.authenticate(device_info)
            
            if success:
                device_info.status = ConnectionStatus.AUTHENTICATED
                logger.info(f"Authenticated device {device_info.name}")
                return True
            else:
                device_info.status = ConnectionStatus.FAILED
                logger.error(f"Failed to authenticate device {device_info.name}")
                return False
                
        except Exception as e:
            device_info.status = ConnectionStatus.FAILED
            logger.error(f"Error authenticating device {device_info.name}: {e}")
            return False
            
    async def establish_trust(self, device_id: str) -> bool:
        """Establish trust relationship with a device."""
        if device_id not in self._connected_devices:
            raise ValueError(f"Device {device_id} not connected")
            
        device_info = self._connected_devices[device_id]
        
        if device_info.status != ConnectionStatus.AUTHENTICATED:
            raise ValueError(f"Device {device_id} must be authenticated before establishing trust")
            
        try:
            # Import trust manager when needed
            if self._trust_manager is None:
                from .trust.channels import TrustManager
                self._trust_manager = TrustManager()
                
            # Establish trust channel
            trust_level = await self._trust_manager.establish_trust(device_info)
            
            if trust_level > 0.0:
                device_info.trust_level = trust_level
                device_info.status = ConnectionStatus.TRUSTED
                logger.info(f"Established trust with device {device_info.name} (level: {trust_level})")
                return True
            else:
                logger.error(f"Failed to establish trust with device {device_info.name}")
                return False
                
        except Exception as e:
            logger.error(f"Error establishing trust with device {device_info.name}: {e}")
            return False
            
    async def onboard_device(self, device_info: DeviceInfo) -> bool:
        """Complete device onboarding process."""
        try:
            # Step 1: Connect
            if not await self.connect_device(device_info):
                return False
                
            # Step 2: Authenticate
            if not await self.authenticate_device(device_info.device_id):
                return False
                
            # Step 3: Establish trust
            if not await self.establish_trust(device_info.device_id):
                return False
                
            # Step 4: Save to database
            await self._save_device_to_database(device_info)
            
            logger.info(f"Successfully onboarded device {device_info.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error onboarding device {device_info.name}: {e}")
            return False
            
    async def _save_device_to_database(self, device_info: DeviceInfo):
        """Save device information to database."""
        with session_scope(self._session_factory) as session:
            device = Device(
                model=device_info.model,
                manufacturer=device_info.manufacturer,
                firmware_version="unknown"  # Will be updated during device communication
            )
            session.add(device)
            session.commit()
            
            # Save endpoints if available
            for endpoint in device_info.endpoints:
                api_endpoint = ApiEndpoint(
                    device_id=device.id,
                    endpoint_url=endpoint,
                    method="GET",  # Default, will be updated
                    authentication_type="unknown"  # Will be updated during authentication
                )
                session.add(api_endpoint)
                
            session.commit()
            
    async def _disconnect_all_devices(self):
        """Disconnect all connected devices."""
        for device_id, device_info in list(self._connected_devices.items()):
            try:
                handler = self._protocol_handlers.get(device_info.protocol)
                if handler:
                    await handler.disconnect(device_info)
                logger.info(f"Disconnected device {device_info.name}")
            except Exception as e:
                logger.error(f"Error disconnecting device {device_info.name}: {e}")
                
        self._connected_devices.clear()
        
    async def list_connected_devices(self) -> List[Dict[str, Any]]:
        """List all connected devices."""
        return [
            {
                "device_id": device_info.device_id,
                "name": device_info.name,
                "model": device_info.model,
                "manufacturer": device_info.manufacturer,
                "protocol": device_info.protocol.value,
                "status": device_info.status.value,
                "trust_level": device_info.trust_level,
                "capabilities": device_info.capabilities,
                "endpoints": device_info.endpoints,
                "last_seen": device_info.last_seen.isoformat(),
            }
            for device_info in self._connected_devices.values()
        ]
        
    async def get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific device."""
        if device_id not in self._connected_devices:
            return None
            
        device_info = self._connected_devices[device_id]
        return {
            "device_id": device_info.device_id,
            "name": device_info.name,
            "status": device_info.status.value,
            "trust_level": device_info.trust_level,
            "last_seen": device_info.last_seen.isoformat(),
        }
        
    # Legacy methods for backward compatibility
    async def list_devices(self) -> List[Dict[str, Any]]:
        """List all discovered devices (legacy method)."""
        with session_scope(self._session_factory) as session:
            devices = session.query(Device).all()
            return [
                {
                    "id": device.id,
                    "model": device.model,
                    "manufacturer": device.manufacturer,
                    "firmware_version": device.firmware_version,
                    "created_at": device.created_at.isoformat() if device.created_at else None,
                }
                for device in devices
            ]
            
    async def start_scan(self) -> Dict[str, Any]:
        """Start a new discovery scan (legacy method)."""
        if not self._running:
            raise RuntimeError("Connection agent is not running")
            
        task = asyncio.create_task(self._perform_scan())
        self._scan_tasks.append(task)
        
        return {
            "scan_id": id(task),
            "status": "started",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    async def _perform_scan(self):
        """Perform the actual discovery scan (legacy method)."""
        try:
            logger.info("Starting discovery scan")
            
            # Use new discovery method
            discovered_devices = await self.discover_devices()
            
            # Save scan results
            with session_scope(self._session_factory) as session:
                for device_info in discovered_devices:
                    scan_result = ScanResult(
                        device_id=None,  # Will be set when device is saved
                        agent_type="connection_agent",
                        raw_data=f"Discovered via {device_info.protocol.value}"
                    )
                    session.add(scan_result)
                session.commit()
                
            logger.info(f"Discovery scan completed, found {len(discovered_devices)} devices")
            
        except Exception as e:
            logger.error(f"Error during discovery scan: {e}")

    # Phase 2 methods
    async def _initialize_phase2_components(self):
        """Initialize Phase 2 components."""
        try:
            # Initialize device registry
            self._device_registry = DeviceRegistry()
            await self._device_registry.start()
            
            # Initialize state manager
            self._state_manager = StateManager()
            await self._state_manager.start()
            
            # Initialize event manager
            self._event_manager = EventManager()
            await self._event_manager.start()
            
            # Initialize communication manager
            self._communication_manager = CommunicationManager()
            await self._communication_manager.start(self._device_registry)
            
            # Set up event subscriptions
            await self._setup_event_subscriptions()
            
            logger.info("Phase 2 components initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing Phase 2 components: {e}")
            raise
            
    async def _stop_phase2_components(self):
        """Stop Phase 2 components."""
        try:
            if self._communication_manager:
                await self._communication_manager.stop()
            if self._event_manager:
                await self._event_manager.stop()
            if self._state_manager:
                await self._state_manager.stop()
            if self._device_registry:
                await self._device_registry.stop()
                
            logger.info("Phase 2 components stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping Phase 2 components: {e}")
            
    async def _setup_event_subscriptions(self):
        """Set up event subscriptions for the connection agent."""
        try:
            if not self._event_manager:
                return
                
            # Subscribe to device events
            await self._event_manager.subscribe_to_device_events(
                subscriber_id="connection_agent",
                callback=self._handle_device_event
            )
            
            # Subscribe to security events
            await self._event_manager.subscribe_to_security_events(
                subscriber_id="connection_agent",
                callback=self._handle_security_event
            )
            
            logger.info("Event subscriptions set up successfully")
            
        except Exception as e:
            logger.error(f"Error setting up event subscriptions: {e}")
            
    async def _handle_device_event(self, event):
        """Handle device-related events."""
        try:
            event_type = event.event_type
            device_id = event.data.get('device_id')
            
            if event_type == EventType.DEVICE_DISCOVERED:
                logger.info(f"Device discovered: {device_id}")
                # Register device in registry and state manager
                if device_id and self._device_registry and self._state_manager:
                    # This would be called when a device is discovered
                    pass
                    
            elif event_type == EventType.DEVICE_CONNECTED:
                logger.info(f"Device connected: {device_id}")
                # Update device state
                if device_id and self._state_manager:
                    await self._state_manager.update_device_state(
                        device_id, 
                        self._state_manager.models.StateType.CONNECTED,
                        reason="Device connected"
                    )
                    
            elif event_type == EventType.DEVICE_DISCONNECTED:
                logger.info(f"Device disconnected: {device_id}")
                # Update device state
                if device_id and self._state_manager:
                    await self._state_manager.update_device_state(
                        device_id,
                        self._state_manager.models.StateType.DISCONNECTED,
                        reason="Device disconnected"
                    )
                    
        except Exception as e:
            logger.error(f"Error handling device event: {e}")
            
    async def _handle_security_event(self, event):
        """Handle security-related events."""
        try:
            event_type = event.event_type
            device_id = event.data.get('device_id')
            
            if event_type == EventType.AUTHENTICATION_SUCCESS:
                logger.info(f"Authentication successful: {device_id}")
                # Update device state
                if device_id and self._state_manager:
                    await self._state_manager.update_device_state(
                        device_id,
                        self._state_manager.models.StateType.AUTHENTICATED,
                        reason="Authentication successful"
                    )
                    
            elif event_type == EventType.AUTHENTICATION_FAILED:
                logger.warning(f"Authentication failed: {device_id}")
                # Update device state
                if device_id and self._state_manager:
                    await self._state_manager.update_device_state(
                        device_id,
                        self._state_manager.models.StateType.ERROR,
                        reason="Authentication failed"
                    )
                    
        except Exception as e:
            logger.error(f"Error handling security event: {e}")


class PlaceholderHandler:
    """Placeholder handler for protocols that aren't implemented yet."""
    
    def __init__(self, protocol: ConnectionProtocol):
        self.protocol = protocol
        
    async def discover(self) -> List[DeviceInfo]:
        """Placeholder discovery method."""
        logger.warning(f"Discovery not implemented for {self.protocol.value}")
        return []
        
    async def connect(self, device_info: DeviceInfo) -> bool:
        """Placeholder connect method."""
        logger.warning(f"Connection not implemented for {self.protocol.value}")
        return False
        
    async def authenticate(self, device_info: DeviceInfo) -> bool:
        """Placeholder authenticate method."""
        logger.warning(f"Authentication not implemented for {self.protocol.value}")
        return False
        
    async def disconnect(self, device_info: DeviceInfo):
        """Placeholder disconnect method."""
        logger.warning(f"Disconnection not implemented for {self.protocol.value}")
