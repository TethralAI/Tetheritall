"""
Device Registry
Manages device registration, discovery, and lifecycle operations.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
import json
import uuid

from .models import DeviceRecord, DeviceStatus, DeviceCapability
from shared.config.settings import settings
from shared.database.api_database import get_session_factory, session_scope
from shared.database.models import Device, ApiEndpoint, ScanResult

logger = logging.getLogger(__name__)


class DeviceRegistry:
    """Central device registry for managing IoT devices."""
    
    def __init__(self):
        self._devices: Dict[str, DeviceRecord] = {}
        self._session_factory = get_session_factory(settings.database_url)
        self._callbacks: Dict[str, List[Callable]] = {
            'device_registered': [],
            'device_updated': [],
            'device_removed': [],
            'device_status_changed': [],
            'device_heartbeat': []
        }
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start the device registry."""
        logger.info("Starting device registry")
        
        # Load existing devices from database
        await self._load_devices_from_database()
        
        # Start background tasks
        self._heartbeat_task = asyncio.create_task(self._heartbeat_monitor())
        self._cleanup_task = asyncio.create_task(self._cleanup_old_devices())
        
        logger.info(f"Device registry started with {len(self._devices)} devices")
        
    async def stop(self):
        """Stop the device registry."""
        logger.info("Stopping device registry")
        
        # Cancel background tasks
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
            
        # Save devices to database
        await self._save_devices_to_database()
        
        logger.info("Device registry stopped")
        
    async def register_device(self, device_info: 'DeviceInfo') -> DeviceRecord:
        """Register a new device in the registry."""
        try:
            # Check if device already exists
            if device_info.device_id in self._devices:
                logger.warning(f"Device {device_info.name} already registered")
                return self._devices[device_info.device_id]
                
            # Create device record
            device_record = DeviceRecord(
                device_id=device_info.device_id,
                name=device_info.name,
                model=device_info.model,
                manufacturer=device_info.manufacturer,
                protocol=device_info.protocol.value,
                endpoints=device_info.endpoints,
                capabilities=device_info.capabilities,
                status=DeviceStatus.REGISTERED,
                trust_level=device_info.trust_level,
                registered_by="connection_agent"
            )
            
            # Add to registry
            self._devices[device_info.device_id] = device_record
            
            # Save to database
            await self._save_device_to_database(device_record)
            
            # Notify callbacks
            await self._notify_callbacks('device_registered', device_record)
            
            logger.info(f"Registered device: {device_record.name} ({device_record.device_id})")
            return device_record
            
        except Exception as e:
            logger.error(f"Error registering device {device_info.name}: {e}")
            raise
            
    async def update_device(self, device_id: str, updates: Dict[str, Any]) -> Optional[DeviceRecord]:
        """Update device information."""
        try:
            device_record = self._devices.get(device_id)
            if not device_record:
                logger.warning(f"Device {device_id} not found in registry")
                return None
                
            # Apply updates
            for key, value in updates.items():
                if hasattr(device_record, key):
                    setattr(device_record, key, value)
                    
            # Update timestamp
            device_record.last_seen = datetime.utcnow()
            
            # Save to database
            await self._save_device_to_database(device_record)
            
            # Notify callbacks
            await self._notify_callbacks('device_updated', device_record)
            
            logger.info(f"Updated device: {device_record.name}")
            return device_record
            
        except Exception as e:
            logger.error(f"Error updating device {device_id}: {e}")
            return None
            
    async def remove_device(self, device_id: str) -> bool:
        """Remove a device from the registry."""
        try:
            device_record = self._devices.get(device_id)
            if not device_record:
                logger.warning(f"Device {device_id} not found in registry")
                return False
                
            # Remove from registry
            del self._devices[device_id]
            
            # Remove from database
            await self._remove_device_from_database(device_id)
            
            # Notify callbacks
            await self._notify_callbacks('device_removed', device_record)
            
            logger.info(f"Removed device: {device_record.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing device {device_id}: {e}")
            return False
            
    async def get_device(self, device_id: str) -> Optional[DeviceRecord]:
        """Get a device by ID."""
        return self._devices.get(device_id)
        
    async def get_devices(self, 
                         status: Optional[DeviceStatus] = None,
                         protocol: Optional[str] = None,
                         manufacturer: Optional[str] = None,
                         capability: Optional[str] = None) -> List[DeviceRecord]:
        """Get devices with optional filtering."""
        devices = list(self._devices.values())
        
        # Apply filters
        if status:
            devices = [d for d in devices if d.status == status]
        if protocol:
            devices = [d for d in devices if d.protocol == protocol]
        if manufacturer:
            devices = [d for d in devices if d.manufacturer.lower() == manufacturer.lower()]
        if capability:
            devices = [d for d in devices if capability in d.capabilities]
            
        return devices
        
    async def update_device_status(self, device_id: str, status: DeviceStatus) -> bool:
        """Update device status."""
        try:
            device_record = self._devices.get(device_id)
            if not device_record:
                logger.warning(f"Device {device_id} not found in registry")
                return False
                
            old_status = device_record.status
            device_record.update_status(status)
            
            # Save to database
            await self._save_device_to_database(device_record)
            
            # Notify callbacks if status changed
            if old_status != status:
                await self._notify_callbacks('device_status_changed', device_record, old_status=old_status)
                
            logger.info(f"Updated device {device_record.name} status: {old_status.value} -> {status.value}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating device status {device_id}: {e}")
            return False
            
    async def update_device_heartbeat(self, device_id: str) -> bool:
        """Update device heartbeat."""
        try:
            device_record = self._devices.get(device_id)
            if not device_record:
                logger.warning(f"Device {device_id} not found in registry")
                return False
                
            device_record.update_heartbeat()
            
            # Save to database
            await self._save_device_to_database(device_record)
            
            # Notify callbacks
            await self._notify_callbacks('device_heartbeat', device_record)
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating device heartbeat {device_id}: {e}")
            return False
            
    async def search_devices(self, query: str) -> List[DeviceRecord]:
        """Search devices by name, model, or manufacturer."""
        query_lower = query.lower()
        results = []
        
        for device in self._devices.values():
            if (query_lower in device.name.lower() or
                query_lower in device.model.lower() or
                query_lower in device.manufacturer.lower()):
                results.append(device)
                
        return results
        
    async def get_device_statistics(self) -> Dict[str, Any]:
        """Get device registry statistics."""
        total_devices = len(self._devices)
        online_devices = sum(1 for d in self._devices.values() if d.is_online())
        trusted_devices = sum(1 for d in self._devices.values() if d.is_trusted())
        
        # Protocol distribution
        protocol_counts = {}
        for device in self._devices.values():
            protocol_counts[device.protocol] = protocol_counts.get(device.protocol, 0) + 1
            
        # Manufacturer distribution
        manufacturer_counts = {}
        for device in self._devices.values():
            manufacturer_counts[device.manufacturer] = manufacturer_counts.get(device.manufacturer, 0) + 1
            
        # Status distribution
        status_counts = {}
        for device in self._devices.values():
            status_counts[device.status.value] = status_counts.get(device.status.value, 0) + 1
            
        return {
            'total_devices': total_devices,
            'online_devices': online_devices,
            'offline_devices': total_devices - online_devices,
            'trusted_devices': trusted_devices,
            'protocol_distribution': protocol_counts,
            'manufacturer_distribution': manufacturer_counts,
            'status_distribution': status_counts,
            'average_trust_level': sum(d.trust_level for d in self._devices.values()) / total_devices if total_devices > 0 else 0.0
        }
        
    def add_callback(self, event: str, callback: Callable):
        """Add a callback for registry events."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
            logger.debug(f"Added callback for event: {event}")
        else:
            logger.warning(f"Unknown event type: {event}")
            
    def remove_callback(self, event: str, callback: Callable):
        """Remove a callback for registry events."""
        if event in self._callbacks and callback in self._callbacks[event]:
            self._callbacks[event].remove(callback)
            logger.debug(f"Removed callback for event: {event}")
            
    async def _notify_callbacks(self, event: str, device_record: DeviceRecord, **kwargs):
        """Notify all callbacks for an event."""
        if event in self._callbacks:
            for callback in self._callbacks[event]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(device_record, **kwargs)
                    else:
                        callback(device_record, **kwargs)
                except Exception as e:
                    logger.error(f"Error in callback for event {event}: {e}")
                    
    async def _load_devices_from_database(self):
        """Load devices from database."""
        try:
            with session_scope(self._session_factory) as session:
                devices = session.query(Device).all()
                
                for device in devices:
                    # Get device endpoints
                    endpoints = session.query(ApiEndpoint).filter_by(device_id=device.id).all()
                    endpoint_urls = [ep.endpoint_url for ep in endpoints]
                    
                    # Create device record
                    device_record = DeviceRecord(
                        device_id=f"db_{device.id}",
                        name=f"Device {device.id}",
                        model=device.model or "Unknown",
                        manufacturer=device.manufacturer or "Unknown",
                        protocol="api",  # Default for database devices
                        endpoints=endpoint_urls,
                        capabilities=["api"],
                        status=DeviceStatus.REGISTERED,
                        firmware_version=device.firmware_version,
                        registered_at=device.created_at
                    )
                    
                    self._devices[device_record.device_id] = device_record
                    
            logger.info(f"Loaded {len(devices)} devices from database")
            
        except Exception as e:
            logger.error(f"Error loading devices from database: {e}")
            
    async def _save_device_to_database(self, device_record: DeviceRecord):
        """Save device to database."""
        try:
            with session_scope(self._session_factory) as session:
                # Check if device exists
                existing_device = session.query(Device).filter_by(
                    model=device_record.model,
                    manufacturer=device_record.manufacturer
                ).first()
                
                if existing_device:
                    # Update existing device
                    existing_device.firmware_version = device_record.firmware_version
                    session.commit()
                else:
                    # Create new device
                    device = Device(
                        model=device_record.model,
                        manufacturer=device_record.manufacturer,
                        firmware_version=device_record.firmware_version
                    )
                    session.add(device)
                    session.commit()
                    
                    # Add endpoints
                    for endpoint_url in device_record.endpoints:
                        api_endpoint = ApiEndpoint(
                            device_id=device.id,
                            endpoint_url=endpoint_url,
                            method="GET",
                            authentication_type="unknown"
                        )
                        session.add(api_endpoint)
                    session.commit()
                    
        except Exception as e:
            logger.error(f"Error saving device to database: {e}")
            
    async def _remove_device_from_database(self, device_id: str):
        """Remove device from database."""
        try:
            # This would remove the device from the database
            # For now, just log the action
            logger.info(f"Removing device {device_id} from database")
            
        except Exception as e:
            logger.error(f"Error removing device from database: {e}")
            
    async def _save_devices_to_database(self):
        """Save all devices to database."""
        try:
            for device_record in self._devices.values():
                await self._save_device_to_database(device_record)
            logger.info("Saved all devices to database")
            
        except Exception as e:
            logger.error(f"Error saving devices to database: {e}")
            
    async def _heartbeat_monitor(self):
        """Monitor device heartbeats and mark offline devices."""
        while True:
            try:
                current_time = datetime.utcnow()
                offline_threshold = timedelta(minutes=5)  # 5 minutes without heartbeat
                
                for device_record in self._devices.values():
                    if (device_record.last_heartbeat and 
                        current_time - device_record.last_heartbeat > offline_threshold and
                        device_record.status in [DeviceStatus.ONLINE, DeviceStatus.CONNECTED, DeviceStatus.AUTHENTICATED, DeviceStatus.TRUSTED]):
                        
                        await self.update_device_status(device_record.device_id, DeviceStatus.OFFLINE)
                        
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat monitor: {e}")
                await asyncio.sleep(60)
                
    async def _cleanup_old_devices(self):
        """Clean up old offline devices."""
        while True:
            try:
                current_time = datetime.utcnow()
                cleanup_threshold = timedelta(days=30)  # 30 days offline
                
                devices_to_remove = []
                for device_record in self._devices.values():
                    if (device_record.status == DeviceStatus.OFFLINE and
                        device_record.last_seen and
                        current_time - device_record.last_seen > cleanup_threshold):
                        
                        devices_to_remove.append(device_record.device_id)
                        
                for device_id in devices_to_remove:
                    await self.remove_device(device_id)
                    
                if devices_to_remove:
                    logger.info(f"Cleaned up {len(devices_to_remove)} old offline devices")
                    
                await asyncio.sleep(3600)  # Check every hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(3600)
