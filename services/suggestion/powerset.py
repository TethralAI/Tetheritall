"""
Powerset Generator
Generates combinations of devices and services with intelligent pruning and optimization.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime
import time
import itertools
import hashlib
import json
from dataclasses import dataclass

from .models import (
    CombinationCandidate, DeviceCapability, ServiceCapability, ContextSnapshot,
    CapabilityType, SuggestionConfig
)

logger = logging.getLogger(__name__)


@dataclass
class PowersetConfig:
    """Configuration for powerset generation."""
    max_combinations: int = 1000
    max_combination_size: int = 5
    min_combination_size: int = 1
    time_budget_ms: int = 5000
    enable_early_pruning: bool = True
    enable_signature_reduction: bool = True
    pruning_threshold: float = 0.1  # Minimum feasibility score to keep


class PowersetGenerator:
    """
    Generates powerset of device and service combinations.
    
    Implements B2 from the spec:
    - Generate combinations from size 1 up to configurable limit
    - Apply early pruning to remove infeasible combinations
    - Collapse equivalent combinations by capability signature
    - Respect strict time budget and always yield candidates
    """
    
    def __init__(self, config: SuggestionConfig):
        self.config = config
        self._outcome_templates = self._initialize_outcome_templates()
        self._pruning_rules = self._initialize_pruning_rules()
        
    async def generate_combinations(
        self,
        capability_graph: Dict[str, Any],
        context_snapshot: ContextSnapshot,
        time_budget_ms: int = 5000
    ) -> List[CombinationCandidate]:
        """
        Generate combinations of devices and services.
        
        Args:
            capability_graph: Graph of available capabilities
            context_snapshot: Current context snapshot
            time_budget_ms: Time budget for generation
            
        Returns:
            List of combination candidates
        """
        start_time = time.time()
        combinations = []
        
        try:
            # Extract devices and services from capability graph
            devices = self._extract_devices_from_graph(capability_graph)
            services = self._extract_services_from_graph(capability_graph)
            
            logger.info(f"Generating combinations from {len(devices)} devices and {len(services)} services")
            
            # Generate combinations of different sizes
            for size in range(self.config.min_combination_size, 
                            min(self.config.max_combination_size + 1, len(devices) + len(services) + 1)):
                
                # Check time budget
                if (time.time() - start_time) * 1000 > time_budget_ms:
                    logger.info(f"Time budget reached, stopping at size {size}")
                    break
                
                # Generate combinations of this size
                size_combinations = await self._generate_size_combinations(
                    devices, services, size, context_snapshot, start_time, time_budget_ms
                )
                
                combinations.extend(size_combinations)
                
                # Check if we have enough combinations
                if len(combinations) >= self.config.max_combinations:
                    logger.info(f"Reached max combinations limit: {len(combinations)}")
                    break
            
            # Apply signature reduction to deduplicate
            if self.config.enable_signature_reduction:
                combinations = self._reduce_by_signature(combinations)
            
            # Sort by estimated value
            combinations.sort(key=lambda c: c.estimated_value, reverse=True)
            
            # Limit to max combinations
            combinations = combinations[:self.config.max_combinations]
            
            logger.info(f"Generated {len(combinations)} unique combinations")
            return combinations
            
        except Exception as e:
            logger.error(f"Error generating combinations: {e}")
            return []
    
    async def _generate_size_combinations(
        self,
        devices: List[DeviceCapability],
        services: List[ServiceCapability],
        size: int,
        context_snapshot: ContextSnapshot,
        start_time: float,
        time_budget_ms: int
    ) -> List[CombinationCandidate]:
        """Generate combinations of a specific size."""
        combinations = []
        
        # Generate all possible combinations of this size
        all_items = devices + services
        
        for item_indices in itertools.combinations(range(len(all_items)), size):
            # Check time budget
            if (time.time() - start_time) * 1000 > time_budget_ms:
                break
            
            # Extract items for this combination
            combination_devices = []
            combination_services = []
            
            for idx in item_indices:
                item = all_items[idx]
                if isinstance(item, DeviceCapability):
                    combination_devices.append(item)
                else:
                    combination_services.append(item)
            
            # Create combination candidate
            candidate = CombinationCandidate(
                devices=combination_devices,
                services=combination_services
            )
            
            # Apply early pruning
            if self.config.enable_early_pruning:
                if not await self._should_keep_combination(candidate, context_snapshot):
                    continue
            
            # Calculate capability signature
            candidate.capability_signature = self._calculate_signature(candidate)
            
            # Estimate initial value
            candidate.estimated_value = await self._estimate_combination_value(
                candidate, context_snapshot
            )
            
            # Check if combination can satisfy any outcome
            if await self._can_satisfy_outcome(candidate):
                combinations.append(candidate)
        
        return combinations
    
    async def _should_keep_combination(
        self,
        candidate: CombinationCandidate,
        context_snapshot: ContextSnapshot
    ) -> bool:
        """Apply early pruning rules to determine if combination should be kept."""
        
        # Rule 1: Check if combination has any devices/services
        if not candidate.devices and not candidate.services:
            return False
        
        # Rule 2: Check for incompatible device combinations
        if not self._check_device_compatibility(candidate.devices):
            return False
        
        # Rule 3: Check for service availability
        if not self._check_service_availability(candidate.services):
            return False
        
        # Rule 4: Check context constraints
        if not self._check_context_constraints(candidate, context_snapshot):
            return False
        
        # Rule 5: Check for obvious infeasibility
        if not self._check_basic_feasibility(candidate):
            return False
        
        return True
    
    def _check_device_compatibility(self, devices: List[DeviceCapability]) -> bool:
        """Check if devices in combination are compatible."""
        # Check for conflicting capabilities
        capability_types = [d.capability_type for d in devices]
        
        # Rule: Can't have multiple devices of same type in same room
        room_devices = {}
        for device in devices:
            if device.room:
                if device.room not in room_devices:
                    room_devices[device.room] = []
                room_devices[device.room].append(device.capability_type)
        
        # Check for conflicts in same room
        for room, capabilities in room_devices.items():
            if len(set(capabilities)) != len(capabilities):
                # Duplicate capability types in same room
                return False
        
        return True
    
    def _check_service_availability(self, services: List[ServiceCapability]) -> bool:
        """Check if services in combination are available."""
        for service in services:
            if not service.available:
                return False
        return True
    
    def _check_context_constraints(
        self,
        candidate: CombinationCandidate,
        context_snapshot: ContextSnapshot
    ) -> bool:
        """Check if combination respects context constraints."""
        
        # Check quiet hours constraints
        if context_snapshot.is_quiet_hours:
            for device in candidate.devices:
                if device.capability_type == CapabilityType.AUDIO:
                    # Check if audio is allowed during quiet hours
                    if not self._is_safety_related(candidate):
                        return False
        
        # Check user presence constraints
        if not context_snapshot.user_present:
            for device in candidate.devices:
                if device.capability_type in [CapabilityType.SECURITY, CapabilityType.ACCESS_CONTROL]:
                    # Security devices might not work when user is away
                    return False
        
        return True
    
    def _check_basic_feasibility(self, candidate: CombinationCandidate) -> bool:
        """Check basic feasibility of combination."""
        
        # Must have at least one device or service
        if not candidate.devices and not candidate.services:
            return False
        
        # Check if devices are reachable
        for device in candidate.devices:
            if not device.reachable:
                return False
        
        return True
    
    def _is_safety_related(self, candidate: CombinationCandidate) -> bool:
        """Check if combination is safety-related."""
        safety_capabilities = [
            CapabilityType.SECURITY,
            CapabilityType.ACCESS_CONTROL,
            CapabilityType.SENSING  # Motion sensors for safety
        ]
        
        for device in candidate.devices:
            if device.capability_type in safety_capabilities:
                return True
        
        return False
    
    def _calculate_signature(self, candidate: CombinationCandidate) -> str:
        """Calculate capability signature for deduplication."""
        # Create normalized signature based on capability types
        device_signatures = []
        for device in candidate.devices:
            device_signatures.append(f"{device.capability_type.value}:{device.room or 'unknown'}")
        
        service_signatures = []
        for service in candidate.services:
            service_signatures.append(f"{service.capability_type.value}")
        
        # Sort for consistent signatures
        device_signatures.sort()
        service_signatures.sort()
        
        # Combine and hash
        signature_data = f"devices:{','.join(device_signatures)};services:{','.join(service_signatures)}"
        return hashlib.md5(signature_data.encode()).hexdigest()
    
    def _reduce_by_signature(self, combinations: List[CombinationCandidate]) -> List[CombinationCandidate]:
        """Reduce combinations by removing duplicates with same signature."""
        seen_signatures = set()
        unique_combinations = []
        
        for combination in combinations:
            if combination.capability_signature not in seen_signatures:
                seen_signatures.add(combination.capability_signature)
                unique_combinations.append(combination)
        
        logger.info(f"Reduced {len(combinations)} to {len(unique_combinations)} unique combinations")
        return unique_combinations
    
    async def _estimate_combination_value(
        self,
        candidate: CombinationCandidate,
        context_snapshot: ContextSnapshot
    ) -> float:
        """Estimate the value of a combination."""
        value = 0.0
        
        # Base value from number of capabilities
        value += len(candidate.devices) * 0.1
        value += len(candidate.services) * 0.05
        
        # Value from capability types
        for device in candidate.devices:
            value += self._get_capability_value(device.capability_type, context_snapshot)
        
        for service in candidate.services:
            value += self._get_capability_value(service.capability_type, context_snapshot)
        
        # Context fit bonus
        context_bonus = self._calculate_context_fit(candidate, context_snapshot)
        value += context_bonus
        
        # Novelty bonus (combinations with more diverse capabilities)
        novelty_bonus = self._calculate_novelty_bonus(candidate)
        value += novelty_bonus
        
        return max(0.0, value)
    
    def _get_capability_value(self, capability_type: CapabilityType, context_snapshot: ContextSnapshot) -> float:
        """Get base value for a capability type."""
        base_values = {
            CapabilityType.LIGHTING: 0.3,
            CapabilityType.SENSING: 0.4,
            CapabilityType.ACTUATION: 0.2,
            CapabilityType.AUDIO: 0.2,
            CapabilityType.VIDEO: 0.5,
            CapabilityType.SECURITY: 0.6,
            CapabilityType.CLIMATE: 0.4,
            CapabilityType.ENERGY: 0.3,
            CapabilityType.ACCESS_CONTROL: 0.5,
            CapabilityType.NETWORK: 0.1,
            CapabilityType.WEATHER: 0.2,
            CapabilityType.CALENDAR: 0.3,
            CapabilityType.PRESENCE: 0.4,
            CapabilityType.TIME: 0.1,
            CapabilityType.LOCATION: 0.3,
            CapabilityType.TRAFFIC: 0.2,
            CapabilityType.NOTIFICATION: 0.1
        }
        
        return base_values.get(capability_type, 0.1)
    
    def _calculate_context_fit(
        self,
        candidate: CombinationCandidate,
        context_snapshot: ContextSnapshot
    ) -> float:
        """Calculate how well combination fits current context."""
        fit_score = 0.0
        
        # Time of day fit
        if context_snapshot.is_quiet_hours:
            # Prefer quiet, non-disruptive combinations
            if not any(d.capability_type == CapabilityType.AUDIO for d in candidate.devices):
                fit_score += 0.2
        
        # Weekend vs weekday fit
        if context_snapshot.is_weekend:
            # Prefer comfort and entertainment combinations
            if any(d.capability_type == CapabilityType.LIGHTING for d in candidate.devices):
                fit_score += 0.1
        
        # Weather fit
        if context_snapshot.weather_conditions:
            weather = context_snapshot.weather_conditions.get("condition", "")
            if weather in ["rain", "snow"] and any(d.capability_type == CapabilityType.LIGHTING for d in candidate.devices):
                fit_score += 0.1
        
        return fit_score
    
    def _calculate_novelty_bonus(self, candidate: CombinationCandidate) -> float:
        """Calculate novelty bonus for diverse combinations."""
        capability_types = set()
        
        for device in candidate.devices:
            capability_types.add(device.capability_type)
        
        for service in candidate.services:
            capability_types.add(service.capability_type)
        
        # Bonus for diverse capability types
        diversity_bonus = len(capability_types) * 0.05
        
        # Bonus for device-service combinations
        if candidate.devices and candidate.services:
            diversity_bonus += 0.1
        
        return diversity_bonus
    
    async def _can_satisfy_outcome(self, candidate: CombinationCandidate) -> bool:
        """Check if combination can satisfy any known outcome."""
        # Check against outcome templates
        for template in self._outcome_templates:
            if self._combination_matches_template(candidate, template):
                return True
        
        return True  # Default to allowing if no specific match
    
    def _combination_matches_template(
        self,
        candidate: CombinationCandidate,
        template: Dict[str, Any]
    ) -> bool:
        """Check if combination matches an outcome template."""
        required_capabilities = template.get("required_capabilities", [])
        
        candidate_capabilities = set()
        for device in candidate.devices:
            candidate_capabilities.add(device.capability_type.value)
        for service in candidate.services:
            candidate_capabilities.add(service.capability_type.value)
        
        # Check if all required capabilities are present
        for required in required_capabilities:
            if required not in candidate_capabilities:
                return False
        
        return True
    
    def _extract_devices_from_graph(self, capability_graph: Dict[str, Any]) -> List[DeviceCapability]:
        """Extract device capabilities from capability graph."""
        devices = []
        
        for device_id, device_info in capability_graph.get("devices", {}).items():
            for capability_info in device_info.get("capabilities", []):
                device = DeviceCapability(
                    capability_type=CapabilityType(capability_info["type"]),
                    device_id=device_id,
                    device_name=device_info["name"],
                    device_brand=device_info["brand"],
                    device_model=device_info["model"],
                    room=device_info.get("room"),
                    zone=device_info.get("zone"),
                    parameters=capability_info.get("parameters", {}),
                    constraints=capability_info.get("constraints", {}),
                    reachable=device_info.get("reachable", True)
                )
                devices.append(device)
        
        return devices
    
    def _extract_services_from_graph(self, capability_graph: Dict[str, Any]) -> List[ServiceCapability]:
        """Extract service capabilities from capability graph."""
        services = []
        
        for service_id, service_info in capability_graph.get("services", {}).items():
            service = ServiceCapability(
                capability_type=CapabilityType(service_info["type"]),
                service_name=service_info["name"],
                service_id=service_id,
                parameters=service_info.get("parameters", {}),
                constraints=service_info.get("constraints", {}),
                available=service_info.get("available", True)
            )
            services.append(service)
        
        return services
    
    def _initialize_outcome_templates(self) -> List[Dict[str, Any]]:
        """Initialize outcome templates for feasibility checking."""
        return [
            {
                "name": "Safe Arrival",
                "required_capabilities": ["lighting", "sensing"],
                "category": "safety"
            },
            {
                "name": "Energy Saver",
                "required_capabilities": ["actuation", "sensing"],
                "category": "energy"
            },
            {
                "name": "Comfort Enhancement",
                "required_capabilities": ["lighting", "climate"],
                "category": "comfort"
            },
            {
                "name": "Security Monitoring",
                "required_capabilities": ["sensing", "video"],
                "category": "security"
            },
            {
                "name": "Weather Response",
                "required_capabilities": ["weather", "actuation"],
                "category": "automation"
            }
        ]
    
    def _initialize_pruning_rules(self) -> List[Dict[str, Any]]:
        """Initialize pruning rules for early filtering."""
        return [
            {
                "name": "incompatible_devices",
                "description": "Remove combinations with incompatible devices",
                "enabled": True
            },
            {
                "name": "unavailable_services",
                "description": "Remove combinations with unavailable services",
                "enabled": True
            },
            {
                "name": "context_violations",
                "description": "Remove combinations that violate context constraints",
                "enabled": True
            }
        ]
