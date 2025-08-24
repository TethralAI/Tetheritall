"""
Device Ingestion Service
Handles ingestion and normalization of devices and services into canonical capabilities.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, time
from dataclasses import dataclass, field
import json

from shared.config.settings import settings
from shared.database.api_database import get_session_factory, session_scope
from shared.database.models import Device, ApiEndpoint

from .models import (
    DeviceCapability, ServiceCapability, ContextSnapshot, CapabilityType,
    SuggestionRequest
)

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    """Result of device and service ingestion."""
    success: bool = True
    capability_graph: Dict[str, Any] = field(default_factory=dict)
    context_snapshot: Optional[ContextSnapshot] = None
    service_readiness_map: Dict[str, bool] = field(default_factory=dict)
    error: Optional[str] = None


class DeviceIngestionService:
    """
    Service for ingesting and normalizing devices and services.
    
    Implements B1 from the spec:
    - Normalize devices and services into canonical capabilities
    - Attach room and zone hints
    - Validate reachability
    - Build capability graph and service readiness map
    """
    
    def __init__(self):
        self._session_factory = get_session_factory(settings.database_url)
        self._running = False
        
        # Capability mapping registry
        self._capability_mappings = self._initialize_capability_mappings()
        
        # Service connectors
        self._service_connectors = {
            "weather": self._get_weather_service,
            "calendar": self._get_calendar_service,
            "presence": self._get_presence_service,
            "time": self._get_time_service,
            "location": self._get_location_service,
            "traffic": self._get_traffic_service,
            "notification": self._get_notification_service
        }
        
    async def start(self):
        """Start the ingestion service."""
        self._running = True
        logger.info("Device ingestion service started")
        
    async def stop(self):
        """Stop the ingestion service."""
        self._running = False
        logger.info("Device ingestion service stopped")
        
    async def ingest(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        context_hints: Optional[Dict[str, Any]] = None
    ) -> IngestionResult:
        """
        Main ingestion method that processes devices and services.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            context_hints: Additional context hints
            
        Returns:
            IngestionResult with capability graph and context snapshot
        """
        try:
            # Step 1: Load devices from database
            devices = await self._load_devices_from_database(user_id)
            
            # Step 2: Normalize devices into capabilities
            device_capabilities = await self._normalize_devices(devices)
            
            # Step 3: Load and validate services
            service_capabilities = await self._load_services()
            
            # Step 4: Build capability graph
            capability_graph = await self._build_capability_graph(
                device_capabilities, service_capabilities
            )
            
            # Step 5: Create context snapshot
            context_snapshot = await self._create_context_snapshot(
                user_id, session_id, context_hints
            )
            
            # Step 6: Build service readiness map
            service_readiness_map = await self._build_service_readiness_map(
                service_capabilities
            )
            
            return IngestionResult(
                success=True,
                capability_graph=capability_graph,
                context_snapshot=context_snapshot,
                service_readiness_map=service_readiness_map
            )
            
        except Exception as e:
            logger.error(f"Error during ingestion: {e}")
            return IngestionResult(
                success=False,
                error=str(e)
            )
    
    async def _load_devices_from_database(self, user_id: str) -> List[Device]:
        """Load devices from the database."""
        devices = []
        
        with session_scope(self._session_factory) as session:
            # Load devices associated with the user
            db_devices = session.query(Device).filter(
                Device.user_id == user_id
            ).all()
            
            for device in db_devices:
                # Load associated API endpoints
                endpoints = session.query(ApiEndpoint).filter(
                    ApiEndpoint.device_id == device.id
                ).all()
                
                device.endpoints = endpoints
                devices.append(device)
        
        logger.info(f"Loaded {len(devices)} devices for user {user_id}")
        return devices
    
    async def _normalize_devices(self, devices: List[Device]) -> List[DeviceCapability]:
        """Normalize devices into canonical capabilities."""
        capabilities = []
        
        for device in devices:
            # Determine device capabilities based on model and manufacturer
            device_capabilities = self._map_device_capabilities(device)
            
            for capability_type in device_capabilities:
                capability = DeviceCapability(
                    capability_type=capability_type,
                    device_id=str(device.id),
                    device_name=device.name or f"{device.manufacturer} {device.model}",
                    device_brand=device.manufacturer,
                    device_model=device.model,
                    room=device.room,
                    zone=device.zone,
                    parameters=self._extract_device_parameters(device, capability_type),
                    constraints=self._extract_device_constraints(device, capability_type),
                    energy_profile=self._extract_energy_profile(device),
                    reachable=self._check_device_reachability(device),
                    last_seen=device.last_seen
                )
                capabilities.append(capability)
        
        logger.info(f"Normalized {len(devices)} devices into {len(capabilities)} capabilities")
        return capabilities
    
    async def _load_services(self) -> List[ServiceCapability]:
        """Load and validate available services."""
        services = []
        
        for service_name, connector_func in self._service_connectors.items():
            try:
                service = await connector_func()
                if service:
                    services.append(service)
            except Exception as e:
                logger.warning(f"Failed to load service {service_name}: {e}")
        
        logger.info(f"Loaded {len(services)} services")
        return services
    
    async def _build_capability_graph(
        self,
        device_capabilities: List[DeviceCapability],
        service_capabilities: List[ServiceCapability]
    ) -> Dict[str, Any]:
        """Build the capability graph from devices and services."""
        graph = {
            "devices": {},
            "services": {},
            "capabilities": {},
            "rooms": {},
            "zones": {}
        }
        
        # Organize device capabilities
        for capability in device_capabilities:
            device_id = capability.device_id
            
            if device_id not in graph["devices"]:
                graph["devices"][device_id] = {
                    "name": capability.device_name,
                    "brand": capability.device_brand,
                    "model": capability.device_model,
                    "room": capability.room,
                    "zone": capability.zone,
                    "capabilities": [],
                    "reachable": capability.reachable
                }
            
            graph["devices"][device_id]["capabilities"].append({
                "type": capability.capability_type.value,
                "parameters": capability.parameters,
                "constraints": capability.constraints
            })
            
            # Index by capability type
            cap_type = capability.capability_type.value
            if cap_type not in graph["capabilities"]:
                graph["capabilities"][cap_type] = []
            graph["capabilities"][cap_type].append(device_id)
            
            # Index by room
            if capability.room:
                if capability.room not in graph["rooms"]:
                    graph["rooms"][capability.room] = []
                graph["rooms"][capability.room].append(device_id)
            
            # Index by zone
            if capability.zone:
                if capability.zone not in graph["zones"]:
                    graph["zones"][capability.zone] = []
                graph["zones"][capability.zone].append(device_id)
        
        # Organize service capabilities
        for capability in service_capabilities:
            service_id = capability.service_id
            
            graph["services"][service_id] = {
                "name": capability.service_name,
                "type": capability.capability_type.value,
                "available": capability.available,
                "parameters": capability.parameters,
                "constraints": capability.constraints
            }
            
            # Index by capability type
            cap_type = capability.capability_type.value
            if cap_type not in graph["capabilities"]:
                graph["capabilities"][cap_type] = []
            graph["capabilities"][cap_type].append(f"service:{service_id}")
        
        return graph
    
    async def _create_context_snapshot(
        self,
        user_id: str,
        session_id: Optional[str],
        context_hints: Optional[Dict[str, Any]]
    ) -> ContextSnapshot:
        """Create a snapshot of current context."""
        now = datetime.now()
        
        # Determine if it's quiet hours
        quiet_hours_start = time(22, 0)  # 10 PM
        quiet_hours_end = time(7, 0)     # 7 AM
        is_quiet_hours = (
            now.time() >= quiet_hours_start or 
            now.time() <= quiet_hours_end
        )
        
        # Get weather conditions
        weather_conditions = await self._get_current_weather()
        
        # Get calendar state
        calendar_state = await self._get_calendar_state(user_id)
        
        # Get user presence
        user_present = await self._get_user_presence(user_id)
        
        return ContextSnapshot(
            timestamp=now,
            time_of_day=now.time(),
            is_weekend=now.weekday() >= 5,
            is_quiet_hours=is_quiet_hours,
            user_present=user_present,
            user_location=context_hints.get("location") if context_hints else None,
            calendar_state=calendar_state,
            weather_conditions=weather_conditions,
            recent_activity=context_hints.get("recent_activity", []) if context_hints else [],
            session_id=session_id
        )
    
    async def _build_service_readiness_map(
        self,
        service_capabilities: List[ServiceCapability]
    ) -> Dict[str, bool]:
        """Build service readiness map."""
        readiness_map = {}
        
        for capability in service_capabilities:
            readiness_map[capability.service_id] = capability.available
        
        return readiness_map
    
    def _map_device_capabilities(self, device: Device) -> List[CapabilityType]:
        """Map device to its capabilities based on model and manufacturer."""
        capabilities = []
        
        # Use capability mappings to determine device capabilities
        device_key = f"{device.manufacturer.lower()}_{device.model.lower()}"
        
        if device_key in self._capability_mappings:
            capabilities.extend(self._capability_mappings[device_key])
        else:
            # Fallback: infer capabilities from device type or name
            device_name = device.name or f"{device.manufacturer} {device.model}"
            capabilities.extend(self._infer_capabilities_from_name(device_name))
        
        return capabilities
    
    def _extract_device_parameters(
        self,
        device: Device,
        capability_type: CapabilityType
    ) -> Dict[str, Any]:
        """Extract parameters for a specific capability type."""
        parameters = {}
        
        if capability_type == CapabilityType.LIGHTING:
            parameters.update({
                "dimmable": True,  # Assume dimmable unless specified otherwise
                "color_temp": True,
                "rgb": False,
                "max_brightness": 100
            })
        elif capability_type == CapabilityType.SENSING:
            parameters.update({
                "sensor_types": ["motion", "temperature", "humidity"],
                "update_interval": 30  # seconds
            })
        elif capability_type == CapabilityType.ACTUATION:
            parameters.update({
                "switch_type": "toggle",
                "max_power": 1000  # watts
            })
        
        return parameters
    
    def _extract_device_constraints(
        self,
        device: Device,
        capability_type: CapabilityType
    ) -> Dict[str, Any]:
        """Extract constraints for a specific capability type."""
        constraints = {}
        
        if capability_type == CapabilityType.LIGHTING:
            constraints.update({
                "min_brightness": 0,
                "max_brightness": 100,
                "quiet_hours_suppression": True
            })
        elif capability_type == CapabilityType.SENSING:
            constraints.update({
                "range": 10,  # meters
                "update_frequency": 30  # seconds
            })
        
        return constraints
    
    def _extract_energy_profile(self, device: Device) -> Optional[Dict[str, Any]]:
        """Extract energy profile for a device."""
        # This would be populated from device specifications or monitoring
        return {
            "power_consumption": 10,  # watts
            "standby_power": 1,       # watts
            "energy_efficiency": "A"
        }
    
    def _check_device_reachability(self, device: Device) -> bool:
        """Check if a device is currently reachable."""
        # This would check device connectivity
        # For now, assume all devices are reachable
        return True
    
    def _initialize_capability_mappings(self) -> Dict[str, List[CapabilityType]]:
        """Initialize the capability mapping registry."""
        return {
            # Philips Hue
            "philips_hue_bulb": [CapabilityType.LIGHTING],
            "philips_hue_switch": [CapabilityType.ACTUATION],
            "philips_hue_sensor": [CapabilityType.SENSING],
            
            # SmartThings
            "samsung_smartthings_hub": [CapabilityType.NETWORK],
            "samsung_smartthings_sensor": [CapabilityType.SENSING],
            
            # Nest
            "google_nest_thermostat": [CapabilityType.CLIMATE, CapabilityType.SENSING],
            "google_nest_camera": [CapabilityType.VIDEO, CapabilityType.SECURITY],
            
            # Generic mappings
            "generic_light_bulb": [CapabilityType.LIGHTING],
            "generic_sensor": [CapabilityType.SENSING],
            "generic_switch": [CapabilityType.ACTUATION],
            "generic_camera": [CapabilityType.VIDEO, CapabilityType.SECURITY],
            "generic_thermostat": [CapabilityType.CLIMATE, CapabilityType.SENSING],
        }
    
    def _infer_capabilities_from_name(self, device_name: str) -> List[CapabilityType]:
        """Infer capabilities from device name."""
        name_lower = device_name.lower()
        capabilities = []
        
        if any(word in name_lower for word in ["light", "bulb", "lamp", "switch"]):
            capabilities.append(CapabilityType.LIGHTING)
        if any(word in name_lower for word in ["sensor", "motion", "temperature", "humidity"]):
            capabilities.append(CapabilityType.SENSING)
        if any(word in name_lower for word in ["switch", "outlet", "plug"]):
            capabilities.append(CapabilityType.ACTUATION)
        if any(word in name_lower for word in ["camera", "video"]):
            capabilities.append(CapabilityType.VIDEO)
        if any(word in name_lower for word in ["lock", "door", "security"]):
            capabilities.append(CapabilityType.SECURITY)
        if any(word in name_lower for word in ["thermostat", "climate"]):
            capabilities.append(CapabilityType.CLIMATE)
        
        return capabilities
    
    # Service connector methods
    async def _get_weather_service(self) -> Optional[ServiceCapability]:
        """Get weather service capability."""
        return ServiceCapability(
            capability_type=CapabilityType.WEATHER,
            service_name="Weather Service",
            service_id="weather",
            parameters={"location": "auto"},
            available=True
        )
    
    async def _get_calendar_service(self) -> Optional[ServiceCapability]:
        """Get calendar service capability."""
        return ServiceCapability(
            capability_type=CapabilityType.CALENDAR,
            service_name="Calendar Service",
            service_id="calendar",
            parameters={"provider": "google"},
            available=True
        )
    
    async def _get_presence_service(self) -> Optional[ServiceCapability]:
        """Get presence service capability."""
        return ServiceCapability(
            capability_type=CapabilityType.PRESENCE,
            service_name="Presence Service",
            service_id="presence",
            parameters={"sources": ["motion", "location", "calendar"]},
            available=True
        )
    
    async def _get_time_service(self) -> Optional[ServiceCapability]:
        """Get time service capability."""
        return ServiceCapability(
            capability_type=CapabilityType.TIME,
            service_name="Time Service",
            service_id="time",
            parameters={"timezone": "auto"},
            available=True
        )
    
    async def _get_location_service(self) -> Optional[ServiceCapability]:
        """Get location service capability."""
        return ServiceCapability(
            capability_type=CapabilityType.LOCATION,
            service_name="Location Service",
            service_id="location",
            parameters={"accuracy": "high"},
            available=True
        )
    
    async def _get_traffic_service(self) -> Optional[ServiceCapability]:
        """Get traffic service capability."""
        return ServiceCapability(
            capability_type=CapabilityType.TRAFFIC,
            service_name="Traffic Service",
            service_id="traffic",
            parameters={"provider": "google"},
            available=False  # Not implemented yet
        )
    
    async def _get_notification_service(self) -> Optional[ServiceCapability]:
        """Get notification service capability."""
        return ServiceCapability(
            capability_type=CapabilityType.NOTIFICATION,
            service_name="Notification Service",
            service_id="notification",
            parameters={"channels": ["push", "email"]},
            available=True
        )
    
    async def _get_current_weather(self) -> Optional[Dict[str, Any]]:
        """Get current weather conditions."""
        # This would integrate with a weather service
        return {
            "temperature": 22,
            "condition": "clear",
            "humidity": 45
        }
    
    async def _get_calendar_state(self, user_id: str) -> Optional[str]:
        """Get current calendar state."""
        # This would check the user's calendar
        return "free"  # Default to free
    
    async def _get_user_presence(self, user_id: str) -> bool:
        """Get user presence status."""
        # This would check various presence indicators
        return True  # Default to present
