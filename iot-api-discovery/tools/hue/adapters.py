from __future__ import annotations

from typing import Dict, Any, Optional
import asyncio
import logging

from config.settings import settings
from tools.hue.local import list_lights, set_light_state
from libs.capabilities.schemas import DeviceAddress, Switchable, Dimmable, ColorControl

logger = logging.getLogger(__name__)


class HueBridgeManager:
    """Manages Philips Hue Bridge connections and credentials."""
    
    def __init__(self):
        self._bridges: Dict[str, Dict[str, Any]] = {}
        self._load_bridges()
    
    def _load_bridges(self):
        """Load bridge configurations from settings."""
        # This would typically load from database or config file
        # For now, we'll use environment variables or settings
        if hasattr(settings, 'hue_bridges'):
            self._bridges = settings.hue_bridges or {}
    
    def get_bridge_config(self, bridge_id: str) -> Optional[Dict[str, Any]]:
        """Get bridge configuration by ID."""
        return self._bridges.get(bridge_id)
    
    def add_bridge(self, bridge_id: str, ip_address: str, username: str, client_key: Optional[str] = None):
        """Add a new bridge configuration."""
        self._bridges[bridge_id] = {
            'ip_address': ip_address,
            'username': username,
            'client_key': client_key
        }
        # TODO: Save to database or config file
    
    def get_device_bridge(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get bridge configuration for a specific device."""
        # Extract bridge ID from device ID (format: bridge_id:light_id)
        if ':' in device_id:
            bridge_id = device_id.split(':', 1)[0]
            return self.get_bridge_config(bridge_id)
        return None


class HueSwitchAdapter(Switchable):
    """Philips Hue switch capability adapter."""
    
    def __init__(self):
        self.bridge_manager = HueBridgeManager()
    
    def turn_on(self, address: DeviceAddress) -> Dict[str, Any]:
        """Turn on a Philips Hue light."""
        try:
            bridge_config = self.bridge_manager.get_device_bridge(address.external_id)
            if not bridge_config:
                return {"ok": False, "error": "Bridge not configured"}
            
            light_id = address.external_id.split(':', 1)[1] if ':' in address.external_id else address.external_id
            
            state = {"on": True}
            result = set_light_state(
                bridge_config['ip_address'],
                bridge_config['username'],
                light_id,
                state
            )
            
            return {"ok": True, "result": result}
            
        except Exception as e:
            logger.error(f"Error turning on Hue light {address.external_id}: {e}")
            return {"ok": False, "error": str(e)}
    
    def turn_off(self, address: DeviceAddress) -> Dict[str, Any]:
        """Turn off a Philips Hue light."""
        try:
            bridge_config = self.bridge_manager.get_device_bridge(address.external_id)
            if not bridge_config:
                return {"ok": False, "error": "Bridge not configured"}
            
            light_id = address.external_id.split(':', 1)[1] if ':' in address.external_id else address.external_id
            
            state = {"on": False}
            result = set_light_state(
                bridge_config['ip_address'],
                bridge_config['username'],
                light_id,
                state
            )
            
            return {"ok": True, "result": result}
            
        except Exception as e:
            logger.error(f"Error turning off Hue light {address.external_id}: {e}")
            return {"ok": False, "error": str(e)}
    
    def get_state(self, address: DeviceAddress) -> Dict[str, Any]:
        """Get the current state of a Philips Hue light."""
        try:
            bridge_config = self.bridge_manager.get_device_bridge(address.external_id)
            if not bridge_config:
                return {"ok": False, "error": "Bridge not configured"}
            
            light_id = address.external_id.split(':', 1)[1] if ':' in address.external_id else address.external_id
            
            lights = list_lights(
                bridge_config['ip_address'],
                bridge_config['username']
            )
            
            if light_id in lights:
                return {"ok": True, "state": lights[light_id]}
            else:
                return {"ok": False, "error": "Light not found"}
                
        except Exception as e:
            logger.error(f"Error getting Hue light state {address.external_id}: {e}")
            return {"ok": False, "error": str(e)}


class HueDimmableAdapter(HueSwitchAdapter, Dimmable):
    """Philips Hue dimmable capability adapter."""
    
    def set_brightness(self, address: DeviceAddress, level: int) -> Dict[str, Any]:
        """Set brightness level for a Philips Hue light."""
        try:
            bridge_config = self.bridge_manager.get_device_bridge(address.external_id)
            if not bridge_config:
                return {"ok": False, "error": "Bridge not configured"}
            
            light_id = address.external_id.split(':', 1)[1] if ':' in address.external_id else address.external_id
            
            # Convert percentage (0-100) to Hue brightness (1-254)
            brightness = max(1, min(254, int((level / 100.0) * 254)))
            
            state = {"bri": brightness}
            result = set_light_state(
                bridge_config['ip_address'],
                bridge_config['username'],
                light_id,
                state
            )
            
            return {"ok": True, "result": result}
            
        except Exception as e:
            logger.error(f"Error setting Hue light brightness {address.external_id}: {e}")
            return {"ok": False, "error": str(e)}


class HueColorControlAdapter(HueDimmableAdapter, ColorControl):
    """Philips Hue color control capability adapter."""
    
    def set_color_hsv(self, address: DeviceAddress, h: float, s: float, v: float) -> Dict[str, Any]:
        """Set HSV color for a Philips Hue light."""
        try:
            bridge_config = self.bridge_manager.get_device_bridge(address.external_id)
            if not bridge_config:
                return {"ok": False, "error": "Bridge not configured"}
            
            light_id = address.external_id.split(':', 1)[1] if ':' in address.external_id else address.external_id
            
            # Convert HSV to Hue format
            # Hue: 0-65535 (16-bit), Saturation: 0-254, Brightness: 1-254
            hue = int((h / 360.0) * 65535)
            saturation = max(0, min(254, int(s * 254)))
            brightness = max(1, min(254, int(v * 254)))
            
            state = {
                "hue": hue,
                "sat": saturation,
                "bri": brightness
            }
            
            result = set_light_state(
                bridge_config['ip_address'],
                bridge_config['username'],
                light_id,
                state
            )
            
            return {"ok": True, "result": result}
            
        except Exception as e:
            logger.error(f"Error setting Hue light color {address.external_id}: {e}")
            return {"ok": False, "error": str(e)}
    
    def set_color_temp(self, address: DeviceAddress, mireds: int) -> Dict[str, Any]:
        """Set color temperature for a Philips Hue light."""
        try:
            bridge_config = self.bridge_manager.get_device_bridge(address.external_id)
            if not bridge_config:
                return {"ok": False, "error": "Bridge not configured"}
            
            light_id = address.external_id.split(':', 1)[1] if ':' in address.external_id else address.external_id
            
            # Convert mireds to Hue format (153-500 mireds)
            # Hue uses mireds directly
            ct = max(153, min(500, int(mireds)))
            
            state = {"ct": ct}
            result = set_light_state(
                bridge_config['ip_address'],
                bridge_config['username'],
                light_id,
                state
            )
            
            return {"ok": True, "result": result}
            
        except Exception as e:
            logger.error(f"Error setting Hue light color temperature {address.external_id}: {e}")
            return {"ok": False, "error": str(e)}
