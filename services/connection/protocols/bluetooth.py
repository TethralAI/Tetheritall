"""
Bluetooth Protocol Handler
Handles discovery and connection to Bluetooth-enabled IoT devices.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import subprocess
import re

from ..agent import DeviceInfo, ConnectionProtocol

logger = logging.getLogger(__name__)


class BluetoothHandler:
    """Handler for Bluetooth-enabled IoT devices."""
    
    def __init__(self):
        self._connected_devices: Dict[str, DeviceInfo] = {}
        self._scan_results: List[Dict[str, Any]] = []
        
    async def discover(self) -> List[DeviceInfo]:
        """Discover Bluetooth-enabled IoT devices."""
        logger.info("Starting Bluetooth device discovery")
        
        discovered_devices = []
        
        try:
            # Method 1: Use system Bluetooth scanning
            bluetooth_devices = await self._scan_bluetooth_devices()
            
            # Method 2: Filter for IoT devices
            iot_devices = await self._filter_iot_devices(bluetooth_devices)
            
            # Method 3: Create device info objects
            for device in iot_devices:
                device_info = self._create_device_info(device)
                if device_info:
                    discovered_devices.append(device_info)
                    
            logger.info(f"Bluetooth discovery found {len(discovered_devices)} IoT devices")
            
        except Exception as e:
            logger.error(f"Error during Bluetooth discovery: {e}")
            
        return discovered_devices
        
    async def connect(self, device_info: DeviceInfo) -> bool:
        """Connect to a Bluetooth device."""
        try:
            logger.info(f"Attempting to connect to Bluetooth device: {device_info.name}")
            
            # Extract MAC address from device_id
            mac_address = self._extract_mac_address(device_info.device_id)
            if not mac_address:
                logger.error(f"Invalid device ID format: {device_info.device_id}")
                return False
                
            # Attempt to pair and connect
            connection_success = await self._establish_bluetooth_connection(mac_address)
            
            if connection_success:
                self._connected_devices[device_info.device_id] = device_info
                logger.info(f"Successfully connected to Bluetooth device: {device_info.name}")
                return True
            else:
                logger.error(f"Failed to connect to Bluetooth device: {device_info.name}")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to Bluetooth device {device_info.name}: {e}")
            return False
            
    async def authenticate(self, device_info: DeviceInfo) -> bool:
        """Authenticate with a Bluetooth device."""
        try:
            logger.info(f"Authenticating with Bluetooth device: {device_info.name}")
            
            # For Bluetooth devices, authentication is typically handled during pairing
            # Check if device is still connected and responsive
            mac_address = self._extract_mac_address(device_info.device_id)
            if not mac_address:
                return False
                
            # Check device status
            is_connected = await self._check_bluetooth_connection(mac_address)
            
            if is_connected:
                logger.info(f"Successfully authenticated with {device_info.name}")
                return True
            else:
                logger.error(f"Failed to authenticate with {device_info.name}")
                return False
                
        except Exception as e:
            logger.error(f"Error authenticating with Bluetooth device {device_info.name}: {e}")
            return False
            
    async def disconnect(self, device_info: DeviceInfo):
        """Disconnect from a Bluetooth device."""
        try:
            if device_info.device_id in self._connected_devices:
                mac_address = self._extract_mac_address(device_info.device_id)
                if mac_address:
                    await self._disconnect_bluetooth_device(mac_address)
                del self._connected_devices[device_info.device_id]
                logger.info(f"Disconnected from Bluetooth device: {device_info.name}")
        except Exception as e:
            logger.error(f"Error disconnecting from Bluetooth device {device_info.name}: {e}")
            
    async def _scan_bluetooth_devices(self) -> List[Dict[str, Any]]:
        """Scan for Bluetooth devices using system commands."""
        devices = []
        
        try:
            # Use Windows Bluetooth command (if available)
            if self._is_windows():
                devices = await self._scan_bluetooth_windows()
            else:
                # Use Linux/Unix Bluetooth commands
                devices = await self._scan_bluetooth_linux()
                
        except Exception as e:
            logger.error(f"Error scanning Bluetooth devices: {e}")
            
        return devices
        
    async def _scan_bluetooth_windows(self) -> List[Dict[str, Any]]:
        """Scan Bluetooth devices on Windows."""
        devices = []
        
        try:
            # Use PowerShell to scan for Bluetooth devices
            cmd = [
                'powershell',
                '-Command',
                'Get-PnpDevice | Where-Object {$_.Class -eq "Bluetooth"} | Select-Object FriendlyName, InstanceId, Status'
            ]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                output = stdout.decode('utf-8')
                devices = self._parse_windows_bluetooth_output(output)
                
        except Exception as e:
            logger.error(f"Error scanning Windows Bluetooth: {e}")
            
        return devices
        
    async def _scan_bluetooth_linux(self) -> List[Dict[str, Any]]:
        """Scan Bluetooth devices on Linux/Unix."""
        devices = []
        
        try:
            # Use hcitool to scan for Bluetooth devices
            cmd = ['hcitool', 'scan']
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                output = stdout.decode('utf-8')
                devices = self._parse_linux_bluetooth_output(output)
                
        except Exception as e:
            logger.error(f"Error scanning Linux Bluetooth: {e}")
            
        return devices
        
    def _parse_windows_bluetooth_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse Windows Bluetooth scan output."""
        devices = []
        
        try:
            lines = output.strip().split('\n')
            
            for line in lines:
                if line.strip() and not line.startswith('---'):
                    # Parse PowerShell output format
                    parts = line.split()
                    if len(parts) >= 2:
                        name = ' '.join(parts[:-2])  # Everything except last two parts
                        instance_id = parts[-2]
                        status = parts[-1]
                        
                        # Extract MAC address from instance ID if possible
                        mac_address = self._extract_mac_from_instance_id(instance_id)
                        
                        devices.append({
                            'name': name,
                            'mac_address': mac_address,
                            'status': status,
                            'instance_id': instance_id
                        })
                        
        except Exception as e:
            logger.error(f"Error parsing Windows Bluetooth output: {e}")
            
        return devices
        
    def _parse_linux_bluetooth_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse Linux Bluetooth scan output."""
        devices = []
        
        try:
            lines = output.strip().split('\n')
            
            for line in lines:
                if line.strip() and not line.startswith('Scanning'):
                    # Parse hcitool scan output format
                    # Format: MAC Address\tDevice Name
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        mac_address = parts[0].strip()
                        name = parts[1].strip()
                        
                        devices.append({
                            'name': name,
                            'mac_address': mac_address,
                            'status': 'OK'
                        })
                        
        except Exception as e:
            logger.error(f"Error parsing Linux Bluetooth output: {e}")
            
        return devices
        
    async def _filter_iot_devices(self, bluetooth_devices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter Bluetooth devices to identify IoT devices."""
        iot_devices = []
        
        for device in bluetooth_devices:
            try:
                name = device.get('name', '').lower()
                
                # Look for IoT device keywords in name
                iot_keywords = [
                    'sensor', 'thermostat', 'lock', 'camera', 'light', 'bulb',
                    'switch', 'outlet', 'plug', 'speaker', 'headphone', 'watch',
                    'tracker', 'scale', 'thermometer', 'monitor', 'hub', 'bridge',
                    'gateway', 'beacon', 'tag', 'key', 'remote', 'controller'
                ]
                
                if any(keyword in name for keyword in iot_keywords):
                    iot_devices.append(device)
                    
            except Exception as e:
                logger.debug(f"Error filtering device {device.get('name')}: {e}")
                
        return iot_devices
        
    def _create_device_info(self, device: Dict[str, Any]) -> Optional[DeviceInfo]:
        """Create DeviceInfo object from Bluetooth device data."""
        try:
            name = device.get('name', 'Unknown Bluetooth Device')
            mac_address = device.get('mac_address', '')
            
            if not mac_address:
                logger.warning(f"No MAC address for device: {name}")
                return None
                
            # Determine device type based on name
            device_type = self._determine_device_type(name)
            
            # Create capabilities based on device type
            capabilities = self._get_device_capabilities(device_type)
            
            return DeviceInfo(
                device_id=f"bluetooth_{mac_address.replace(':', '_')}",
                name=name,
                model=device_type,
                manufacturer=self._determine_manufacturer(name),
                protocol=ConnectionProtocol.BLUETOOTH,
                capabilities=capabilities,
                endpoints=[f"bluetooth://{mac_address}"]
            )
            
        except Exception as e:
            logger.error(f"Error creating device info: {e}")
            return None
            
    def _determine_device_type(self, name: str) -> str:
        """Determine device type based on name."""
        name_lower = name.lower()
        
        if any(keyword in name_lower for keyword in ['thermostat', 'temp']):
            return 'Thermostat'
        elif any(keyword in name_lower for keyword in ['lock', 'deadbolt']):
            return 'Smart Lock'
        elif any(keyword in name_lower for keyword in ['camera', 'cam']):
            return 'Security Camera'
        elif any(keyword in name_lower for keyword in ['light', 'bulb', 'lamp']):
            return 'Smart Light'
        elif any(keyword in name_lower for keyword in ['switch', 'outlet', 'plug']):
            return 'Smart Switch'
        elif any(keyword in name_lower for keyword in ['speaker', 'sound']):
            return 'Smart Speaker'
        elif any(keyword in name_lower for keyword in ['watch', 'band', 'tracker']):
            return 'Wearable'
        elif any(keyword in name_lower for keyword in ['scale', 'weight']):
            return 'Smart Scale'
        elif any(keyword in name_lower for keyword in ['hub', 'bridge', 'gateway']):
            return 'Hub/Gateway'
        else:
            return 'IoT Device'
            
    def _determine_manufacturer(self, name: str) -> str:
        """Determine manufacturer based on device name."""
        name_lower = name.lower()
        
        # Common IoT manufacturers
        manufacturers = {
            'philips': 'Philips',
            'hue': 'Philips',
            'nest': 'Google',
            'ring': 'Ring',
            'amazon': 'Amazon',
            'echo': 'Amazon',
            'alexa': 'Amazon',
            'apple': 'Apple',
            'homekit': 'Apple',
            'samsung': 'Samsung',
            'smartthings': 'Samsung',
            'xiaomi': 'Xiaomi',
            'mi': 'Xiaomi',
            'wyze': 'Wyze',
            'tuya': 'Tuya',
            'smartlife': 'Tuya',
            'ikea': 'IKEA',
            'tradfri': 'IKEA',
            'sonos': 'Sonos',
            'bose': 'Bose',
            'fitbit': 'Fitbit',
            'garmin': 'Garmin',
            'withings': 'Withings',
            'august': 'August',
            'schlage': 'Schlage',
            'kwikset': 'Kwikset',
            'yale': 'Yale',
            'ecobee': 'Ecobee',
            'honeywell': 'Honeywell'
        }
        
        for keyword, manufacturer in manufacturers.items():
            if keyword in name_lower:
                return manufacturer
                
        return 'Unknown'
        
    def _get_device_capabilities(self, device_type: str) -> List[str]:
        """Get device capabilities based on device type."""
        capabilities_map = {
            'Thermostat': ['temperature_control', 'climate'],
            'Smart Lock': ['access_control', 'security'],
            'Security Camera': ['video', 'security', 'motion_detection'],
            'Smart Light': ['lighting', 'dimmable'],
            'Smart Switch': ['power_control', 'energy_monitoring'],
            'Smart Speaker': ['audio', 'voice_assistant'],
            'Wearable': ['health_monitoring', 'activity_tracking'],
            'Smart Scale': ['weight_measurement', 'health_monitoring'],
            'Hub/Gateway': ['protocol_bridge', 'central_control']
        }
        
        return capabilities_map.get(device_type, ['bluetooth'])
        
    async def _establish_bluetooth_connection(self, mac_address: str) -> bool:
        """Establish Bluetooth connection to device."""
        try:
            # This would use system Bluetooth APIs
            # For now, simulate connection success
            logger.info(f"Establishing Bluetooth connection to {mac_address}")
            
            # In a real implementation, this would:
            # 1. Check if device is paired
            # 2. Pair if necessary
            # 3. Connect to device
            # 4. Verify connection
            
            # Simulate connection process
            await asyncio.sleep(1)
            
            # For now, assume connection is successful
            return True
            
        except Exception as e:
            logger.error(f"Error establishing Bluetooth connection: {e}")
            return False
            
    async def _check_bluetooth_connection(self, mac_address: str) -> bool:
        """Check if Bluetooth device is connected."""
        try:
            # This would check actual Bluetooth connection status
            # For now, simulate connection check
            logger.debug(f"Checking Bluetooth connection to {mac_address}")
            
            # Simulate connection check
            await asyncio.sleep(0.1)
            
            # For now, assume device is connected if it was previously connected
            return True
            
        except Exception as e:
            logger.error(f"Error checking Bluetooth connection: {e}")
            return False
            
    async def _disconnect_bluetooth_device(self, mac_address: str):
        """Disconnect from Bluetooth device."""
        try:
            logger.info(f"Disconnecting from Bluetooth device {mac_address}")
            
            # This would use system Bluetooth APIs to disconnect
            # For now, just log the action
            
        except Exception as e:
            logger.error(f"Error disconnecting Bluetooth device: {e}")
            
    def _extract_mac_address(self, device_id: str) -> Optional[str]:
        """Extract MAC address from device ID."""
        try:
            if device_id.startswith("bluetooth_"):
                mac_with_underscores = device_id.replace("bluetooth_", "")
                mac_address = mac_with_underscores.replace("_", ":")
                
                # Validate MAC address format
                if re.match(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', mac_address):
                    return mac_address
                    
        except Exception as e:
            logger.error(f"Error extracting MAC address: {e}")
            
        return None
        
    def _extract_mac_from_instance_id(self, instance_id: str) -> Optional[str]:
        """Extract MAC address from Windows instance ID."""
        try:
            # Windows instance ID format: BTHENUM\{0000110e-0000-1000-8000-00805f9b34fb}_VID&0001000a_PID&0001\8&12345678&0&000000000000_C00000000
            # Look for MAC address pattern in the instance ID
            mac_pattern = r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})'
            match = re.search(mac_pattern, instance_id)
            
            if match:
                return match.group(0)
                
        except Exception as e:
            logger.error(f"Error extracting MAC from instance ID: {e}")
            
        return None
        
    def _is_windows(self) -> bool:
        """Check if running on Windows."""
        import platform
        return platform.system().lower() == 'windows'
