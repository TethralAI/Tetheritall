"""
Placement Decider

Chooses edge, cloud, or hybrid per step based on constraints and privacy class.
"""

import asyncio
import logging
import random
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .models import (
    PlacementDecision, PlacementTarget, ResourceCapability, FeasibilityResult,
    ExecutionStep, AllocationRequest, PrivacyClass, StepType
)
from .resource_allocator import ResourceAllocatorConfig

logger = logging.getLogger(__name__)


@dataclass
class PlacementStrategy:
    """Placement strategy configuration."""
    name: str
    privacy_weight: float
    cost_weight: float
    latency_weight: float
    energy_weight: float
    reliability_weight: float
    local_preference: float
    cloud_preference: float
    edge_preference: float


class PlacementDecider:
    """
    Chooses edge, cloud, or hybrid per step based on constraints and privacy class.
    """
    
    def __init__(self, config: ResourceAllocatorConfig):
        self.config = config
        self._running = False
        self._strategies = self._initialize_strategies()
        self._placement_rules = self._initialize_placement_rules()
        self._cost_models = self._initialize_cost_models()
        self._latency_models = self._initialize_latency_models()
    
    async def start(self):
        """Start the placement decider."""
        self._running = True
        logger.info("Placement decider started")
    
    async def stop(self):
        """Stop the placement decider."""
        self._running = False
        logger.info("Placement decider stopped")
    
    async def decide_placement(
        self, 
        step: ExecutionStep, 
        feasibility: FeasibilityResult,
        request: AllocationRequest
    ) -> PlacementDecision:
        """
        Decide placement for a single step.
        
        This considers:
        - Privacy requirements
        - Cost constraints
        - Latency requirements
        - Energy efficiency
        - Reliability needs
        - Available resources
        """
        if not self._running:
            raise RuntimeError("Placement decider is not running")
        
        try:
            logger.debug(f"Deciding placement for step {step.step_id}")
            
            # Determine placement strategy
            strategy = self._determine_strategy(step, request)
            
            # Filter compatible resources by placement target
            local_resources = self._filter_resources_by_target(
                feasibility.compatible_resources, PlacementTarget.LOCAL_DEVICE
            )
            edge_resources = self._filter_resources_by_target(
                feasibility.compatible_resources, PlacementTarget.EDGE_GATEWAY
            )
            cloud_resources = self._filter_resources_by_target(
                feasibility.compatible_resources, PlacementTarget.CLOUD_REGION
            )
            
            # Apply placement rules
            target, primary_resource = self._apply_placement_rules(
                step, strategy, local_resources, edge_resources, cloud_resources, request
            )
            
            if not primary_resource:
                # Fallback to best available resource
                all_resources = feasibility.compatible_resources
                if all_resources:
                    primary_resource = all_resources[0]
                    target = self._determine_target_from_resource(primary_resource)
                else:
                    raise ValueError(f"No compatible resources for step {step.step_id}")
            
            # Select fallback resources
            fallback_resources = self._select_fallback_resources(
                step, target, feasibility.compatible_resources, primary_resource
            )
            
            # Calculate metrics
            expected_cost = self._calculate_expected_cost(step, primary_resource, target)
            expected_latency = self._calculate_expected_latency(step, primary_resource, target)
            privacy_score = self._calculate_privacy_score(step, target, request)
            energy_efficiency = self._calculate_energy_efficiency(step, primary_resource, target)
            reliability_score = self._calculate_reliability_score(step, primary_resource, target)
            
            # Generate rationale
            rationale = self._generate_placement_rationale(
                step, target, primary_resource, strategy, expected_cost, expected_latency,
                privacy_score, energy_efficiency, reliability_score
            )
            
            return PlacementDecision(
                step_id=step.step_id,
                target=target,
                primary_resource=primary_resource,
                fallback_resources=fallback_resources,
                rationale=rationale,
                expected_cost=expected_cost,
                expected_latency_ms=expected_latency,
                privacy_score=privacy_score,
                energy_efficiency=energy_efficiency,
                reliability_score=reliability_score
            )
            
        except Exception as e:
            logger.error(f"Error deciding placement for step {step.step_id}: {e}")
            # Return a default placement decision
            if feasibility.compatible_resources:
                default_resource = feasibility.compatible_resources[0]
                return PlacementDecision(
                    step_id=step.step_id,
                    target=PlacementTarget.LOCAL_DEVICE,
                    primary_resource=default_resource,
                    fallback_resources=[],
                    rationale=f"Default placement due to error: {str(e)}",
                    expected_cost=0.0,
                    expected_latency_ms=0,
                    privacy_score=0.5,
                    energy_efficiency=0.5,
                    reliability_score=0.5
                )
            else:
                raise
    
    def _initialize_strategies(self) -> Dict[str, PlacementStrategy]:
        """Initialize placement strategies."""
        return {
            "privacy_first": PlacementStrategy(
                name="privacy_first",
                privacy_weight=0.6,
                cost_weight=0.1,
                latency_weight=0.1,
                energy_weight=0.1,
                reliability_weight=0.1,
                local_preference=0.8,
                cloud_preference=0.1,
                edge_preference=0.1
            ),
            "cost_optimized": PlacementStrategy(
                name="cost_optimized",
                privacy_weight=0.1,
                cost_weight=0.6,
                latency_weight=0.1,
                energy_weight=0.1,
                reliability_weight=0.1,
                local_preference=0.7,
                cloud_preference=0.2,
                edge_preference=0.1
            ),
            "latency_optimized": PlacementStrategy(
                name="latency_optimized",
                privacy_weight=0.1,
                cost_weight=0.1,
                latency_weight=0.6,
                energy_weight=0.1,
                reliability_weight=0.1,
                local_preference=0.6,
                cloud_preference=0.2,
                edge_preference=0.2
            ),
            "energy_efficient": PlacementStrategy(
                name="energy_efficient",
                privacy_weight=0.1,
                cost_weight=0.1,
                latency_weight=0.1,
                energy_weight=0.6,
                reliability_weight=0.1,
                local_preference=0.5,
                cloud_preference=0.3,
                edge_preference=0.2
            ),
            "balanced": PlacementStrategy(
                name="balanced",
                privacy_weight=0.2,
                cost_weight=0.2,
                latency_weight=0.2,
                energy_weight=0.2,
                reliability_weight=0.2,
                local_preference=0.6,
                cloud_preference=0.2,
                edge_preference=0.2
            )
        }
    
    def _initialize_placement_rules(self) -> Dict[str, Any]:
        """Initialize placement rules."""
        return {
            "privacy_rules": {
                PrivacyClass.RESTRICTED: [PlacementTarget.LOCAL_DEVICE],
                PrivacyClass.CONFIDENTIAL: [PlacementTarget.LOCAL_DEVICE, PlacementTarget.EDGE_GATEWAY],
                PrivacyClass.INTERNAL: [PlacementTarget.LOCAL_DEVICE, PlacementTarget.EDGE_GATEWAY, PlacementTarget.EDGE_CLUSTER],
                PrivacyClass.PUBLIC: [PlacementTarget.LOCAL_DEVICE, PlacementTarget.EDGE_GATEWAY, PlacementTarget.EDGE_CLUSTER, PlacementTarget.CLOUD_REGION]
            },
            "step_type_rules": {
                StepType.DEVICE_CONTROL: [PlacementTarget.LOCAL_DEVICE, PlacementTarget.EDGE_GATEWAY],
                StepType.DATA_COLLECTION: [PlacementTarget.LOCAL_DEVICE, PlacementTarget.EDGE_GATEWAY],
                StepType.ML_INFERENCE: [PlacementTarget.EDGE_GATEWAY, PlacementTarget.EDGE_CLUSTER, PlacementTarget.CLOUD_REGION],
                StepType.NOTIFICATION: [PlacementTarget.LOCAL_DEVICE, PlacementTarget.EDGE_GATEWAY, PlacementTarget.CLOUD_REGION],
                StepType.DATA_ANALYSIS: [PlacementTarget.EDGE_CLUSTER, PlacementTarget.CLOUD_REGION],
                StepType.STORAGE_OPERATION: [PlacementTarget.EDGE_GATEWAY, PlacementTarget.EDGE_CLUSTER, PlacementTarget.CLOUD_REGION]
            },
            "constraint_rules": {
                "max_latency_ms": {
                    10: [PlacementTarget.LOCAL_DEVICE],
                    50: [PlacementTarget.LOCAL_DEVICE, PlacementTarget.EDGE_GATEWAY],
                    200: [PlacementTarget.LOCAL_DEVICE, PlacementTarget.EDGE_GATEWAY, PlacementTarget.EDGE_CLUSTER],
                    1000: [PlacementTarget.LOCAL_DEVICE, PlacementTarget.EDGE_GATEWAY, PlacementTarget.EDGE_CLUSTER, PlacementTarget.CLOUD_REGION]
                },
                "max_cost_per_hour": {
                    0.001: [PlacementTarget.LOCAL_DEVICE],
                    0.01: [PlacementTarget.LOCAL_DEVICE, PlacementTarget.EDGE_GATEWAY],
                    0.1: [PlacementTarget.LOCAL_DEVICE, PlacementTarget.EDGE_GATEWAY, PlacementTarget.EDGE_CLUSTER],
                    1.0: [PlacementTarget.LOCAL_DEVICE, PlacementTarget.EDGE_GATEWAY, PlacementTarget.EDGE_CLUSTER, PlacementTarget.CLOUD_REGION]
                }
            }
        }
    
    def _initialize_cost_models(self) -> Dict[PlacementTarget, Dict[str, float]]:
        """Initialize cost models for different placement targets."""
        return {
            PlacementTarget.LOCAL_DEVICE: {
                "base_cost": 0.0,
                "compute_cost": 0.0,
                "network_cost": 0.0,
                "storage_cost": 0.0
            },
            PlacementTarget.EDGE_GATEWAY: {
                "base_cost": 0.001,
                "compute_cost": 0.002,
                "network_cost": 0.001,
                "storage_cost": 0.001
            },
            PlacementTarget.EDGE_CLUSTER: {
                "base_cost": 0.005,
                "compute_cost": 0.01,
                "network_cost": 0.002,
                "storage_cost": 0.003
            },
            PlacementTarget.CLOUD_REGION: {
                "base_cost": 0.01,
                "compute_cost": 0.05,
                "network_cost": 0.005,
                "storage_cost": 0.01
            }
        }
    
    def _initialize_latency_models(self) -> Dict[PlacementTarget, Dict[str, int]]:
        """Initialize latency models for different placement targets."""
        return {
            PlacementTarget.LOCAL_DEVICE: {
                "base_latency": 1,
                "network_latency": 0,
                "processing_latency": 10,
                "total_latency": 11
            },
            PlacementTarget.EDGE_GATEWAY: {
                "base_latency": 5,
                "network_latency": 10,
                "processing_latency": 50,
                "total_latency": 65
            },
            PlacementTarget.EDGE_CLUSTER: {
                "base_latency": 10,
                "network_latency": 20,
                "processing_latency": 100,
                "total_latency": 130
            },
            PlacementTarget.CLOUD_REGION: {
                "base_latency": 50,
                "network_latency": 100,
                "processing_latency": 200,
                "total_latency": 350
            }
        }
    
    def _determine_strategy(self, step: ExecutionStep, request: AllocationRequest) -> PlacementStrategy:
        """Determine the placement strategy based on step and request."""
        # Check if privacy-first is explicitly requested
        if request.privacy_requirements.get("privacy_first", False):
            return self._strategies["privacy_first"]
        
        # Check if cost optimization is requested
        if request.cost_budget and request.cost_budget < 0.01:
            return self._strategies["cost_optimized"]
        
        # Check if latency optimization is requested
        if request.latency_budget_ms and request.latency_budget_ms < 100:
            return self._strategies["latency_optimized"]
        
        # Check if energy efficiency is requested
        if request.energy_constraints.get("energy_efficient", False):
            return self._strategies["energy_efficient"]
        
        # Default to balanced strategy
        return self._strategies["balanced"]
    
    def _filter_resources_by_target(
        self, 
        resources: List[ResourceCapability], 
        target: PlacementTarget
    ) -> List[ResourceCapability]:
        """Filter resources by placement target."""
        filtered = []
        for resource in resources:
            if self._resource_matches_target(resource, target):
                filtered.append(resource)
        return filtered
    
    def _resource_matches_target(self, resource: ResourceCapability, target: PlacementTarget) -> bool:
        """Check if a resource matches a placement target."""
        if target == PlacementTarget.LOCAL_DEVICE:
            return resource.resource_type.value in ["device", "sensor", "actuator"]
        elif target == PlacementTarget.EDGE_GATEWAY:
            return resource.resource_type.value == "edge_compute"
        elif target == PlacementTarget.EDGE_CLUSTER:
            return resource.resource_type.value == "edge_compute" and resource.cost_per_hour > 0.005
        elif target == PlacementTarget.CLOUD_REGION:
            return resource.resource_type.value == "cloud_compute"
        else:
            return True
    
    def _apply_placement_rules(
        self,
        step: ExecutionStep,
        strategy: PlacementStrategy,
        local_resources: List[ResourceCapability],
        edge_resources: List[ResourceCapability],
        cloud_resources: List[ResourceCapability],
        request: AllocationRequest
    ) -> tuple[PlacementTarget, Optional[ResourceCapability]]:
        """Apply placement rules to determine target and primary resource."""
        
        # Get allowed targets based on privacy class
        privacy_rules = self._placement_rules["privacy_rules"]
        step_type_rules = self._placement_rules["step_type_rules"]
        
        # Determine privacy class from step or request
        privacy_class = self._determine_privacy_class(step, request)
        allowed_targets = privacy_rules.get(privacy_class, [PlacementTarget.LOCAL_DEVICE])
        
        # Filter by step type rules
        step_type_targets = step_type_rules.get(step.step_type, [PlacementTarget.LOCAL_DEVICE])
        allowed_targets = [t for t in allowed_targets if t in step_type_targets]
        
        # Score each target based on strategy
        target_scores = {}
        for target in allowed_targets:
            score = self._calculate_target_score(target, strategy, step, request)
            target_scores[target] = score
        
        # Select best target
        if target_scores:
            best_target = max(target_scores, key=target_scores.get)
        else:
            best_target = PlacementTarget.LOCAL_DEVICE
        
        # Select primary resource for the target
        primary_resource = self._select_primary_resource(best_target, local_resources, edge_resources, cloud_resources)
        
        return best_target, primary_resource
    
    def _determine_privacy_class(self, step: ExecutionStep, request: AllocationRequest) -> PrivacyClass:
        """Determine privacy class for the step."""
        # Check if privacy class is specified in step metadata
        if hasattr(step, 'metadata') and step.metadata.get('privacy_class'):
            return step.metadata['privacy_class']
        
        # Check if privacy class is specified in request
        if request.privacy_requirements.get('privacy_class'):
            return request.privacy_requirements['privacy_class']
        
        # Default based on step type
        if step.step_type in [StepType.DEVICE_CONTROL, StepType.DATA_COLLECTION]:
            return PrivacyClass.CONFIDENTIAL
        elif step.step_type in [StepType.ML_INFERENCE, StepType.DATA_ANALYSIS]:
            return PrivacyClass.INTERNAL
        else:
            return PrivacyClass.PUBLIC
    
    def _calculate_target_score(
        self, 
        target: PlacementTarget, 
        strategy: PlacementStrategy,
        step: ExecutionStep,
        request: AllocationRequest
    ) -> float:
        """Calculate score for a placement target."""
        score = 0.0
        
        # Privacy score (higher for local targets)
        privacy_scores = {
            PlacementTarget.LOCAL_DEVICE: 1.0,
            PlacementTarget.EDGE_GATEWAY: 0.8,
            PlacementTarget.EDGE_CLUSTER: 0.6,
            PlacementTarget.CLOUD_REGION: 0.2
        }
        score += privacy_scores.get(target, 0.5) * strategy.privacy_weight
        
        # Cost score (lower is better)
        cost_scores = {
            PlacementTarget.LOCAL_DEVICE: 1.0,
            PlacementTarget.EDGE_GATEWAY: 0.8,
            PlacementTarget.EDGE_CLUSTER: 0.6,
            PlacementTarget.CLOUD_REGION: 0.2
        }
        score += cost_scores.get(target, 0.5) * strategy.cost_weight
        
        # Latency score (lower is better)
        latency_scores = {
            PlacementTarget.LOCAL_DEVICE: 1.0,
            PlacementTarget.EDGE_GATEWAY: 0.8,
            PlacementTarget.EDGE_CLUSTER: 0.6,
            PlacementTarget.CLOUD_REGION: 0.3
        }
        score += latency_scores.get(target, 0.5) * strategy.latency_weight
        
        # Energy efficiency score
        energy_scores = {
            PlacementTarget.LOCAL_DEVICE: 0.9,
            PlacementTarget.EDGE_GATEWAY: 1.0,
            PlacementTarget.EDGE_CLUSTER: 0.8,
            PlacementTarget.CLOUD_REGION: 0.6
        }
        score += energy_scores.get(target, 0.5) * strategy.energy_weight
        
        # Reliability score
        reliability_scores = {
            PlacementTarget.LOCAL_DEVICE: 0.7,
            PlacementTarget.EDGE_GATEWAY: 0.9,
            PlacementTarget.EDGE_CLUSTER: 0.8,
            PlacementTarget.CLOUD_REGION: 1.0
        }
        score += reliability_scores.get(target, 0.5) * strategy.reliability_weight
        
        return score
    
    def _select_primary_resource(
        self,
        target: PlacementTarget,
        local_resources: List[ResourceCapability],
        edge_resources: List[ResourceCapability],
        cloud_resources: List[ResourceCapability]
    ) -> Optional[ResourceCapability]:
        """Select primary resource for the target."""
        if target == PlacementTarget.LOCAL_DEVICE and local_resources:
            return local_resources[0]
        elif target == PlacementTarget.EDGE_GATEWAY and edge_resources:
            return edge_resources[0]
        elif target == PlacementTarget.EDGE_CLUSTER and edge_resources:
            return edge_resources[0]
        elif target == PlacementTarget.CLOUD_REGION and cloud_resources:
            return cloud_resources[0]
        else:
            # Fallback to any available resource
            all_resources = local_resources + edge_resources + cloud_resources
            return all_resources[0] if all_resources else None
    
    def _determine_target_from_resource(self, resource: ResourceCapability) -> PlacementTarget:
        """Determine placement target from resource type."""
        if resource.resource_type.value in ["device", "sensor", "actuator"]:
            return PlacementTarget.LOCAL_DEVICE
        elif resource.resource_type.value == "edge_compute":
            return PlacementTarget.EDGE_GATEWAY
        elif resource.resource_type.value == "cloud_compute":
            return PlacementTarget.CLOUD_REGION
        else:
            return PlacementTarget.LOCAL_DEVICE
    
    def _select_fallback_resources(
        self,
        step: ExecutionStep,
        target: PlacementTarget,
        all_resources: List[ResourceCapability],
        primary_resource: ResourceCapability
    ) -> List[ResourceCapability]:
        """Select fallback resources."""
        fallbacks = []
        max_fallbacks = self.config.max_fallback_resources
        
        # Filter out the primary resource
        available_resources = [r for r in all_resources if r.resource_id != primary_resource.resource_id]
        
        # Sort by suitability
        available_resources.sort(key=lambda r: self._calculate_resource_suitability(step, r), reverse=True)
        
        # Select fallbacks
        for resource in available_resources[:max_fallbacks]:
            fallbacks.append(resource)
        
        return fallbacks
    
    def _calculate_resource_suitability(self, step: ExecutionStep, resource: ResourceCapability) -> float:
        """Calculate resource suitability for the step."""
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
        protocol_match = 0.5  # Default score
        if hasattr(step, 'protocols') and step.protocols:
            matching_protocols = sum(1 for p in step.protocols if p in resource.protocols)
            protocol_match = matching_protocols / len(step.protocols)
        suitability += protocol_match * 0.1
        
        return suitability
    
    def _calculate_expected_cost(self, step: ExecutionStep, resource: ResourceCapability, target: PlacementTarget) -> float:
        """Calculate expected cost for the step."""
        cost_model = self._cost_models.get(target, self._cost_models[PlacementTarget.LOCAL_DEVICE])
        
        # Base cost
        total_cost = cost_model["base_cost"]
        
        # Add resource-specific cost
        total_cost += resource.cost_per_hour * 0.1  # Assume 6 minutes execution time
        
        # Add step-specific costs
        if step.step_type == StepType.ML_INFERENCE:
            total_cost += cost_model["compute_cost"]
        elif step.step_type == StepType.DATA_ANALYSIS:
            total_cost += cost_model["compute_cost"] + cost_model["storage_cost"]
        elif step.step_type == StepType.STORAGE_OPERATION:
            total_cost += cost_model["storage_cost"]
        
        return total_cost
    
    def _calculate_expected_latency(self, step: ExecutionStep, resource: ResourceCapability, target: PlacementTarget) -> int:
        """Calculate expected latency for the step."""
        latency_model = self._latency_models.get(target, self._latency_models[PlacementTarget.LOCAL_DEVICE])
        
        # Base latency
        total_latency = latency_model["total_latency"]
        
        # Add resource-specific latency
        total_latency += resource.latency_ms
        
        # Add step-specific latency
        if step.step_type == StepType.ML_INFERENCE:
            total_latency += 1000  # ML inference overhead
        elif step.step_type == StepType.DATA_ANALYSIS:
            total_latency += 500   # Data analysis overhead
        
        return total_latency
    
    def _calculate_privacy_score(self, step: ExecutionStep, target: PlacementTarget, request: AllocationRequest) -> float:
        """Calculate privacy score for the placement."""
        privacy_scores = {
            PlacementTarget.LOCAL_DEVICE: 1.0,
            PlacementTarget.EDGE_GATEWAY: 0.8,
            PlacementTarget.EDGE_CLUSTER: 0.6,
            PlacementTarget.CLOUD_REGION: 0.2
        }
        
        base_score = privacy_scores.get(target, 0.5)
        
        # Adjust based on privacy requirements
        if request.privacy_requirements.get("enhanced_privacy", False):
            base_score *= 1.2
        
        return min(base_score, 1.0)
    
    def _calculate_energy_efficiency(self, step: ExecutionStep, resource: ResourceCapability, target: PlacementTarget) -> float:
        """Calculate energy efficiency for the placement."""
        # Base efficiency by target
        target_efficiency = {
            PlacementTarget.LOCAL_DEVICE: 0.9,
            PlacementTarget.EDGE_GATEWAY: 1.0,
            PlacementTarget.EDGE_CLUSTER: 0.8,
            PlacementTarget.CLOUD_REGION: 0.6
        }
        
        base_efficiency = target_efficiency.get(target, 0.5)
        
        # Adjust based on resource efficiency
        resource_efficiency = 1.0 - resource.current_load  # Less loaded = more efficient
        
        return (base_efficiency + resource_efficiency) / 2
    
    def _calculate_reliability_score(self, step: ExecutionStep, resource: ResourceCapability, target: PlacementTarget) -> float:
        """Calculate reliability score for the placement."""
        # Base reliability by target
        target_reliability = {
            PlacementTarget.LOCAL_DEVICE: 0.7,
            PlacementTarget.EDGE_GATEWAY: 0.9,
            PlacementTarget.EDGE_CLUSTER: 0.8,
            PlacementTarget.CLOUD_REGION: 1.0
        }
        
        base_reliability = target_reliability.get(target, 0.5)
        
        # Adjust based on resource health
        health = resource.metadata.get("health")
        if health and hasattr(health, "error_count"):
            error_penalty = min(health.error_count * 0.1, 0.3)
            base_reliability -= error_penalty
        
        return max(base_reliability, 0.0)
    
    def _generate_placement_rationale(
        self,
        step: ExecutionStep,
        target: PlacementTarget,
        primary_resource: ResourceCapability,
        strategy: PlacementStrategy,
        expected_cost: float,
        expected_latency: int,
        privacy_score: float,
        energy_efficiency: float,
        reliability_score: float
    ) -> str:
        """Generate placement rationale."""
        rationale_parts = []
        
        rationale_parts.append(f"Selected {target.value} placement using {strategy.name} strategy")
        rationale_parts.append(f"Primary resource: {primary_resource.resource_id}")
        rationale_parts.append(f"Expected cost: ${expected_cost:.4f}, latency: {expected_latency}ms")
        rationale_parts.append(f"Privacy score: {privacy_score:.2f}, energy efficiency: {energy_efficiency:.2f}, reliability: {reliability_score:.2f}")
        
        if target == PlacementTarget.LOCAL_DEVICE:
            rationale_parts.append("Local placement chosen for privacy and low latency")
        elif target == PlacementTarget.EDGE_GATEWAY:
            rationale_parts.append("Edge placement chosen for balanced performance and privacy")
        elif target == PlacementTarget.CLOUD_REGION:
            rationale_parts.append("Cloud placement chosen for scalability and reliability")
        
        return "; ".join(rationale_parts)
