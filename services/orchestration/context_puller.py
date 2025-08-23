"""
Context Puller
Queries current device graph, environment, occupancy, tariffs, and quiet hours.
"""

from __future__ import annotations

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from .models import ContextSnapshot, DeviceCapability, PrivacyClass, TrustTier

logger = logging.getLogger(__name__)


@dataclass
class EnvironmentData:
    """Environment sensor data."""
    temperature: float
    humidity: float
    pressure: float
    light_level: float
    air_quality: float
    timestamp: datetime


@dataclass
class OccupancyData:
    """Occupancy and presence data."""
    presence: bool
    location: str
    activity_level: str
    user_count: int
    timestamp: datetime


@dataclass
class TariffData:
    """Energy tariff information."""
    current_rate: float
    peak_rate: float
    off_peak_rate: float
    currency: str
    time_zone: str
    timestamp: datetime


@dataclass
class QuietHoursData:
    """Quiet hours configuration."""
    enabled: bool
    start_time: str  # HH:MM format
    end_time: str    # HH:MM format
    days: List[str]  # ["monday", "tuesday", etc.]
    exceptions: List[Dict[str, Any]]


class ContextPuller:
    """Pulls current context from various data sources."""
    
    def __init__(self):
        # Cache for context data
        self._context_cache: Dict[str, Any] = {}
        self._cache_ttl = 30  # seconds
        
        # Mock data sources (replace with actual integrations)
        self._device_registry = MockDeviceRegistry()
        self._environment_service = MockEnvironmentService()
        self._occupancy_service = MockOccupancyService()
        self._tariff_service = MockTariffService()
        self._quiet_hours_service = MockQuietHoursService()
    
    async def get_snapshot(self, task_spec: 'TaskSpec') -> ContextSnapshot:
        """
        Get a complete context snapshot for the task.
        
        Args:
            task_spec: Task specification to get context for
            
        Returns:
            ContextSnapshot with current system state
        """
        logger.debug(f"Getting context snapshot for task {task_spec.task_id}")
        
        # Get device graph
        device_graph = await self._get_device_graph(task_spec)
        
        # Get environment data
        environment = await self._get_environment_data()
        
        # Get occupancy data
        occupancy = await self._get_occupancy_data()
        
        # Get tariff data
        tariffs = await self._get_tariff_data()
        
        # Get quiet hours
        quiet_hours = await self._get_quiet_hours()
        
        return ContextSnapshot(
            device_graph=device_graph,
            environment=environment,
            occupancy=occupancy,
            tariffs=tariffs,
            quiet_hours=quiet_hours
        )
    
    async def _get_device_graph(self, task_spec: 'TaskSpec') -> Dict[str, DeviceCapability]:
        """Get current device graph with capabilities."""
        cache_key = f"device_graph_{task_spec.user_id or 'global'}"
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            return self._context_cache[cache_key]["data"]
        
        # Get devices from registry
        devices = await self._device_registry.get_devices()
        
        # Filter devices based on task requirements
        relevant_devices = self._filter_relevant_devices(devices, task_spec)
        
        # Convert to DeviceCapability objects
        device_graph = {}
        for device in relevant_devices:
            capability = DeviceCapability(
                device_id=device["id"],
                capability_type=device["type"],
                parameters=device["parameters"],
                privacy_class=self._determine_device_privacy(device),
                trust_tier=self._determine_device_trust(device),
                local_processing=device.get("local_processing", True),
                cloud_required=device.get("cloud_required", False)
            )
            device_graph[device["id"]] = capability
        
        # Cache the result
        self._cache_result(cache_key, device_graph)
        
        return device_graph
    
    async def _get_environment_data(self) -> Dict[str, Any]:
        """Get current environment data."""
        cache_key = "environment_data"
        
        if self._is_cache_valid(cache_key):
            return self._context_cache[cache_key]["data"]
        
        # Get environment data from service
        env_data = await self._environment_service.get_current_data()
        
        environment = {
            "temperature": env_data.temperature,
            "humidity": env_data.humidity,
            "pressure": env_data.pressure,
            "light_level": env_data.light_level,
            "air_quality": env_data.air_quality,
            "timestamp": env_data.timestamp.isoformat()
        }
        
        self._cache_result(cache_key, environment)
        return environment
    
    async def _get_occupancy_data(self) -> Dict[str, Any]:
        """Get current occupancy data."""
        cache_key = "occupancy_data"
        
        if self._is_cache_valid(cache_key):
            return self._context_cache[cache_key]["data"]
        
        # Get occupancy data from service
        occ_data = await self._occupancy_service.get_current_data()
        
        occupancy = {
            "presence": occ_data.presence,
            "location": occ_data.location,
            "activity_level": occ_data.activity_level,
            "user_count": occ_data.user_count,
            "timestamp": occ_data.timestamp.isoformat()
        }
        
        self._cache_result(cache_key, occupancy)
        return occupancy
    
    async def _get_tariff_data(self) -> Dict[str, Any]:
        """Get current tariff data."""
        cache_key = "tariff_data"
        
        if self._is_cache_valid(cache_key):
            return self._context_cache[cache_key]["data"]
        
        # Get tariff data from service
        tariff_data = await self._tariff_service.get_current_data()
        
        tariffs = {
            "current_rate": tariff_data.current_rate,
            "peak_rate": tariff_data.peak_rate,
            "off_peak_rate": tariff_data.off_peak_rate,
            "currency": tariff_data.currency,
            "time_zone": tariff_data.time_zone,
            "timestamp": tariff_data.timestamp.isoformat()
        }
        
        self._cache_result(cache_key, tariffs)
        return tariffs
    
    async def _get_quiet_hours(self) -> Dict[str, Any]:
        """Get quiet hours configuration."""
        cache_key = "quiet_hours"
        
        if self._is_cache_valid(cache_key):
            return self._context_cache[cache_key]["data"]
        
        # Get quiet hours from service
        quiet_data = await self._quiet_hours_service.get_configuration()
        
        quiet_hours = {
            "enabled": quiet_data.enabled,
            "start_time": quiet_data.start_time,
            "end_time": quiet_data.end_time,
            "days": quiet_data.days,
            "exceptions": quiet_data.exceptions
        }
        
        self._cache_result(cache_key, quiet_hours)
        return quiet_hours
    
    def _filter_relevant_devices(self, devices: List[Dict[str, Any]], task_spec: 'TaskSpec') -> List[Dict[str, Any]]:
        """Filter devices based on task requirements."""
        relevant_devices = []
        
        # Extract device types from task goals and constraints
        required_types = self._extract_required_device_types(task_spec)
        
        for device in devices:
            # Check if device type matches requirements
            if not required_types or device["type"] in required_types:
                relevant_devices.append(device)
        
        return relevant_devices
    
    def _extract_required_device_types(self, task_spec: 'TaskSpec') -> List[str]:
        """Extract required device types from task specification."""
        required_types = []
        
        # Check goals for device types
        for goal in task_spec.goals:
            if "thermostat" in goal.target.lower():
                required_types.append("thermostat")
            elif "light" in goal.target.lower():
                required_types.append("lighting")
            elif "security" in goal.target.lower():
                required_types.append("security")
            elif "sensor" in goal.target.lower():
                required_types.append("sensor")
        
        # Check constraints for device types
        for constraint in task_spec.constraints:
            if constraint.type == "device_availability" and isinstance(constraint.value, list):
                required_types.extend(constraint.value)
        
        return list(set(required_types))  # Remove duplicates
    
    def _determine_device_privacy(self, device: Dict[str, Any]) -> PrivacyClass:
        """Determine privacy class for a device."""
        device_type = device.get("type", "")
        
        # High-privacy devices
        if device_type in ["camera", "microphone", "biometric_sensor"]:
            return PrivacyClass.CONFIDENTIAL
        
        # Medium-privacy devices
        if device_type in ["thermostat", "smart_lock", "presence_sensor"]:
            return PrivacyClass.INTERNAL
        
        # Low-privacy devices
        if device_type in ["light", "switch", "outlet"]:
            return PrivacyClass.PUBLIC
        
        return PrivacyClass.INTERNAL
    
    def _determine_device_trust(self, device: Dict[str, Any]) -> TrustTier:
        """Determine trust tier for a device."""
        # Check device trust level
        trust_level = device.get("trust_level", "basic")
        
        trust_mapping = {
            "untrusted": TrustTier.UNTRUSTED,
            "basic": TrustTier.BASIC,
            "verified": TrustTier.VERIFIED,
            "trusted": TrustTier.TRUSTED,
            "privileged": TrustTier.PRIVILEGED
        }
        
        return trust_mapping.get(trust_level, TrustTier.BASIC)
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in self._context_cache:
            return False
        
        cache_entry = self._context_cache[cache_key]
        age = datetime.utcnow() - cache_entry["timestamp"]
        
        return age.total_seconds() < self._cache_ttl
    
    def _cache_result(self, cache_key: str, data: Any):
        """Cache a result with timestamp."""
        self._context_cache[cache_key] = {
            "data": data,
            "timestamp": datetime.utcnow()
        }
    
    async def get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a specific device."""
        return await self._device_registry.get_device_status(device_id)
    
    async def get_environment_summary(self) -> Dict[str, Any]:
        """Get a summary of current environment conditions."""
        env_data = await self._get_environment_data()
        
        return {
            "comfort_level": self._calculate_comfort_level(env_data),
            "energy_efficiency": self._calculate_energy_efficiency(env_data),
            "air_quality_status": self._get_air_quality_status(env_data["air_quality"])
        }
    
    def _calculate_comfort_level(self, env_data: Dict[str, Any]) -> str:
        """Calculate comfort level based on environment data."""
        temp = env_data["temperature"]
        humidity = env_data["humidity"]
        
        # Simple comfort calculation
        if 20 <= temp <= 24 and 40 <= humidity <= 60:
            return "optimal"
        elif 18 <= temp <= 26 and 30 <= humidity <= 70:
            return "comfortable"
        else:
            return "uncomfortable"
    
    def _calculate_energy_efficiency(self, env_data: Dict[str, Any]) -> str:
        """Calculate energy efficiency based on environment data."""
        temp = env_data["temperature"]
        light = env_data["light_level"]
        
        # Simple efficiency calculation
        if 20 <= temp <= 22 and light < 500:  # Low light, moderate temp
            return "efficient"
        elif temp < 18 or temp > 26 or light > 1000:
            return "inefficient"
        else:
            return "moderate"
    
    def _get_air_quality_status(self, air_quality: float) -> str:
        """Get air quality status."""
        if air_quality < 50:
            return "excellent"
        elif air_quality < 100:
            return "good"
        elif air_quality < 150:
            return "moderate"
        else:
            return "poor"


# Mock services for demonstration (replace with actual integrations)
class MockDeviceRegistry:
    """Mock device registry service."""
    
    async def get_devices(self) -> List[Dict[str, Any]]:
        """Get all available devices."""
        await asyncio.sleep(0.1)  # Simulate network delay
        
        return [
            {
                "id": "thermostat_001",
                "type": "thermostat",
                "parameters": {"min_temp": 16, "max_temp": 30},
                "trust_level": "verified",
                "local_processing": True,
                "cloud_required": False
            },
            {
                "id": "light_001",
                "type": "lighting",
                "parameters": {"brightness": 100, "color_temp": 2700},
                "trust_level": "basic",
                "local_processing": True,
                "cloud_required": False
            },
            {
                "id": "camera_001",
                "type": "camera",
                "parameters": {"resolution": "1080p", "motion_detection": True},
                "trust_level": "trusted",
                "local_processing": True,
                "cloud_required": True
            },
            {
                "id": "sensor_001",
                "type": "sensor",
                "parameters": {"sensor_type": "motion", "range": 10},
                "trust_level": "basic",
                "local_processing": True,
                "cloud_required": False
            }
        ]
    
    async def get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific device."""
        await asyncio.sleep(0.05)
        
        # Mock device statuses
        statuses = {
            "thermostat_001": {"state": "active", "current_temp": 22.5, "target_temp": 22},
            "light_001": {"state": "off", "brightness": 0},
            "camera_001": {"state": "standby", "recording": False},
            "sensor_001": {"state": "active", "motion_detected": False}
        }
        
        return statuses.get(device_id)


class MockEnvironmentService:
    """Mock environment service."""
    
    async def get_current_data(self) -> EnvironmentData:
        """Get current environment data."""
        await asyncio.sleep(0.1)
        
        return EnvironmentData(
            temperature=22.5,
            humidity=45.0,
            pressure=1013.25,
            light_level=300.0,
            air_quality=75.0,
            timestamp=datetime.utcnow()
        )


class MockOccupancyService:
    """Mock occupancy service."""
    
    async def get_current_data(self) -> OccupancyData:
        """Get current occupancy data."""
        await asyncio.sleep(0.1)
        
        return OccupancyData(
            presence=True,
            location="living_room",
            activity_level="active",
            user_count=2,
            timestamp=datetime.utcnow()
        )


class MockTariffService:
    """Mock tariff service."""
    
    async def get_current_data(self) -> TariffData:
        """Get current tariff data."""
        await asyncio.sleep(0.1)
        
        return TariffData(
            current_rate=0.12,
            peak_rate=0.18,
            off_peak_rate=0.08,
            currency="USD",
            time_zone="America/New_York",
            timestamp=datetime.utcnow()
        )


class MockQuietHoursService:
    """Mock quiet hours service."""
    
    async def get_configuration(self) -> QuietHoursData:
        """Get quiet hours configuration."""
        await asyncio.sleep(0.05)
        
        return QuietHoursData(
            enabled=True,
            start_time="22:00",
            end_time="07:00",
            days=["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
            exceptions=[]
        )
