"""
IoT Hub Manager
Manages multiple IoT hub connections and provides a unified interface for device discovery and control.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import json
import uuid

from .hubs.base import (
    BaseIoTHub, HubConfig, IoTDevice, DeviceType, DeviceCapability,
)
from .hubs import (
    HomeAssistantHub, AlexaHub, HomeKitHub, SmartThingsHub, NestHub
)

logger = logging.getLogger(__name__)


class IoTHubManager:
    """Manages multiple IoT hub connections."""
    
    def __init__(self):
        self.hubs: Dict[str, BaseIoTHub] = {}
        self.devices: Dict[str, IoTDevice] = {}
        self._callbacks: List[Callable] = []
        self._running = False
        self._discovery_task: Optional[asyncio.Task] = None
        self._event_task: Optional[asyncio.Task] = None
        
    async def add_hub(self, config: HubConfig) -> str:
        """Add a new IoT hub."""
        try:
            hub_id = config.hub_id
            logger.info(f"Adding hub: {hub_id} ({config.hub_type})")
            
            # Create hub instance based on type
            hub = self._create_hub_instance(config)
            if not hub:
                raise ValueError(f"Unsupported hub type: {config.hub_type}")
            
            logger.info(f"Created hub instance: {type(hub).__name__}")
                
            # Store hub
            self.hubs[hub_id] = hub
            logger.info(f"Stored hub in manager. Total hubs: {len(self.hubs)}")
            
            # Add event callback
            hub.add_callback(self._handle_hub_event)
            
            logger.info(f"Added IoT hub: {config.name} ({config.hub_type})")
            return hub_id
            
        except Exception as e:
            logger.error(f"Error adding hub: {e}")
            raise
            
    def _create_hub_instance(self, config: HubConfig) -> Optional[BaseIoTHub]:
        """Create hub instance based on configuration."""
        hub_type = config.hub_type.lower()
        
        if hub_type == 'homeassistant':
            return HomeAssistantHub(config)
        elif hub_type == 'alexa':
            return AlexaHub(config)
        elif hub_type == 'homekit':
            return HomeKitHub(config)
        elif hub_type == 'smartthings':
            return SmartThingsHub(config)
        elif hub_type == 'nest':
            return NestHub(config)
        else:
            logger.error(f"Unsupported hub type: {hub_type}")
            return None
            
    async def remove_hub(self, hub_id: str) -> bool:
        """Remove an IoT hub."""
        try:
            if hub_id not in self.hubs:
                logger.warning(f"Hub {hub_id} not found")
                return False
                
            hub = self.hubs[hub_id]
            
            # Stop hub
            await hub.stop()
            
            # Remove hub devices
            devices_to_remove = [device_id for device_id, device in self.devices.items() if device.hub_id == hub_id]
            for device_id in devices_to_remove:
                del self.devices[device_id]
                
            # Remove hub
            del self.hubs[hub_id]
            
            logger.info(f"Removed IoT hub: {hub_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing hub {hub_id}: {e}")
            return False
            
    async def start(self):
        """Start the IoT hub manager."""
        self._running = True
        
        # Start all hubs
        for hub_id, hub in self.hubs.items():
            try:
                await hub.start()
                logger.info(f"Started hub: {hub_id}")
            except Exception as e:
                logger.error(f"Error starting hub {hub_id}: {e}")
                
        # Start background tasks
        self._discovery_task = asyncio.create_task(self._device_discovery_loop())
        self._event_task = asyncio.create_task(self._event_processing_loop())
        
        logger.info("IoT Hub Manager started")
        
    async def stop(self):
        """Stop the IoT hub manager."""
        self._running = False
        
        # Cancel background tasks
        if self._discovery_task:
            self._discovery_task.cancel()
        if self._event_task:
            self._event_task.cancel()
            
        # Stop all hubs
        for hub_id, hub in self.hubs.items():
            try:
                await hub.stop()
                logger.info(f"Stopped hub: {hub_id}")
            except Exception as e:
                logger.error(f"Error stopping hub {hub_id}: {e}")
                
        logger.info("IoT Hub Manager stopped")
        
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
                
    async def _handle_hub_event(self, event_type: str, data: Any):
        """Handle events from individual hubs."""
        try:
            if event_type == 'device_discovered':
                device = data
                self.devices[device.device_id] = device
                await self._notify_callbacks('device_discovered', device)
                
            elif event_type == 'device_state_changed':
                device = data
                self.devices[device.device_id] = device
                await self._notify_callbacks('device_state_changed', device)
                
        except Exception as e:
            logger.error(f"Error handling hub event: {e}")
            
    async def _device_discovery_loop(self):
        """Background task for device discovery."""
        while self._running:
            try:
                # Discover devices from all hubs
                for hub_id, hub in self.hubs.items():
                    if hub.is_connected():
                        try:
                            devices = await hub.discover_devices()
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
                            logger.error(f"Error discovering devices from hub {hub_id}: {e}")
                            
            except Exception as e:
                logger.error(f"Error in device discovery loop: {e}")
                
            await asyncio.sleep(300)  # Discover every 5 minutes
            
    async def _event_processing_loop(self):
        """Background task for event processing."""
        while self._running:
            try:
                # Process any pending events
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error in event processing loop: {e}")
                
    async def get_all_devices(self) -> List[IoTDevice]:
        """Get all discovered devices from all hubs."""
        return list(self.devices.values())
        
    async def get_devices_by_hub(self, hub_id: str) -> List[IoTDevice]:
        """Get devices from a specific hub."""
        return [device for device in self.devices.values() if device.hub_id == hub_id]
        
    async def get_devices_by_type(self, device_type: DeviceType) -> List[IoTDevice]:
        """Get devices of a specific type."""
        return [device for device in self.devices.values() if device.device_type == device_type]
        
    async def get_device(self, device_id: str) -> Optional[IoTDevice]:
        """Get a specific device."""
        return self.devices.get(device_id)
        
    async def get_device_state(self, device_id: str) -> Dict[str, Any]:
        """Get current state of a device."""
        device = self.devices.get(device_id)
        if not device:
            return {}
            
        hub = self.hubs.get(device.hub_id)
        if not hub:
            return {}
            
        try:
            return await hub.get_device_state(device_id)
        except Exception as e:
            logger.error(f"Error getting device state: {e}")
            return {}
            
    async def set_device_state(self, device_id: str, state: Dict[str, Any]) -> bool:
        """Set state of a device."""
        device = self.devices.get(device_id)
        if not device:
            return False
            
        hub = self.hubs.get(device.hub_id)
        if not hub:
            return False
            
        try:
            success = await hub.set_device_state(device_id, state)
            if success:
                # Update local device state
                device.state.update(state)
                device.updated_at = datetime.utcnow()
                await self._notify_callbacks('device_state_changed', device)
            return success
        except Exception as e:
            logger.error(f"Error setting device state: {e}")
            return False
            
    async def get_hub_status(self) -> Dict[str, Any]:
        """Get status of all hubs."""
        status = {}
        for hub_id, hub in self.hubs.items():
            status[hub_id] = hub.get_status()
        return status
        
    async def get_manager_statistics(self) -> Dict[str, Any]:
        """Get IoT hub manager statistics."""
        total_devices = len(self.devices)
        device_types = {}
        hub_devices = {}
        
        for device in self.devices.values():
            # Count by device type
            device_type = device.device_type.value
            device_types[device_type] = device_types.get(device_type, 0) + 1
            
            # Count by hub
            hub_id = device.hub_id
            hub_devices[hub_id] = hub_devices.get(hub_id, 0) + 1
            
        return {
            'total_hubs': len(self.hubs),
            'total_devices': total_devices,
            'device_types': device_types,
            'hub_devices': hub_devices,
            'running': self._running
        }
        
    async def search_devices(self, query: str) -> List[IoTDevice]:
        """Search devices by name or capabilities."""
        query = query.lower()
        results = []
        
        for device in self.devices.values():
            # Search by name
            if query in device.name.lower():
                results.append(device)
                continue
                
            # Search by capabilities
            for capability in device.capabilities:
                if query in capability.value.lower():
                    results.append(device)
                    break
                    
        return results
        
    async def get_devices_by_capability(self, capability: DeviceCapability) -> List[IoTDevice]:
        """Get devices with a specific capability."""
        return [device for device in self.devices.values() if capability in device.capabilities]
        
    async def export_devices(self) -> Dict[str, Any]:
        """Export all device data."""
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'hubs': {hub_id: hub.get_status() for hub_id, hub in self.hubs.items()},
            'devices': [
                {
                    'device_id': device.device_id,
                    'name': device.name,
                    'device_type': device.device_type.value,
                    'hub_id': device.hub_id,
                    'hub_name': device.hub_name,
                    'capabilities': [cap.value for cap in device.capabilities],
                    'attributes': device.attributes,
                    'state': device.state,
                    'location': device.location,
                    'manufacturer': device.manufacturer,
                    'model': device.model,
                    'firmware_version': device.firmware_version,
                    'last_seen': device.last_seen.isoformat() if device.last_seen else None,
                    'created_at': device.created_at.isoformat(),
                    'updated_at': device.updated_at.isoformat()
                }
                for device in self.devices.values()
            ]
        }
    
    def is_running(self) -> bool:
        """Check if the manager is running."""
        return self._running
    
    async def list_hubs(self) -> Dict[str, BaseIoTHub]:
        """List all connected hubs."""
        return self.hubs
    
    async def get_all_devices(self) -> Dict[str, IoTDevice]:
        """Get all devices across all hubs."""
        return self.devices
    
    async def get_device(self, device_id: str) -> Optional[IoTDevice]:
        """Get a specific device."""
        return self.devices.get(device_id)
    
    async def control_device(self, device_id: str, command: Dict[str, Any]) -> Dict[str, Any]:
        """Control a device."""
        device = self.devices.get(device_id)
        if not device:
            return {"success": False, "error": "Device not found"}
        
        hub = self.hubs.get(device.hub_id)
        if not hub:
            return {"success": False, "error": "Hub not found"}
        
        try:
            result = await hub.set_device_state(device_id, command)
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Error controlling device {device_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get manager statistics."""
        return await self.get_manager_statistics()
    
    async def start_discovery(self):
        """Start device discovery across all hubs."""
        for hub in self.hubs.values():
            try:
                await hub.discover_devices()
            except Exception as e:
                logger.error(f"Error starting discovery for hub: {e}")
    
    async def get_recent_events(self) -> List[Dict[str, Any]]:
        """Get recent events from all hubs."""
        events = []
        for hub in self.hubs.values():
            try:
                hub_events = await hub.get_recent_events()
                events.extend(hub_events)
            except Exception as e:
                logger.error(f"Error getting events from hub: {e}")
        return events
