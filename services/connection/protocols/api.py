"""
API Protocol Handler
Handles discovery and connection to API-based IoT devices.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import requests
import json

from ..agent import DeviceInfo, ConnectionProtocol

logger = logging.getLogger(__name__)


class APIHandler:
    """Handler for API-based IoT devices."""
    
    def __init__(self):
        self._connected_devices: Dict[str, DeviceInfo] = {}
        self._scan_results: List[Dict[str, Any]] = []
        
    async def discover(self) -> List[DeviceInfo]:
        """Discover API-based IoT devices."""
        logger.info("Starting API device discovery")
        
        discovered_devices = []
        
        try:
            # Common IoT API endpoints to check
            api_endpoints = [
                "http://192.168.1.100:8080",  # Example local device
                "http://192.168.1.101:8080",  # Example local device
                "http://192.168.1.102:8080",  # Example local device
            ]
            
            for endpoint in api_endpoints:
                device_info = await self._probe_api_endpoint(endpoint)
                if device_info:
                    discovered_devices.append(device_info)
                    
            logger.info(f"API discovery found {len(discovered_devices)} devices")
            
        except Exception as e:
            logger.error(f"Error during API discovery: {e}")
            
        return discovered_devices
        
    async def connect(self, device_info: DeviceInfo) -> bool:
        """Connect to an API device."""
        try:
            logger.info(f"Attempting to connect to API device: {device_info.name}")
            
            if not device_info.endpoints:
                logger.error(f"No endpoints available for device {device_info.name}")
                return False
                
            # Test connection to primary endpoint
            endpoint = device_info.endpoints[0]
            response = await self._make_request(endpoint, timeout=5)
            
            if response and response.status_code < 500:
                self._connected_devices[device_info.device_id] = device_info
                logger.info(f"Successfully connected to API device: {device_info.name}")
                return True
            else:
                logger.error(f"Failed to connect to API device: {device_info.name}")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to API device {device_info.name}: {e}")
            return False
            
    async def authenticate(self, device_info: DeviceInfo) -> bool:
        """Authenticate with an API device."""
        try:
            logger.info(f"Authenticating with API device: {device_info.name}")
            
            # Try common authentication methods
            auth_methods = [
                self._try_basic_auth,
                self._try_token_auth,
                self._try_api_key_auth,
                self._try_no_auth
            ]
            
            for auth_method in auth_methods:
                if await auth_method(device_info):
                    logger.info(f"Successfully authenticated with {device_info.name}")
                    return True
                    
            logger.error(f"Failed to authenticate with {device_info.name}")
            return False
            
        except Exception as e:
            logger.error(f"Error authenticating with API device {device_info.name}: {e}")
            return False
            
    async def disconnect(self, device_info: DeviceInfo):
        """Disconnect from an API device."""
        try:
            if device_info.device_id in self._connected_devices:
                del self._connected_devices[device_info.device_id]
                logger.info(f"Disconnected from API device: {device_info.name}")
        except Exception as e:
            logger.error(f"Error disconnecting from API device {device_info.name}: {e}")
            
    async def _probe_api_endpoint(self, endpoint: str) -> Optional[DeviceInfo]:
        """Probe an API endpoint for device information."""
        try:
            # Try to get device information from common endpoints
            info_endpoints = [
                '/api/v1/info',
                '/device/info',
                '/status',
                '/info',
                '/api/device',
                '/'
            ]
            
            for info_endpoint in info_endpoints:
                try:
                    url = f"{endpoint}{info_endpoint}"
                    response = await self._make_request(url, timeout=2)
                    
                    if response and response.status_code == 200:
                        data = response.json()
                        return self._parse_device_info(data, endpoint)
                        
                except Exception as e:
                    logger.debug(f"Failed to probe {info_endpoint} on {endpoint}: {e}")
                    
            # If no info endpoint found, create basic device info
            return DeviceInfo(
                device_id=f"api_{endpoint.replace('://', '_').replace(':', '_').replace('/', '_')}",
                name=f"API Device ({endpoint})",
                model="Unknown",
                manufacturer="Unknown",
                protocol=ConnectionProtocol.API,
                capabilities=["api"],
                endpoints=[endpoint]
            )
            
        except Exception as e:
            logger.error(f"Error probing API endpoint {endpoint}: {e}")
            return None
            
    async def _try_basic_auth(self, device_info: DeviceInfo) -> bool:
        """Try basic authentication."""
        try:
            if device_info.endpoints:
                endpoint = device_info.endpoints[0]
                
                # Try common credentials
                credentials = [
                    ('admin', 'admin'),
                    ('admin', 'password'),
                    ('root', 'root'),
                    ('user', 'user'),
                    ('', '')  # No credentials
                ]
                
                for username, password in credentials:
                    try:
                        response = await self._make_request(
                            endpoint, 
                            auth=(username, password),
                            timeout=3
                        )
                        if response and response.status_code == 200:
                            return True
                    except:
                        continue
                        
        except Exception as e:
            logger.debug(f"Basic auth failed: {e}")
            
        return False
        
    async def _try_token_auth(self, device_info: DeviceInfo) -> bool:
        """Try token-based authentication."""
        try:
            if device_info.endpoints:
                endpoint = device_info.endpoints[0]
                
                # Try common token endpoints
                token_endpoints = [
                    '/api/token',
                    '/auth/token',
                    '/login',
                    '/api/login'
                ]
                
                for token_endpoint in token_endpoints:
                    try:
                        url = f"{endpoint}{token_endpoint}"
                        response = await self._make_request(url, timeout=3)
                        if response and response.status_code == 200:
                            return True
                    except:
                        continue
                        
        except Exception as e:
            logger.debug(f"Token auth failed: {e}")
            
        return False
        
    async def _try_api_key_auth(self, device_info: DeviceInfo) -> bool:
        """Try API key authentication."""
        try:
            if device_info.endpoints:
                endpoint = device_info.endpoints[0]
                
                # Try common API key headers
                api_key_headers = [
                    {'X-API-Key': 'test'},
                    {'Authorization': 'Bearer test'},
                    {'X-Auth-Token': 'test'},
                    {'Api-Key': 'test'}
                ]
                
                for headers in api_key_headers:
                    try:
                        response = await self._make_request(
                            endpoint,
                            headers=headers,
                            timeout=3
                        )
                        if response and response.status_code == 200:
                            return True
                    except:
                        continue
                        
        except Exception as e:
            logger.debug(f"API key auth failed: {e}")
            
        return False
        
    async def _try_no_auth(self, device_info: DeviceInfo) -> bool:
        """Try connecting without authentication."""
        try:
            if device_info.endpoints:
                endpoint = device_info.endpoints[0]
                response = await self._make_request(endpoint, timeout=3)
                return response is not None and response.status_code == 200
                
        except Exception as e:
            logger.debug(f"No auth failed: {e}")
            
        return False
        
    async def _make_request(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Make HTTP request with timeout."""
        try:
            # Use asyncio to run requests in thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.get(url, **kwargs)
            )
            return response
        except Exception as e:
            logger.debug(f"Request failed for {url}: {e}")
            return None
            
    def _parse_device_info(self, data: Dict[str, Any], endpoint: str) -> DeviceInfo:
        """Parse device information from API response."""
        try:
            # Extract device information from common API response formats
            name = data.get('name', data.get('device_name', data.get('hostname', f"API Device ({endpoint})")))
            model = data.get('model', data.get('device_model', 'Unknown'))
            manufacturer = data.get('manufacturer', data.get('vendor', 'Unknown'))
            
            # Extract capabilities
            capabilities = data.get('capabilities', [])
            if not capabilities:
                capabilities = ['api']  # Default capability
                
            # Extract endpoints
            endpoints = data.get('endpoints', [])
            if not endpoints:
                endpoints = [endpoint]
                
            return DeviceInfo(
                device_id=f"api_{endpoint.replace('://', '_').replace(':', '_').replace('/', '_')}",
                name=name,
                model=model,
                manufacturer=manufacturer,
                protocol=ConnectionProtocol.API,
                capabilities=capabilities,
                endpoints=endpoints
            )
            
        except Exception as e:
            logger.error(f"Error parsing device info: {e}")
            # Return basic device info
            return DeviceInfo(
                device_id=f"api_{endpoint.replace('://', '_').replace(':', '_').replace('/', '_')}",
                name=f"API Device ({endpoint})",
                model="Unknown",
                manufacturer="Unknown",
                protocol=ConnectionProtocol.API,
                capabilities=["api"],
                endpoints=[endpoint]
            )
