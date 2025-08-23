"""
Trust Channels Manager
Manages secure trust relationships with IoT devices.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import hashlib
import secrets
import json
from enum import Enum

from ..agent import DeviceInfo

logger = logging.getLogger(__name__)


class TrustLevel(Enum):
    """Trust levels for devices."""
    UNTRUSTED = 0.0
    LOW = 0.25
    MEDIUM = 0.5
    HIGH = 0.75
    FULL = 1.0


class TrustChannel:
    """Represents a trust channel with a device."""
    
    def __init__(self, device_id: str, trust_level: float = 0.0):
        self.device_id = device_id
        self.trust_level = trust_level
        self.created_at = datetime.utcnow()
        self.last_verified = datetime.utcnow()
        self.verification_count = 0
        self.channel_key = secrets.token_hex(32)
        self.is_active = True
        
    def verify(self) -> bool:
        """Verify the trust channel is still valid."""
        # Check if channel hasn't expired (24 hours)
        if datetime.utcnow() - self.last_verified > timedelta(hours=24):
            self.is_active = False
            return False
            
        self.last_verified = datetime.utcnow()
        self.verification_count += 1
        return True
        
    def increase_trust(self, increment: float = 0.1) -> float:
        """Increase trust level."""
        self.trust_level = min(1.0, self.trust_level + increment)
        return self.trust_level
        
    def decrease_trust(self, decrement: float = 0.1) -> float:
        """Decrease trust level."""
        self.trust_level = max(0.0, self.trust_level - decrement)
        return self.trust_level


class TrustManager:
    """Manages trust relationships with IoT devices."""
    
    def __init__(self):
        self._trust_channels: Dict[str, TrustChannel] = {}
        self._trust_policies: Dict[str, Dict[str, Any]] = {}
        self._setup_default_policies()
        
    def _setup_default_policies(self):
        """Setup default trust policies."""
        self._trust_policies = {
            'default': {
                'min_trust_level': 0.0,
                'max_trust_level': 1.0,
                'trust_increment': 0.1,
                'trust_decrement': 0.2,
                'verification_interval': 3600,  # 1 hour
                'max_failures': 3
            },
            'high_security': {
                'min_trust_level': 0.5,
                'max_trust_level': 1.0,
                'trust_increment': 0.05,
                'trust_decrement': 0.3,
                'verification_interval': 1800,  # 30 minutes
                'max_failures': 2
            },
            'low_security': {
                'min_trust_level': 0.0,
                'max_trust_level': 0.8,
                'trust_increment': 0.2,
                'trust_decrement': 0.1,
                'verification_interval': 7200,  # 2 hours
                'max_failures': 5
            }
        }
        
    async def establish_trust(self, device_info: DeviceInfo) -> float:
        """Establish a trust relationship with a device."""
        try:
            logger.info(f"Establishing trust with device {device_info.name}")
            
            # Determine initial trust level based on device type and manufacturer
            initial_trust = self._calculate_initial_trust(device_info)
            
            # Create trust channel
            trust_channel = TrustChannel(device_info.device_id, initial_trust)
            self._trust_channels[device_info.device_id] = trust_channel
            
            # Perform initial trust verification
            verification_success = await self._verify_device_trust(device_info)
            
            if verification_success:
                # Increase trust based on successful verification
                trust_channel.increase_trust(0.1)
                logger.info(f"Trust established with {device_info.name} at level {trust_channel.trust_level}")
            else:
                # Decrease trust based on failed verification
                trust_channel.decrease_trust(0.2)
                logger.warning(f"Trust verification failed for {device_info.name}, level: {trust_channel.trust_level}")
                
            return trust_channel.trust_level
            
        except Exception as e:
            logger.error(f"Error establishing trust with {device_info.name}: {e}")
            return 0.0
            
    def _calculate_initial_trust(self, device_info: DeviceInfo) -> float:
        """Calculate initial trust level based on device characteristics."""
        initial_trust = 0.3  # Base trust level
        
        # Adjust based on manufacturer reputation
        manufacturer_trust = self._get_manufacturer_trust_level(device_info.manufacturer)
        initial_trust += manufacturer_trust
        
        # Adjust based on device type
        device_type_trust = self._get_device_type_trust_level(device_info.model)
        initial_trust += device_type_trust
        
        # Adjust based on protocol
        protocol_trust = self._get_protocol_trust_level(device_info.protocol)
        initial_trust += protocol_trust
        
        # Ensure trust level is within bounds
        return max(0.0, min(1.0, initial_trust))
        
    def _get_manufacturer_trust_level(self, manufacturer: str) -> float:
        """Get trust level adjustment based on manufacturer."""
        manufacturer_trust_levels = {
            'Philips': 0.2,
            'Google': 0.2,
            'Amazon': 0.15,
            'Apple': 0.2,
            'Samsung': 0.15,
            'Xiaomi': 0.1,
            'Wyze': 0.1,
            'Tuya': 0.05,
            'IKEA': 0.1,
            'Sonos': 0.15,
            'Bose': 0.15,
            'Fitbit': 0.1,
            'Garmin': 0.1,
            'Withings': 0.1,
            'August': 0.15,
            'Schlage': 0.15,
            'Kwikset': 0.1,
            'Yale': 0.1,
            'Ecobee': 0.15,
            'Honeywell': 0.15
        }
        
        return manufacturer_trust_levels.get(manufacturer, 0.0)
        
    def _get_device_type_trust_level(self, device_type: str) -> float:
        """Get trust level adjustment based on device type."""
        device_type_trust_levels = {
            'Thermostat': 0.1,
            'Smart Lock': 0.15,
            'Security Camera': 0.1,
            'Smart Light': 0.05,
            'Smart Switch': 0.05,
            'Smart Speaker': 0.1,
            'Wearable': 0.05,
            'Smart Scale': 0.05,
            'Hub/Gateway': 0.2
        }
        
        return device_type_trust_levels.get(device_type, 0.0)
        
    def _get_protocol_trust_level(self, protocol) -> float:
        """Get trust level adjustment based on protocol."""
        protocol_trust_levels = {
            'wifi': 0.05,
            'bluetooth': 0.1,
            'zigbee': 0.15,
            'zwave': 0.15,
            'matter': 0.2,
            'api': 0.05
        }
        
        return protocol_trust_levels.get(protocol.value, 0.0)
        
    async def _verify_device_trust(self, device_info: DeviceInfo) -> bool:
        """Verify device trust through various checks."""
        try:
            verification_methods = [
                self._verify_device_identity,
                self._verify_device_capabilities,
                self._verify_device_communication,
                self._verify_device_security
            ]
            
            successful_verifications = 0
            total_verifications = len(verification_methods)
            
            for method in verification_methods:
                try:
                    if await method(device_info):
                        successful_verifications += 1
                except Exception as e:
                    logger.debug(f"Verification method {method.__name__} failed: {e}")
                    
            # Require at least 50% of verifications to pass
            success_rate = successful_verifications / total_verifications
            return success_rate >= 0.5
            
        except Exception as e:
            logger.error(f"Error during trust verification: {e}")
            return False
            
    async def _verify_device_identity(self, device_info: DeviceInfo) -> bool:
        """Verify device identity."""
        try:
            # Check if device has valid identification
            if device_info.device_id and device_info.name:
                # Simulate identity verification
                await asyncio.sleep(0.1)
                return True
            return False
        except Exception as e:
            logger.debug(f"Identity verification failed: {e}")
            return False
            
    async def _verify_device_capabilities(self, device_info: DeviceInfo) -> bool:
        """Verify device capabilities."""
        try:
            # Check if device has valid capabilities
            if device_info.capabilities and len(device_info.capabilities) > 0:
                # Simulate capability verification
                await asyncio.sleep(0.1)
                return True
            return False
        except Exception as e:
            logger.debug(f"Capability verification failed: {e}")
            return False
            
    async def _verify_device_communication(self, device_info: DeviceInfo) -> bool:
        """Verify device communication."""
        try:
            # Check if device can communicate
            if device_info.endpoints and len(device_info.endpoints) > 0:
                # Simulate communication test
                await asyncio.sleep(0.1)
                return True
            return False
        except Exception as e:
            logger.debug(f"Communication verification failed: {e}")
            return False
            
    async def _verify_device_security(self, device_info: DeviceInfo) -> bool:
        """Verify device security."""
        try:
            # Check device security characteristics
            # For now, assume all devices pass basic security check
            await asyncio.sleep(0.1)
            return True
        except Exception as e:
            logger.debug(f"Security verification failed: {e}")
            return False
            
    async def verify_trust(self, device_id: str) -> bool:
        """Verify existing trust relationship."""
        trust_channel = self._trust_channels.get(device_id)
        if not trust_channel:
            logger.warning(f"No trust channel found for device {device_id}")
            return False
            
        # Check if channel is still active
        if not trust_channel.verify():
            logger.warning(f"Trust channel expired for device {device_id}")
            return False
            
        # Perform periodic trust verification
        if trust_channel.verification_count % 10 == 0:  # Every 10th verification
            device_info = self._get_device_info(device_id)
            if device_info:
                verification_success = await self._verify_device_trust(device_info)
                if verification_success:
                    trust_channel.increase_trust(0.05)
                else:
                    trust_channel.decrease_trust(0.1)
                    
        return trust_channel.is_active
        
    def get_trust_level(self, device_id: str) -> float:
        """Get current trust level for a device."""
        trust_channel = self._trust_channels.get(device_id)
        if trust_channel:
            return trust_channel.trust_level
        return 0.0
        
    def increase_trust(self, device_id: str, increment: float = 0.1) -> float:
        """Increase trust level for a device."""
        trust_channel = self._trust_channels.get(device_id)
        if trust_channel:
            return trust_channel.increase_trust(increment)
        return 0.0
        
    def decrease_trust(self, device_id: str, decrement: float = 0.1) -> float:
        """Decrease trust level for a device."""
        trust_channel = self._trust_channels.get(device_id)
        if trust_channel:
            return trust_channel.decrease_trust(decrement)
        return 0.0
        
    def revoke_trust(self, device_id: str) -> bool:
        """Revoke trust for a device."""
        if device_id in self._trust_channels:
            del self._trust_channels[device_id]
            logger.info(f"Trust revoked for device {device_id}")
            return True
        return False
        
    def get_all_trust_channels(self) -> List[Dict[str, Any]]:
        """Get all trust channels."""
        return [
            {
                'device_id': channel.device_id,
                'trust_level': channel.trust_level,
                'created_at': channel.created_at.isoformat(),
                'last_verified': channel.last_verified.isoformat(),
                'verification_count': channel.verification_count,
                'is_active': channel.is_active
            }
            for channel in self._trust_channels.values()
        ]
        
    def cleanup_expired_channels(self):
        """Clean up expired trust channels."""
        current_time = datetime.utcnow()
        expired_channels = []
        
        for device_id, channel in self._trust_channels.items():
            if current_time - channel.last_verified > timedelta(hours=24):
                expired_channels.append(device_id)
                
        for device_id in expired_channels:
            del self._trust_channels[device_id]
            
        if expired_channels:
            logger.info(f"Cleaned up {len(expired_channels)} expired trust channels")
            
    def _get_device_info(self, device_id: str) -> Optional[DeviceInfo]:
        """Get device info by device ID."""
        # This would typically come from the connection agent
        # For now, return None as this is a placeholder
        return None
