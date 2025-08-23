"""
Feasibility Scanner

Checks device readiness, protocol support, energy and time estimates.
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .models import (
    FeasibilityResult, FeasibilityStatus, ResourceCapability, ResourceType,
    ExecutionStep, StepType
)

logger = logging.getLogger(__name__)


@dataclass
class DeviceHealth:
    """Device health information."""
    device_id: str
    online: bool
    battery_level: float
    signal_strength: float
    last_seen: datetime
    error_count: int
    maintenance_due: bool


@dataclass
class ProtocolSupport:
    """Protocol support information."""
    protocol: str
    supported: bool
    version: str
    capabilities: List[str]
    performance_rating: float


class MockDeviceRegistry:
    """Mock device registry for feasibility checking."""
    
    def __init__(self):
        self._devices = {
            "thermostat_living": {
                "id": "thermostat_living",
                "type": ResourceType.DEVICE,
                "capabilities": ["temperature_control", "scheduling", "remote_access"],
                "protocols": ["zigbee", "wifi", "http"],
                "power_state": "online",
                "network_quality": 0.95,
                "bandwidth_mbps": 100.0,
                "latency_ms": 5.0,
                "cost_per_hour": 0.001,
                "available_slots": 3,
                "current_load": 0.3,
                "last_heartbeat": datetime.utcnow(),
                "health": DeviceHealth(
                    device_id="thermostat_living",
                    online=True,
                    battery_level=0.85,
                    signal_strength=0.9,
                    last_seen=datetime.utcnow(),
                    error_count=0,
                    maintenance_due=False
                )
            },
            "light_bulb_1": {
                "id": "light_bulb_1",
                "type": ResourceType.DEVICE,
                "capabilities": ["dimmable_lighting", "color_control", "motion_sensing"],
                "protocols": ["zigbee", "wifi"],
                "power_state": "online",
                "network_quality": 0.88,
                "bandwidth_mbps": 50.0,
                "latency_ms": 8.0,
                "cost_per_hour": 0.0005,
                "available_slots": 2,
                "current_load": 0.1,
                "last_heartbeat": datetime.utcnow(),
                "health": DeviceHealth(
                    device_id="light_bulb_1",
                    online=True,
                    battery_level=1.0,  # Plugged in
                    signal_strength=0.85,
                    last_seen=datetime.utcnow(),
                    error_count=1,
                    maintenance_due=False
                )
            },
            "edge_gateway_1": {
                "id": "edge_gateway_1",
                "type": ResourceType.EDGE_COMPUTE,
                "capabilities": ["local_processing", "data_aggregation", "protocol_translation"],
                "protocols": ["mqtt", "http", "coap", "zigbee"],
                "power_state": "online",
                "network_quality": 0.98,
                "bandwidth_mbps": 1000.0,
                "latency_ms": 2.0,
                "cost_per_hour": 0.01,
                "available_slots": 10,
                "current_load": 0.4,
                "last_heartbeat": datetime.utcnow(),
                "health": DeviceHealth(
                    device_id="edge_gateway_1",
                    online=True,
                    battery_level=1.0,  # Plugged in
                    signal_strength=1.0,
                    last_seen=datetime.utcnow(),
                    error_count=0,
                    maintenance_due=False
                )
            },
            "cloud_region_us_east": {
                "id": "cloud_region_us_east",
                "type": ResourceType.CLOUD_COMPUTE,
                "capabilities": ["ml_inference", "data_analysis", "long_term_storage"],
                "protocols": ["http", "grpc", "websocket"],
                "power_state": "online",
                "network_quality": 0.99,
                "bandwidth_mbps": 10000.0,
                "latency_ms": 50.0,
                "cost_per_hour": 0.05,
                "available_slots": 100,
                "current_load": 0.6,
                "last_heartbeat": datetime.utcnow(),
                "health": DeviceHealth(
                    device_id="cloud_region_us_east",
                    online=True,
                    battery_level=1.0,
                    signal_strength=1.0,
                    last_seen=datetime.utcnow(),
                    error_count=0,
                    maintenance_due=False
                )
            }
        }
    
    async def get_device_capabilities(self, device_id: str) -> Optional[ResourceCapability]:
        """Get device capabilities."""
        device = self._devices.get(device_id)
        if not device:
            return None
        
        return ResourceCapability(
            resource_id=device["id"],
            resource_type=device["type"],
            capabilities=device["capabilities"],
            protocols=device["protocols"],
            power_state=device["power_state"],
            network_quality=device["network_quality"],
            bandwidth_mbps=device["bandwidth_mbps"],
            latency_ms=device["latency_ms"],
            cost_per_hour=device["cost_per_hour"],
            available_slots=device["available_slots"],
            current_load=device["current_load"],
            last_heartbeat=device["last_heartbeat"],
            metadata={"health": device["health"]}
        )
    
    async def get_all_devices(self) -> List[ResourceCapability]:
        """Get all available devices."""
        devices = []
        for device_id in self._devices:
            device = await self.get_device_capabilities(device_id)
            if device:
                devices.append(device)
        return devices
    
    async def get_devices_by_capability(self, capability: str) -> List[ResourceCapability]:
        """Get devices that support a specific capability."""
        devices = []
        for device_id, device_data in self._devices.items():
            if capability in device_data["capabilities"]:
                device = await self.get_device_capabilities(device_id)
                if device:
                    devices.append(device)
        return devices


class FeasibilityScanner:
    """
    Checks device readiness, protocol support, energy and time estimates.
    """
    
    def __init__(self):
        self._running = False
        self._device_registry = MockDeviceRegistry()
        self._protocol_requirements = {
            StepType.DEVICE_CONTROL: ["zigbee", "wifi", "http", "mqtt"],
            StepType.DATA_COLLECTION: ["http", "mqtt", "coap"],
            StepType.ML_INFERENCE: ["http", "grpc"],
            StepType.NOTIFICATION: ["http", "websocket", "mqtt"],
            StepType.DATA_ANALYSIS: ["http", "grpc"],
            StepType.STORAGE_OPERATION: ["http", "grpc"]
        }
        self._energy_estimates = {
            StepType.DEVICE_CONTROL: {"min": 0.1, "max": 2.0, "avg": 0.5},
            StepType.DATA_COLLECTION: {"min": 0.05, "max": 1.0, "avg": 0.2},
            StepType.ML_INFERENCE: {"min": 1.0, "max": 10.0, "avg": 3.0},
            StepType.NOTIFICATION: {"min": 0.01, "max": 0.5, "avg": 0.1},
            StepType.DATA_ANALYSIS: {"min": 0.5, "max": 5.0, "avg": 1.5},
            StepType.STORAGE_OPERATION: {"min": 0.1, "max": 2.0, "avg": 0.8}
        }
        self._time_estimates = {
            StepType.DEVICE_CONTROL: {"min": 100, "max": 2000, "avg": 500},
            StepType.DATA_COLLECTION: {"min": 50, "max": 1000, "avg": 200},
            StepType.ML_INFERENCE: {"min": 500, "max": 10000, "avg": 2000},
            StepType.NOTIFICATION: {"min": 10, "max": 500, "avg": 100},
            StepType.DATA_ANALYSIS: {"min": 200, "max": 5000, "avg": 1000},
            StepType.STORAGE_OPERATION: {"min": 100, "max": 3000, "avg": 800}
        }
    
    async def start(self):
        """Start the feasibility scanner."""
        self._running = True
        logger.info("Feasibility scanner started")
    
    async def stop(self):
        """Stop the feasibility scanner."""
        self._running = False
        logger.info("Feasibility scanner stopped")
    
    async def check_feasibility(self, step: ExecutionStep) -> FeasibilityResult:
        """
        Check feasibility for a single step.
        
        This checks:
        - Device readiness and health
        - Protocol support
        - Energy requirements
        - Time estimates
        - Network requirements
        """
        if not self._running:
            raise RuntimeError("Feasibility scanner is not running")
        
        try:
            logger.debug(f"Checking feasibility for step {step.step_id}")
            
            # Get compatible resources
            compatible_resources = await self._find_compatible_resources(step)
            
            if not compatible_resources:
                return FeasibilityResult(
                    step_id=step.step_id,
                    status=FeasibilityStatus.INFEASIBLE,
                    compatible_resources=[],
                    estimated_energy_wh=0.0,
                    estimated_time_ms=0,
                    protocol_support=False,
                    power_requirement_met=False,
                    network_requirement_met=False,
                    errors=["No compatible resources found"]
                )
            
            # Check protocol support
            protocol_support = self._check_protocol_support(step, compatible_resources)
            
            # Check power requirements
            power_requirement_met = self._check_power_requirements(step, compatible_resources)
            
            # Check network requirements
            network_requirement_met = self._check_network_requirements(step, compatible_resources)
            
            # Calculate energy and time estimates
            estimated_energy = self._estimate_energy_consumption(step)
            estimated_time = self._estimate_execution_time(step)
            
            # Determine overall feasibility
            status = self._determine_feasibility_status(
                compatible_resources, protocol_support, power_requirement_met,
                network_requirement_met
            )
            
            # Collect warnings
            warnings = self._collect_warnings(
                step, compatible_resources, protocol_support, power_requirement_met,
                network_requirement_met
            )
            
            return FeasibilityResult(
                step_id=step.step_id,
                status=status,
                compatible_resources=compatible_resources,
                estimated_energy_wh=estimated_energy,
                estimated_time_ms=estimated_time,
                protocol_support=protocol_support,
                power_requirement_met=power_requirement_met,
                network_requirement_met=network_requirement_met,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Error checking feasibility for step {step.step_id}: {e}")
            return FeasibilityResult(
                step_id=step.step_id,
                status=FeasibilityStatus.UNKNOWN,
                compatible_resources=[],
                estimated_energy_wh=0.0,
                estimated_time_ms=0,
                protocol_support=False,
                power_requirement_met=False,
                network_requirement_met=False,
                errors=[f"Feasibility check error: {str(e)}"]
            )
    
    async def _find_compatible_resources(self, step: ExecutionStep) -> List[ResourceCapability]:
        """Find resources compatible with the step requirements."""
        compatible_resources = []
        
        # Get all devices
        all_devices = await self._device_registry.get_all_devices()
        
        for device in all_devices:
            if self._is_resource_compatible(step, device):
                compatible_resources.append(device)
        
        # Sort by suitability (better resources first)
        compatible_resources.sort(key=lambda r: self._calculate_resource_suitability(step, r), reverse=True)
        
        return compatible_resources
    
    def _is_resource_compatible(self, step: ExecutionStep, resource: ResourceCapability) -> bool:
        """Check if a resource is compatible with the step."""
        # Check if resource is online and healthy
        if resource.power_state != "online":
            return False
        
        # Check if resource has available slots
        if resource.available_slots <= 0:
            return False
        
        # Check if resource is not overloaded
        if resource.current_load > 0.9:  # 90% load threshold
            return False
        
        # Check if resource supports required capabilities
        if step.target_device and step.target_device not in resource.capabilities:
            return False
        
        # Check if resource supports required protocols
        required_protocols = self._protocol_requirements.get(step.step_type, [])
        if required_protocols and not any(p in resource.protocols for p in required_protocols):
            return False
        
        return True
    
    def _calculate_resource_suitability(self, step: ExecutionStep, resource: ResourceCapability) -> float:
        """Calculate how suitable a resource is for the step."""
        suitability = 0.0
        
        # Network quality (30% weight)
        suitability += resource.network_quality * 0.3
        
        # Available capacity (25% weight)
        capacity_score = 1.0 - resource.current_load
        suitability += capacity_score * 0.25
        
        # Cost efficiency (20% weight)
        cost_score = 1.0 / (1.0 + resource.cost_per_hour)
        suitability += cost_score * 0.2
        
        # Latency (15% weight)
        latency_score = 1.0 / (1.0 + resource.latency_ms / 100.0)
        suitability += latency_score * 0.15
        
        # Protocol match (10% weight)
        required_protocols = self._protocol_requirements.get(step.step_type, [])
        if required_protocols:
            protocol_match = sum(1 for p in required_protocols if p in resource.protocols) / len(required_protocols)
            suitability += protocol_match * 0.1
        
        return suitability
    
    def _check_protocol_support(self, step: ExecutionStep, resources: List[ResourceCapability]) -> bool:
        """Check if any resource supports the required protocols."""
        required_protocols = self._protocol_requirements.get(step.step_type, [])
        if not required_protocols:
            return True  # No protocol requirements
        
        for resource in resources:
            if any(p in resource.protocols for p in required_protocols):
                return True
        
        return False
    
    def _check_power_requirements(self, step: ExecutionStep, resources: List[ResourceCapability]) -> bool:
        """Check if power requirements can be met."""
        for resource in resources:
            # Check if device has sufficient battery or is plugged in
            health = resource.metadata.get("health")
            if health and hasattr(health, "battery_level"):
                if health.battery_level > 0.2 or health.battery_level == 1.0:  # Plugged in
                    return True
            else:
                # Assume plugged in if no battery info
                return True
        
        return False
    
    def _check_network_requirements(self, step: ExecutionStep, resources: List[ResourceCapability]) -> bool:
        """Check if network requirements can be met."""
        for resource in resources:
            # Check network quality
            if resource.network_quality < 0.5:
                continue
            
            # Check bandwidth (basic requirement)
            if resource.bandwidth_mbps < 1.0:
                continue
            
            # Check latency (basic requirement)
            if resource.latency_ms > 1000:
                continue
            
            return True
        
        return False
    
    def _estimate_energy_consumption(self, step: ExecutionStep) -> float:
        """Estimate energy consumption for the step."""
        estimates = self._energy_estimates.get(step.step_type, {"avg": 1.0})
        
        # Add some randomness to simulate real-world variation
        base_energy = estimates["avg"]
        variation = random.uniform(0.8, 1.2)
        
        return base_energy * variation
    
    def _estimate_execution_time(self, step: ExecutionStep) -> int:
        """Estimate execution time for the step."""
        estimates = self._time_estimates.get(step.step_type, {"avg": 1000})
        
        # Add some randomness to simulate real-world variation
        base_time = estimates["avg"]
        variation = random.uniform(0.7, 1.3)
        
        return int(base_time * variation)
    
    def _determine_feasibility_status(
        self,
        compatible_resources: List[ResourceCapability],
        protocol_support: bool,
        power_requirement_met: bool,
        network_requirement_met: bool
    ) -> FeasibilityStatus:
        """Determine the overall feasibility status."""
        if not compatible_resources:
            return FeasibilityStatus.INFEASIBLE
        
        if not protocol_support:
            return FeasibilityStatus.INFEASIBLE
        
        if not power_requirement_met:
            return FeasibilityStatus.INFEASIBLE
        
        if not network_requirement_met:
            return FeasibilityStatus.INFEASIBLE
        
        # Check if we have optimal resources
        optimal_resources = [r for r in compatible_resources if r.network_quality > 0.8 and r.current_load < 0.5]
        
        if optimal_resources:
            return FeasibilityStatus.FEASIBLE
        else:
            return FeasibilityStatus.DEGRADED
    
    def _collect_warnings(
        self,
        step: ExecutionStep,
        compatible_resources: List[ResourceCapability],
        protocol_support: bool,
        power_requirement_met: bool,
        network_requirement_met: bool
    ) -> List[str]:
        """Collect warnings about the feasibility check."""
        warnings = []
        
        if len(compatible_resources) < 2:
            warnings.append("Limited resource options available")
        
        for resource in compatible_resources:
            if resource.current_load > 0.7:
                warnings.append(f"Resource {resource.resource_id} is under high load")
            
            if resource.network_quality < 0.8:
                warnings.append(f"Resource {resource.resource_id} has poor network quality")
            
            health = resource.metadata.get("health")
            if health and hasattr(health, "error_count") and health.error_count > 0:
                warnings.append(f"Resource {resource.resource_id} has recent errors")
        
        return warnings
