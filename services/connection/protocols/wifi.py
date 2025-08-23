"""
WiFi Protocol Handler
Handles discovery and connection to WiFi-enabled IoT devices.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import subprocess
import re
import socket
import requests
from urllib.parse import urljoin

from ..agent import DeviceInfo, ConnectionProtocol

logger = logging.getLogger(__name__)


class WiFiHandler:
    """Handler for WiFi-enabled IoT devices."""
    
    def __init__(self):
        self._connected_devices: Dict[str, DeviceInfo] = {}
        self._scan_results: List[Dict[str, Any]] = []
        
    async def discover(self) -> List[DeviceInfo]:
        """Discover WiFi-enabled IoT devices on the network."""
        logger.info("Starting WiFi device discovery")
        
        discovered_devices = []
        
        try:
            # Method 1: Network scan for common IoT device ports
            network_devices = await self._scan_network()
            
            # Method 2: Look for common IoT device patterns
            iot_devices = await self._identify_iot_devices(network_devices)
            
            # Method 3: Check for device APIs
            for device in iot_devices:
                device_info = await self._probe_device_api(device)
                if device_info:
                    discovered_devices.append(device_info)
                    
            logger.info(f"WiFi discovery found {len(discovered_devices)} IoT devices")
            
        except Exception as e:
            logger.error(f"Error during WiFi discovery: {e}")
            
        return discovered_devices
        
    async def connect(self, device_info: DeviceInfo) -> bool:
        """Connect to a WiFi device."""
        try:
            logger.info(f"Attempting to connect to WiFi device: {device_info.name}")
            
            # Check if device is reachable
            if not await self._ping_device(device_info.device_id):
                logger.error(f"Device {device_info.name} is not reachable")
                return False
                
            # Attempt to establish connection
            connection_success = await self._establish_connection(device_info)
            
            if connection_success:
                self._connected_devices[device_info.device_id] = device_info
                logger.info(f"Successfully connected to WiFi device: {device_info.name}")
                return True
            else:
                logger.error(f"Failed to connect to WiFi device: {device_info.name}")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to WiFi device {device_info.name}: {e}")
            return False
            
    async def authenticate(self, device_info: DeviceInfo) -> bool:
        """Authenticate with a WiFi device."""
        try:
            logger.info(f"Authenticating with WiFi device: {device_info.name}")
            
            # Try common authentication methods
            auth_methods = [
                self._try_basic_auth,
                self._try_token_auth,
                self._try_certificate_auth,
                self._try_no_auth
            ]
            
            for auth_method in auth_methods:
                if await auth_method(device_info):
                    logger.info(f"Successfully authenticated with {device_info.name}")
                    return True
                    
            logger.error(f"Failed to authenticate with {device_info.name}")
            return False
            
        except Exception as e:
            logger.error(f"Error authenticating with WiFi device {device_info.name}: {e}")
            return False
            
    async def disconnect(self, device_info: DeviceInfo):
        """Disconnect from a WiFi device."""
        try:
            if device_info.device_id in self._connected_devices:
                del self._connected_devices[device_info.device_id]
                logger.info(f"Disconnected from WiFi device: {device_info.name}")
        except Exception as e:
            logger.error(f"Error disconnecting from WiFi device {device_info.name}: {e}")
            
    async def _scan_network(self) -> List[Dict[str, Any]]:
        """Scan the network for devices."""
        devices = []
        
        try:
            # Get local network range
            local_ip = self._get_local_ip()
            network_range = self._get_network_range(local_ip)
            
            # Scan common IoT ports
            common_ports = [80, 443, 8080, 8883, 1883, 5683, 5353, 1900]
            
            for ip in network_range:
                for port in common_ports:
                    if await self._check_port(ip, port):
                        devices.append({
                            'ip': ip,
                            'port': port,
                            'protocol': 'http' if port in [80, 443, 8080] else 'unknown'
                        })
                        
        except Exception as e:
            logger.error(f"Error scanning network: {e}")
            
        return devices
        
    async def _identify_iot_devices(self, network_devices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify which network devices are likely IoT devices."""
        iot_devices = []
        
        for device in network_devices:
            try:
                # Check for common IoT device signatures
                if await self._has_iot_signature(device):
                    iot_devices.append(device)
                    
            except Exception as e:
                logger.debug(f"Error checking device {device.get('ip')}: {e}")
                
        return iot_devices
        
    async def _probe_device_api(self, device: Dict[str, Any]) -> Optional[DeviceInfo]:
        """Probe device for API endpoints and device information."""
        try:
            ip = device['ip']
            port = device['port']
            
            # Try common IoT API endpoints
            api_endpoints = [
                '/api/v1/info',
                '/device/info',
                '/status',
                '/info',
                '/api/device',
                '/'
            ]
            
            device_info = None
            
            for endpoint in api_endpoints:
                try:
                    url = f"http://{ip}:{port}{endpoint}"
                    response = await self._make_request(url, timeout=2)
                    
                    if response and response.status_code == 200:
                        device_info = self._parse_device_info(response.json(), ip, port)
                        break
                        
                except Exception as e:
                    logger.debug(f"Failed to probe {endpoint} on {ip}:{port}: {e}")
                    
            # If no API found, create basic device info
            if not device_info:
                device_info = DeviceInfo(
                    device_id=f"wifi_{ip}_{port}",
                    name=f"Unknown Device ({ip})",
                    model="Unknown",
                    manufacturer="Unknown",
                    protocol=ConnectionProtocol.WIFI,
                    capabilities=["network"],
                    endpoints=[f"http://{ip}:{port}"]
                )
                
            return device_info
            
        except Exception as e:
            logger.error(f"Error probing device API: {e}")
            return None
            
    async def _ping_device(self, device_id: str) -> bool:
        """Check if device is reachable."""
        try:
            # Extract IP from device_id
            if device_id.startswith("wifi_"):
                ip = device_id.split("_")[1]
                
                # Use ping to check reachability
                result = await asyncio.create_subprocess_exec(
                    'ping', '-n', '1', '-w', '1000', ip,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                await result.wait()
                return result.returncode == 0
                
        except Exception as e:
            logger.error(f"Error pinging device: {e}")
            
        return False
        
    async def _establish_connection(self, device_info: DeviceInfo) -> bool:
        """Establish connection to device."""
        try:
            # For WiFi devices, connection is typically just network reachability
            # and successful API communication
            if device_info.endpoints:
                endpoint = device_info.endpoints[0]
                response = await self._make_request(endpoint, timeout=5)
                return response is not None and response.status_code < 500
                
        except Exception as e:
            logger.error(f"Error establishing connection: {e}")
            
        return False
        
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
                        url = urljoin(endpoint, token_endpoint)
                        response = await self._make_request(url, timeout=3)
                        if response and response.status_code == 200:
                            return True
                    except:
                        continue
                        
        except Exception as e:
            logger.debug(f"Token auth failed: {e}")
            
        return False
        
    async def _try_certificate_auth(self, device_info: DeviceInfo) -> bool:
        """Try certificate-based authentication."""
        # This would require certificate files and is more complex
        # For now, return False as it's not commonly used in basic IoT devices
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
            
    async def _check_port(self, ip: str, port: int) -> bool:
        """Check if port is open on device."""
        try:
            # Use asyncio to run socket connection in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._socket_connect(ip, port)
            )
            return result
        except Exception as e:
            logger.debug(f"Port check failed for {ip}:{port}: {e}")
            return False
            
    def _socket_connect(self, ip: str, port: int) -> bool:
        """Synchronous socket connection check."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except:
            return False
            
    async def _has_iot_signature(self, device: Dict[str, Any]) -> bool:
        """Check if device has IoT device signatures."""
        try:
            ip = device['ip']
            port = device['port']
            
            # Check for common IoT device headers
            url = f"http://{ip}:{port}"
            response = await self._make_request(url, timeout=2)
            
            if response:
                headers = response.headers
                
                # Look for IoT device indicators in headers
                iot_indicators = [
                    'x-powered-by',
                    'server',
                    'www-authenticate',
                    'content-type'
                ]
                
                for indicator in iot_indicators:
                    if indicator in headers:
                        header_value = headers[indicator].lower()
                        if any(keyword in header_value for keyword in ['iot', 'device', 'sensor', 'smart']):
                            return True
                            
                # Check response content for IoT indicators
                if 'text/html' in headers.get('content-type', ''):
                    content = response.text.lower()
                    iot_keywords = ['iot', 'device', 'sensor', 'smart', 'home', 'automation']
                    if any(keyword in content for keyword in iot_keywords):
                        return True
                        
        except Exception as e:
            logger.debug(f"Error checking IoT signature: {e}")
            
        return False
        
    def _parse_device_info(self, data: Dict[str, Any], ip: str, port: int) -> DeviceInfo:
        """Parse device information from API response."""
        try:
            # Extract device information from common API response formats
            name = data.get('name', data.get('device_name', data.get('hostname', f"Device ({ip})")))
            model = data.get('model', data.get('device_model', 'Unknown'))
            manufacturer = data.get('manufacturer', data.get('vendor', 'Unknown'))
            
            # Extract capabilities
            capabilities = data.get('capabilities', [])
            if not capabilities:
                capabilities = ['network']  # Default capability
                
            # Extract endpoints
            endpoints = data.get('endpoints', [])
            if not endpoints:
                endpoints = [f"http://{ip}:{port}"]
                
            return DeviceInfo(
                device_id=f"wifi_{ip}_{port}",
                name=name,
                model=model,
                manufacturer=manufacturer,
                protocol=ConnectionProtocol.WIFI,
                capabilities=capabilities,
                endpoints=endpoints
            )
            
        except Exception as e:
            logger.error(f"Error parsing device info: {e}")
            # Return basic device info
            return DeviceInfo(
                device_id=f"wifi_{ip}_{port}",
                name=f"Unknown Device ({ip})",
                model="Unknown",
                manufacturer="Unknown",
                protocol=ConnectionProtocol.WIFI,
                capabilities=["network"],
                endpoints=[f"http://{ip}:{port}"]
            )
            
    def _get_local_ip(self) -> str:
        """Get local IP address."""
        try:
            # Create a socket to get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return "192.168.1.1"  # Default fallback
            
    def _get_network_range(self, local_ip: str) -> List[str]:
        """Get network range for scanning."""
        try:
            # Extract network prefix
            parts = local_ip.split('.')
            network_prefix = '.'.join(parts[:3])
            
            # Generate IP range (1-254)
            ips = []
            for i in range(1, 255):
                ips.append(f"{network_prefix}.{i}")
                
            return ips
        except:
            return []
