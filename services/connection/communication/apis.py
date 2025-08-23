"""
Device APIs
Defines device API interfaces and management.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import json
import requests
from abc import ABC, abstractmethod
import uuid

from .protocols import Message, Command, Response, MessageType, CommunicationProtocol

logger = logging.getLogger(__name__)


class DeviceAPI(ABC):
    """Abstract base class for device APIs."""
    
    def __init__(self, device_id: str, endpoint: str):
        self.device_id = device_id
        self.endpoint = endpoint
        self.is_connected = False
        self.last_heartbeat = None
        self.response_time = 0.0
        
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the device API."""
        pass
        
    @abstractmethod
    async def disconnect(self):
        """Disconnect from the device API."""
        pass
        
    @abstractmethod
    async def send_command(self, command: Command) -> Optional[Response]:
        """Send a command to the device."""
        pass
        
    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """Get device status."""
        pass
        
    @abstractmethod
    async def get_configuration(self) -> Dict[str, Any]:
        """Get device configuration."""
        pass
        
    @abstractmethod
    async def update_configuration(self, config: Dict[str, Any]) -> bool:
        """Update device configuration."""
        pass
        
    @abstractmethod
    async def send_heartbeat(self) -> bool:
        """Send heartbeat to device."""
        pass


class HTTPDeviceAPI(DeviceAPI):
    """HTTP-based device API implementation."""
    
    def __init__(self, device_id: str, endpoint: str, timeout: int = 30):
        super().__init__(device_id, endpoint)
        self.timeout = timeout
        self.session = None
        
    async def connect(self) -> bool:
        """Connect to the device API."""
        try:
            # Test connection by making a simple request
            response = await self._make_request("GET", "/status", timeout=5)
            if response and response.status_code == 200:
                self.is_connected = True
                logger.info(f"Connected to device API: {self.device_id}")
                return True
            else:
                logger.warning(f"Failed to connect to device API: {self.device_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to device API {self.device_id}: {e}")
            return False
            
    async def disconnect(self):
        """Disconnect from the device API."""
        self.is_connected = False
        logger.info(f"Disconnected from device API: {self.device_id}")
        
    async def send_command(self, command: Command) -> Optional[Response]:
        """Send a command to the device."""
        try:
            start_time = datetime.utcnow()
            
            # Prepare request data
            data = {
                'command_type': command.command_type,
                'parameters': command.parameters,
                'timeout': command.timeout
            }
            
            # Send command
            response = await self._make_request("POST", "/command", json=data, timeout=command.timeout or self.timeout)
            
            # Calculate response time
            end_time = datetime.utcnow()
            self.response_time = (end_time - start_time).total_seconds()
            
            if response and response.status_code == 200:
                response_data = response.json()
                return Response(
                    response_id=str(uuid.uuid4()),
                    command_id=command.command_id,
                    device_id=self.device_id,
                    success=response_data.get('success', False),
                    data=response_data.get('data', {}),
                    error=response_data.get('error')
                )
            else:
                logger.error(f"Failed to send command to device {self.device_id}")
                return Response(
                    response_id=str(uuid.uuid4()),
                    command_id=command.command_id,
                    device_id=self.device_id,
                    success=False,
                    error="HTTP request failed"
                )
                
        except Exception as e:
            logger.error(f"Error sending command to device {self.device_id}: {e}")
            return Response(
                response_id=str(uuid.uuid4()),
                command_id=command.command_id,
                device_id=self.device_id,
                success=False,
                error=str(e)
            )
            
    async def get_status(self) -> Dict[str, Any]:
        """Get device status."""
        try:
            response = await self._make_request("GET", "/status", timeout=10)
            if response and response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get status from device {self.device_id}")
                return {'error': 'Failed to get status'}
                
        except Exception as e:
            logger.error(f"Error getting status from device {self.device_id}: {e}")
            return {'error': str(e)}
            
    async def get_configuration(self) -> Dict[str, Any]:
        """Get device configuration."""
        try:
            response = await self._make_request("GET", "/config", timeout=10)
            if response and response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get configuration from device {self.device_id}")
                return {'error': 'Failed to get configuration'}
                
        except Exception as e:
            logger.error(f"Error getting configuration from device {self.device_id}: {e}")
            return {'error': str(e)}
            
    async def update_configuration(self, config: Dict[str, Any]) -> bool:
        """Update device configuration."""
        try:
            response = await self._make_request("PUT", "/config", json=config, timeout=30)
            if response and response.status_code == 200:
                logger.info(f"Updated configuration for device {self.device_id}")
                return True
            else:
                logger.error(f"Failed to update configuration for device {self.device_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating configuration for device {self.device_id}: {e}")
            return False
            
    async def send_heartbeat(self) -> bool:
        """Send heartbeat to device."""
        try:
            response = await self._make_request("GET", "/heartbeat", timeout=5)
            if response and response.status_code == 200:
                self.last_heartbeat = datetime.utcnow()
                return True
            else:
                logger.warning(f"Heartbeat failed for device {self.device_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending heartbeat to device {self.device_id}: {e}")
            return False
            
    async def _make_request(self, method: str, path: str, **kwargs) -> Optional[requests.Response]:
        """Make HTTP request to device."""
        try:
            url = f"{self.endpoint}{path}"
            
            # Use asyncio to run requests in thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.request(method, url, timeout=kwargs.get('timeout', self.timeout), **kwargs)
            )
            return response
            
        except Exception as e:
            logger.error(f"HTTP request failed for {url}: {e}")
            return None


class APIManager:
    """Manages device API connections and interactions."""
    
    def __init__(self):
        self._apis: Dict[str, DeviceAPI] = {}
        self._callbacks: Dict[str, List[Callable]] = {
            'command_sent': [],
            'response_received': [],
            'api_connected': [],
            'api_disconnected': [],
            'heartbeat_received': []
        }
        self._heartbeat_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start the API manager."""
        logger.info("Starting API manager")
        
        # Start heartbeat task
        self._heartbeat_task = asyncio.create_task(self._heartbeat_monitor())
        
        logger.info("API manager started")
        
    async def stop(self):
        """Stop the API manager."""
        logger.info("Stopping API manager")
        
        # Cancel heartbeat task
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            
        # Disconnect all APIs
        for api in self._apis.values():
            await api.disconnect()
            
        logger.info("API manager stopped")
        
    async def register_device_api(self, device_id: str, endpoint: str, protocol: str = "http") -> DeviceAPI:
        """Register a device API."""
        try:
            if device_id in self._apis:
                logger.warning(f"Device API {device_id} already registered")
                return self._apis[device_id]
                
            # Create appropriate API based on protocol
            if protocol.lower() in ["http", "https"]:
                api = HTTPDeviceAPI(device_id, endpoint)
            else:
                # For now, default to HTTP
                api = HTTPDeviceAPI(device_id, endpoint)
                
            # Connect to the API
            if await api.connect():
                self._apis[device_id] = api
                await self._notify_callbacks('api_connected', api)
                logger.info(f"Registered device API: {device_id}")
                return api
            else:
                logger.error(f"Failed to connect to device API: {device_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error registering device API {device_id}: {e}")
            return None
            
    async def unregister_device_api(self, device_id: str) -> bool:
        """Unregister a device API."""
        try:
            api = self._apis.get(device_id)
            if not api:
                logger.warning(f"Device API {device_id} not found")
                return False
                
            # Disconnect API
            await api.disconnect()
            
            # Remove from manager
            del self._apis[device_id]
            
            await self._notify_callbacks('api_disconnected', api)
            logger.info(f"Unregistered device API: {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error unregistering device API {device_id}: {e}")
            return False
            
    async def send_command(self, device_id: str, command: Command) -> Optional[Response]:
        """Send a command to a device."""
        try:
            api = self._apis.get(device_id)
            if not api:
                logger.error(f"Device API {device_id} not found")
                return None
                
            # Send command
            response = await api.send_command(command)
            
            # Notify callbacks
            await self._notify_callbacks('command_sent', api, command=command)
            if response:
                await self._notify_callbacks('response_received', api, response=response)
                
            return response
            
        except Exception as e:
            logger.error(f"Error sending command to device {device_id}: {e}")
            return None
            
    async def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """Get device status."""
        try:
            api = self._apis.get(device_id)
            if not api:
                logger.error(f"Device API {device_id} not found")
                return {'error': 'Device API not found'}
                
            return await api.get_status()
            
        except Exception as e:
            logger.error(f"Error getting status for device {device_id}: {e}")
            return {'error': str(e)}
            
    async def get_device_configuration(self, device_id: str) -> Dict[str, Any]:
        """Get device configuration."""
        try:
            api = self._apis.get(device_id)
            if not api:
                logger.error(f"Device API {device_id} not found")
                return {'error': 'Device API not found'}
                
            return await api.get_configuration()
            
        except Exception as e:
            logger.error(f"Error getting configuration for device {device_id}: {e}")
            return {'error': str(e)}
            
    async def update_device_configuration(self, device_id: str, config: Dict[str, Any]) -> bool:
        """Update device configuration."""
        try:
            api = self._apis.get(device_id)
            if not api:
                logger.error(f"Device API {device_id} not found")
                return False
                
            return await api.update_configuration(config)
            
        except Exception as e:
            logger.error(f"Error updating configuration for device {device_id}: {e}")
            return False
            
    async def get_connected_apis(self) -> List[str]:
        """Get list of connected device APIs."""
        return list(self._apis.keys())
        
    async def get_api_statistics(self) -> Dict[str, Any]:
        """Get API manager statistics."""
        total_apis = len(self._apis)
        connected_apis = sum(1 for api in self._apis.values() if api.is_connected)
        
        # Calculate average response time
        response_times = [api.response_time for api in self._apis.values() if api.response_time > 0]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0
        
        return {
            'total_apis': total_apis,
            'connected_apis': connected_apis,
            'disconnected_apis': total_apis - connected_apis,
            'average_response_time': avg_response_time
        }
        
    def add_callback(self, event: str, callback: Callable):
        """Add a callback for API events."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
            logger.debug(f"Added callback for event: {event}")
        else:
            logger.warning(f"Unknown event type: {event}")
            
    def remove_callback(self, event: str, callback: Callable):
        """Remove a callback for API events."""
        if event in self._callbacks and callback in self._callbacks[event]:
            self._callbacks[event].remove(callback)
            logger.debug(f"Removed callback for event: {event}")
            
    async def _notify_callbacks(self, event: str, api: DeviceAPI, **kwargs):
        """Notify all callbacks for an event."""
        if event in self._callbacks:
            for callback in self._callbacks[event]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(api, **kwargs)
                    else:
                        callback(api, **kwargs)
                except Exception as e:
                    logger.error(f"Error in callback for event {event}: {e}")
                    
    async def _heartbeat_monitor(self):
        """Monitor device heartbeats."""
        while True:
            try:
                for api in self._apis.values():
                    if api.is_connected:
                        success = await api.send_heartbeat()
                        if success:
                            await self._notify_callbacks('heartbeat_received', api)
                            
                await asyncio.sleep(30)  # Send heartbeat every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat monitor: {e}")
                await asyncio.sleep(30)
