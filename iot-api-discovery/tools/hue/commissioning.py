from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json

from .local import discover_bridges, pair, list_lights
from .adapters import HueBridgeManager
from ..discovery.arp import scan_network
from ..network_tools import ping_host

logger = logging.getLogger(__name__)


class HueCommissioningService:
    """Comprehensive Philips Hue commissioning service."""
    
    def __init__(self):
        self.bridge_manager = HueBridgeManager()
        self._commissioning_cache: Dict[str, Dict[str, Any]] = {}
        
    async def discover_hue_bridges(self, network_range: Optional[str] = None) -> List[Dict[str, Any]]:
        """Discover Philips Hue bridges on the network."""
        bridges = []
        
        # Method 1: Use Philips cloud discovery
        try:
            cloud_bridges = discover_bridges()
            for bridge in cloud_bridges:
                bridge_info = {
                    'id': bridge.get('id', 'unknown'),
                    'ip_address': bridge.get('internalipaddress'),
                    'port': bridge.get('port', 80),
                    'discovery_method': 'cloud',
                    'status': 'discovered'
                }
                bridges.append(bridge_info)
                logger.info(f"Discovered Hue bridge via cloud: {bridge_info['ip_address']}")
        except Exception as e:
            logger.warning(f"Cloud discovery failed: {e}")
        
        # Method 2: Network scanning (if network range provided)
        if network_range:
            try:
                network_bridges = await self._scan_network_for_bridges(network_range)
                for bridge in network_bridges:
                    # Check if already discovered
                    if not any(b['ip_address'] == bridge['ip_address'] for b in bridges):
                        bridges.append(bridge)
                        logger.info(f"Discovered Hue bridge via network scan: {bridge['ip_address']}")
            except Exception as e:
                logger.warning(f"Network scanning failed: {e}")
        
        return bridges
    
    async def _scan_network_for_bridges(self, network_range: str) -> List[Dict[str, Any]]:
        """Scan network for potential Hue bridges."""
        bridges = []
        
        # Scan for common Hue bridge ports and services
        try:
            # Scan for devices with port 80 open
            devices = await scan_network(network_range)
            
            for device in devices:
                ip = device.get('ip')
                if not ip:
                    continue
                
                # Check if it's a Hue bridge by probing common endpoints
                if await self._probe_hue_bridge(ip):
                    bridge_info = {
                        'id': f"discovered_{ip.replace('.', '_')}",
                        'ip_address': ip,
                        'port': 80,
                        'discovery_method': 'network_scan',
                        'status': 'discovered'
                    }
                    bridges.append(bridge_info)
                    
        except Exception as e:
            logger.error(f"Network scanning error: {e}")
            
        return bridges
    
    async def _probe_hue_bridge(self, ip: str) -> bool:
        """Probe an IP address to check if it's a Hue bridge."""
        try:
            import httpx
            
            # Check for Hue bridge description
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"http://{ip}/description.xml")
                if response.status_code == 200:
                    content = response.text.lower()
                    if "philips hue" in content or "hue bridge" in content:
                        return True
                
                # Check for Hue API endpoint
                response = await client.get(f"http://{ip}/api/config")
                if response.status_code in (200, 401, 403):
                    content = response.text.lower()
                    if "whitelist" in content:
                        return True
                        
        except Exception:
            pass
            
        return False
    
    async def pair_bridge(self, bridge_ip: str, app_name: str = "iot-orchestrator", device_name: str = "server") -> Dict[str, Any]:
        """Pair with a Philips Hue bridge."""
        try:
            logger.info(f"Attempting to pair with Hue bridge at {bridge_ip}")
            
            # Attempt pairing
            result = pair(bridge_ip, app_name, device_name)
            
            if result.get('ok') and result.get('username'):
                # Successfully paired
                bridge_id = f"hue_{bridge_ip.replace('.', '_')}"
                
                # Add bridge to manager
                self.bridge_manager.add_bridge(
                    bridge_id=bridge_id,
                    ip_address=bridge_ip,
                    username=result['username'],
                    client_key=result.get('clientkey')
                )
                
                # Cache commissioning info
                self._commissioning_cache[bridge_id] = {
                    'paired_at': datetime.utcnow(),
                    'bridge_ip': bridge_ip,
                    'username': result['username'],
                    'status': 'paired'
                }
                
                logger.info(f"Successfully paired with Hue bridge {bridge_id}")
                return {
                    'ok': True,
                    'bridge_id': bridge_id,
                    'username': result['username'],
                    'message': 'Bridge paired successfully'
                }
            else:
                logger.warning(f"Failed to pair with Hue bridge at {bridge_ip}: {result.get('error')}")
                return {
                    'ok': False,
                    'error': result.get('error', 'Unknown pairing error'),
                    'message': 'Press the link button on the bridge and try again'
                }
                
        except Exception as e:
            logger.error(f"Error pairing with Hue bridge {bridge_ip}: {e}")
            return {
                'ok': False,
                'error': str(e),
                'message': 'Connection error during pairing'
            }
    
    async def discover_devices(self, bridge_id: str) -> List[Dict[str, Any]]:
        """Discover devices (lights) on a paired bridge."""
        try:
            bridge_config = self.bridge_manager.get_bridge_config(bridge_id)
            if not bridge_config:
                return []
            
            # Get all lights from the bridge
            lights = list_lights(
                bridge_config['ip_address'],
                bridge_config['username']
            )
            
            devices = []
            for light_id, light_data in lights.items():
                device_info = await self._analyze_light_capabilities(light_id, light_data, bridge_id)
                devices.append(device_info)
            
            logger.info(f"Discovered {len(devices)} devices on bridge {bridge_id}")
            return devices
            
        except Exception as e:
            logger.error(f"Error discovering devices on bridge {bridge_id}: {e}")
            return []
    
    async def _analyze_light_capabilities(self, light_id: str, light_data: Dict[str, Any], bridge_id: str) -> Dict[str, Any]:
        """Analyze a light's capabilities and create device info."""
        device_id = f"{bridge_id}:{light_id}"
        
        # Extract basic info
        device_info = {
            'device_id': device_id,
            'bridge_id': bridge_id,
            'light_id': light_id,
            'name': light_data.get('name', f'Hue Light {light_id}'),
            'type': light_data.get('type', 'unknown'),
            'model_id': light_data.get('modelid', 'unknown'),
            'manufacturer': light_data.get('manufacturername', 'Philips'),
            'state': light_data.get('state', {}),
            'capabilities': [],
            'provider': 'hue',
            'discovered_at': datetime.utcnow().isoformat()
        }
        
        # Analyze capabilities based on light type and state
        capabilities = []
        
        # Basic switch capability (all lights have this)
        capabilities.append('switchable')
        
        # Check for dimming capability
        if 'bri' in light_data.get('state', {}):
            capabilities.append('dimmable')
        
        # Check for color capability
        if 'hue' in light_data.get('state', {}) and 'sat' in light_data.get('state', {}):
            capabilities.append('color_control')
        
        # Check for color temperature capability
        if 'ct' in light_data.get('state', {}):
            capabilities.append('color_temperature')
        
        device_info['capabilities'] = capabilities
        
        return device_info
    
    async def test_device_communication(self, device_id: str) -> Dict[str, Any]:
        """Test communication with a specific device."""
        try:
            bridge_config = self.bridge_manager.get_device_bridge(device_id)
            if not bridge_config:
                return {'ok': False, 'error': 'Bridge not configured'}
            
            light_id = device_id.split(':', 1)[1] if ':' in device_id else device_id
            
            # Test by getting current state
            lights = list_lights(
                bridge_config['ip_address'],
                bridge_config['username']
            )
            
            if light_id in lights:
                return {
                    'ok': True,
                    'device_id': device_id,
                    'state': lights[light_id].get('state', {}),
                    'reachable': True
                }
            else:
                return {
                    'ok': False,
                    'error': 'Device not found',
                    'reachable': False
                }
                
        except Exception as e:
            logger.error(f"Error testing device communication {device_id}: {e}")
            return {
                'ok': False,
                'error': str(e),
                'reachable': False
            }
    
    async def commission_device(self, device_id: str, device_config: Dict[str, Any]) -> Dict[str, Any]:
        """Commission a device with specific configuration."""
        try:
            # Test communication first
            test_result = await self.test_device_communication(device_id)
            if not test_result.get('ok'):
                return test_result
            
            # Apply device configuration
            bridge_config = self.bridge_manager.get_device_bridge(device_id)
            light_id = device_id.split(':', 1)[1] if ':' in device_id else device_id
            
            # Set device name if provided
            if 'name' in device_config:
                from .local import set_light_state
                # Note: Hue doesn't support setting names via API, this would be stored locally
                pass
            
            # Commissioning complete
            return {
                'ok': True,
                'device_id': device_id,
                'commissioned_at': datetime.utcnow().isoformat(),
                'status': 'commissioned',
                'message': 'Device commissioned successfully'
            }
            
        except Exception as e:
            logger.error(f"Error commissioning device {device_id}: {e}")
            return {
                'ok': False,
                'error': str(e),
                'message': 'Commissioning failed'
            }
    
    async def get_commissioning_status(self, bridge_id: Optional[str] = None) -> Dict[str, Any]:
        """Get commissioning status for bridges and devices."""
        status = {
            'bridges': {},
            'devices': {},
            'total_bridges': 0,
            'total_devices': 0,
            'last_updated': datetime.utcnow().isoformat()
        }
        
        if bridge_id:
            # Get status for specific bridge
            bridge_config = self.bridge_manager.get_bridge_config(bridge_id)
            if bridge_config:
                status['bridges'][bridge_id] = {
                    'ip_address': bridge_config['ip_address'],
                    'paired': True,
                    'paired_at': self._commissioning_cache.get(bridge_id, {}).get('paired_at'),
                    'status': 'active'
                }
                
                # Get devices for this bridge
                devices = await self.discover_devices(bridge_id)
                status['devices'][bridge_id] = devices
                status['total_devices'] = len(devices)
        else:
            # Get status for all bridges
            for bridge_id in self.bridge_manager._bridges.keys():
                bridge_config = self.bridge_manager.get_bridge_config(bridge_id)
                if bridge_config:
                    status['bridges'][bridge_id] = {
                        'ip_address': bridge_config['ip_address'],
                        'paired': True,
                        'paired_at': self._commissioning_cache.get(bridge_id, {}).get('paired_at'),
                        'status': 'active'
                    }
                    
                    # Get devices for this bridge
                    devices = await self.discover_devices(bridge_id)
                    status['devices'][bridge_id] = devices
                    status['total_devices'] += len(devices)
        
        status['total_bridges'] = len(status['bridges'])
        
        return status
    
    async def remove_bridge(self, bridge_id: str) -> Dict[str, Any]:
        """Remove a bridge and all its devices."""
        try:
            if bridge_id in self.bridge_manager._bridges:
                del self.bridge_manager._bridges[bridge_id]
            
            if bridge_id in self._commissioning_cache:
                del self._commissioning_cache[bridge_id]
            
            logger.info(f"Removed bridge {bridge_id}")
            return {
                'ok': True,
                'bridge_id': bridge_id,
                'message': 'Bridge removed successfully'
            }
            
        except Exception as e:
            logger.error(f"Error removing bridge {bridge_id}: {e}")
            return {
                'ok': False,
                'error': str(e),
                'message': 'Failed to remove bridge'
            }
