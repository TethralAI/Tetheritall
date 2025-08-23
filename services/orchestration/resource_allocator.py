"""
Resource Allocation Agent

Mission: Bind plan steps to the best concrete resources and decide where to run them.

This component handles:
- Feasibility scanning of resources
- Placement decisions (edge/cloud/hybrid)
- Resource binding and reservation
- Execution preparation
- Dispatch coordination
- Adaptive rebinding on failures
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from .models import (
    AllocationStatus, ResourceType, PlacementTarget, FeasibilityStatus,
    ResourceCapability, FeasibilityResult, PlacementDecision, ResourceReservation,
    BoundStep, ResourceAllocation, AllocationRequest, AllocationResponse,
    RebindingRequest, AllocationMetrics, ExecutionStep, ExecutionPlan,
    PrivacyClass, TrustTier
)

logger = logging.getLogger(__name__)


@dataclass
class ResourceAllocatorConfig:
    """Configuration for the resource allocator."""
    max_feasibility_check_time_ms: int = 2000
    max_placement_decision_time_ms: int = 3000
    max_binding_time_ms: int = 5000
    enable_adaptive_rebinding: bool = True
    rebinding_timeout_ms: int = 10000
    local_execution_preference: float = 0.8
    privacy_first_placement: bool = True
    cost_optimization_weight: float = 0.3
    latency_optimization_weight: float = 0.3
    energy_optimization_weight: float = 0.2
    reliability_optimization_weight: float = 0.2
    max_fallback_resources: int = 3
    reservation_timeout_minutes: int = 30


class ResourceAllocator:
    """
    Main resource allocation agent that binds plan steps to concrete resources.
    
    Mission: Bind plan steps to the best concrete resources and decide where to run them.
    """
    
    def __init__(self, config: Optional[ResourceAllocatorConfig] = None):
        self.config = config or ResourceAllocatorConfig()
        self._running = False
        self._allocations: Dict[str, ResourceAllocation] = {}
        self._metrics: Dict[str, AllocationMetrics] = {}
        self._active_rebindings: Dict[str, asyncio.Task] = {}
        
        # Initialize sub-components
        self.feasibility_scanner = FeasibilityScanner()
        self.placement_decider = PlacementDecider(self.config)
        self.resource_binder = ResourceBinder()
        self.execution_prepper = ExecutionPrepper()
        self.dispatcher = Dispatcher()
        self.adaptive_rebinder = AdaptiveRebinder(self.config)
        
    async def start(self):
        """Start the resource allocator."""
        self._running = True
        await self.feasibility_scanner.start()
        await self.placement_decider.start()
        await self.resource_binder.start()
        await self.execution_prepper.start()
        await self.dispatcher.start()
        await self.adaptive_rebinder.start()
        logger.info("Resource allocator started")
        
    async def stop(self):
        """Stop the resource allocator."""
        self._running = False
        await self.feasibility_scanner.stop()
        await self.placement_decider.stop()
        await self.resource_binder.stop()
        await self.execution_prepper.stop()
        await self.dispatcher.stop()
        await self.adaptive_rebinder.stop()
        logger.info("Resource allocator stopped")
        
    async def allocate_resources(self, request: AllocationRequest) -> AllocationResponse:
        """
        Allocate resources for an execution plan.
        
        This implements the main workflow:
        1. Feasibility Scan
        2. Placement Decision
        3. Binding and Reservation
        4. Execution Prep
        5. Dispatch
        """
        start_time = time.time()
        allocation_id = str(uuid.uuid4())
        
        try:
            logger.info(f"Starting resource allocation for plan {request.plan_id}")
            
            # 1. Feasibility Scan
            feasibility_results = await self._scan_feasibility(request.execution_plan)
            if not self._check_feasibility_overall(feasibility_results):
                return AllocationResponse(
                    allocation_id=allocation_id,
                    status=AllocationStatus.FAILED,
                    bound_steps=[],
                    placement_rationale="Infeasible plan - insufficient resources",
                    expected_cost=0.0,
                    expected_latency_ms=0,
                    privacy_score=0.0,
                    errors=["Plan is infeasible with current resources"]
                )
            
            # 2. Placement Decision
            placement_decisions = await self._make_placement_decisions(
                request.execution_plan, feasibility_results, request
            )
            
            # 3. Binding and Reservation
            bound_steps, reservations = await self._bind_and_reserve(
                request.execution_plan, placement_decisions, request
            )
            
            # 4. Execution Prep
            prepared_steps = await self._prepare_execution(bound_steps, request)
            
            # 5. Create allocation record
            allocation = ResourceAllocation(
                allocation_id=allocation_id,
                plan_id=request.plan_id,
                status=AllocationStatus.RESERVED,
                bound_steps=prepared_steps,
                reservations=reservations,
                placement_rationale=self._generate_placement_rationale(placement_decisions),
                expected_total_cost=self._calculate_total_cost(prepared_steps),
                expected_total_latency_ms=self._calculate_total_latency(prepared_steps),
                privacy_score=self._calculate_privacy_score(prepared_steps),
                energy_efficiency=self._calculate_energy_efficiency(prepared_steps),
                reliability_score=self._calculate_reliability_score(prepared_steps)
            )
            
            self._allocations[allocation_id] = allocation
            
            # 6. Dispatch (async)
            asyncio.create_task(self._dispatch_allocation(allocation))
            
            # 7. Calculate metrics
            binding_time_ms = int((time.time() - start_time) * 1000)
            metrics = AllocationMetrics(
                allocation_id=allocation_id,
                placement_accuracy=self._calculate_placement_accuracy(placement_decisions),
                rebinding_rate=0.0,  # Will be updated during execution
                local_execution_ratio=self._calculate_local_execution_ratio(prepared_steps),
                device_utilization=self._calculate_device_utilization(reservations),
                average_binding_time_ms=binding_time_ms,
                cost_variance=0.0,  # Will be updated during execution
                latency_variance=0.0,  # Will be updated during execution
                privacy_compliance_score=allocation.privacy_score,
                energy_efficiency_score=allocation.energy_efficiency
            )
            self._metrics[allocation_id] = metrics
            
            return AllocationResponse(
                allocation_id=allocation_id,
                status=AllocationStatus.RESERVED,
                bound_steps=prepared_steps,
                placement_rationale=allocation.placement_rationale,
                expected_cost=allocation.expected_total_cost,
                expected_latency_ms=allocation.expected_total_latency_ms,
                privacy_score=allocation.privacy_score,
                warnings=self._collect_warnings(feasibility_results, placement_decisions)
            )
            
        except Exception as e:
            logger.error(f"Error in resource allocation {allocation_id}: {e}")
            return AllocationResponse(
                allocation_id=allocation_id,
                status=AllocationStatus.FAILED,
                bound_steps=[],
                placement_rationale="Allocation failed",
                expected_cost=0.0,
                expected_latency_ms=0,
                privacy_score=0.0,
                errors=[f"Allocation error: {str(e)}"]
            )
    
    async def rebind_resources(self, request: RebindingRequest) -> AllocationResponse:
        """Rebind resources for a specific step due to failure or drift."""
        if not self._running:
            raise RuntimeError("Resource allocator is not running")
            
        allocation = self._allocations.get(request.allocation_id)
        if not allocation:
            raise ValueError(f"Allocation {request.allocation_id} not found")
            
        return await self.adaptive_rebinder.rebind_step(request, allocation)
    
    async def get_allocation_status(self, allocation_id: str) -> Optional[AllocationStatus]:
        """Get the current status of an allocation."""
        allocation = self._allocations.get(allocation_id)
        return allocation.status if allocation else None
    
    async def get_allocation_metrics(self, allocation_id: str) -> Optional[AllocationMetrics]:
        """Get metrics for an allocation."""
        return self._metrics.get(allocation_id)
    
    async def cancel_allocation(self, allocation_id: str) -> bool:
        """Cancel an allocation and release resources."""
        allocation = self._allocations.get(allocation_id)
        if not allocation:
            return False
            
        try:
            # Release reservations
            await self.resource_binder.release_reservations(allocation.reservations)
            
            # Cancel any active rebinding
            if allocation_id in self._active_rebindings:
                self._active_rebindings[allocation_id].cancel()
                del self._active_rebindings[allocation_id]
            
            # Update status
            allocation.status = AllocationStatus.CANCELLED
            allocation.updated_at = datetime.utcnow()
            
            logger.info(f"Allocation {allocation_id} cancelled")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling allocation {allocation_id}: {e}")
            return False
    
    # Private methods for the main workflow
    
    async def _scan_feasibility(self, plan: ExecutionPlan) -> List[FeasibilityResult]:
        """Scan feasibility for all steps in the plan."""
        tasks = []
        for step in plan.steps:
            task = self.feasibility_scanner.check_feasibility(step)
            tasks.append(task)
        
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    def _check_feasibility_overall(self, results: List[FeasibilityResult]) -> bool:
        """Check if the overall plan is feasible."""
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Feasibility check failed: {result}")
                return False
            if result.status == FeasibilityStatus.INFEASIBLE:
                return False
        return True
    
    async def _make_placement_decisions(
        self, 
        plan: ExecutionPlan, 
        feasibility_results: List[FeasibilityResult],
        request: AllocationRequest
    ) -> List[PlacementDecision]:
        """Make placement decisions for all steps."""
        decisions = []
        for step, feasibility in zip(plan.steps, feasibility_results):
            if isinstance(feasibility, Exception):
                continue
            decision = await self.placement_decider.decide_placement(
                step, feasibility, request
            )
            decisions.append(decision)
        return decisions
    
    async def _bind_and_reserve(
        self,
        plan: ExecutionPlan,
        placement_decisions: List[PlacementDecision],
        request: AllocationRequest
    ) -> tuple[List[BoundStep], List[ResourceReservation]]:
        """Bind steps to resources and create reservations."""
        bound_steps = []
        all_reservations = []
        
        for step, placement in zip(plan.steps, placement_decisions):
            bound_step, reservations = await self.resource_binder.bind_step(
                step, placement, request
            )
            bound_steps.append(bound_step)
            all_reservations.extend(reservations)
        
        return bound_steps, all_reservations
    
    async def _prepare_execution(
        self, 
        bound_steps: List[BoundStep], 
        request: AllocationRequest
    ) -> List[BoundStep]:
        """Prepare steps for execution."""
        prepared_steps = []
        for step in bound_steps:
            prepared_step = await self.execution_prepper.prepare_step(step, request)
            prepared_steps.append(prepared_step)
        return prepared_steps
    
    async def _dispatch_allocation(self, allocation: ResourceAllocation):
        """Dispatch the allocation to the executor."""
        try:
            await self.dispatcher.dispatch_allocation(allocation)
            allocation.status = AllocationStatus.DISPATCHED
            allocation.updated_at = datetime.utcnow()
            logger.info(f"Allocation {allocation.allocation_id} dispatched")
        except Exception as e:
            logger.error(f"Error dispatching allocation {allocation.allocation_id}: {e}")
            allocation.status = AllocationStatus.FAILED
            allocation.updated_at = datetime.utcnow()
    
    def _generate_placement_rationale(self, decisions: List[PlacementDecision]) -> str:
        """Generate overall placement rationale."""
        rationales = [d.rationale for d in decisions if d.rationale]
        return "; ".join(rationales) if rationales else "Standard placement strategy applied"
    
    def _calculate_total_cost(self, steps: List[BoundStep]) -> float:
        """Calculate total expected cost."""
        return sum(step.placement.expected_cost for step in steps)
    
    def _calculate_total_latency(self, steps: List[BoundStep]) -> int:
        """Calculate total expected latency."""
        return sum(step.placement.expected_latency_ms for step in steps)
    
    def _calculate_privacy_score(self, steps: List[BoundStep]) -> float:
        """Calculate overall privacy score."""
        if not steps:
            return 0.0
        scores = [step.placement.privacy_score for step in steps]
        return sum(scores) / len(scores)
    
    def _calculate_energy_efficiency(self, steps: List[BoundStep]) -> float:
        """Calculate overall energy efficiency."""
        if not steps:
            return 0.0
        scores = [step.placement.energy_efficiency for step in steps]
        return sum(scores) / len(scores)
    
    def _calculate_reliability_score(self, steps: List[BoundStep]) -> float:
        """Calculate overall reliability score."""
        if not steps:
            return 0.0
        scores = [step.placement.reliability_score for step in steps]
        return sum(scores) / len(scores)
    
    def _calculate_placement_accuracy(self, decisions: List[PlacementDecision]) -> float:
        """Calculate placement accuracy score."""
        if not decisions:
            return 0.0
        # This would be based on historical accuracy data
        return 0.85  # Placeholder
    
    def _calculate_local_execution_ratio(self, steps: List[BoundStep]) -> float:
        """Calculate ratio of steps executed locally."""
        if not steps:
            return 0.0
        local_steps = sum(1 for step in steps if step.placement.target == PlacementTarget.LOCAL_DEVICE)
        return local_steps / len(steps)
    
    def _calculate_device_utilization(self, reservations: List[ResourceReservation]) -> float:
        """Calculate device utilization."""
        if not reservations:
            return 0.0
        # This would be based on actual device capacity vs usage
        return 0.65  # Placeholder
    
    def _collect_warnings(
        self, 
        feasibility_results: List[FeasibilityResult],
        placement_decisions: List[PlacementDecision]
    ) -> List[str]:
        """Collect warnings from feasibility and placement."""
        warnings = []
        for result in feasibility_results:
            if isinstance(result, FeasibilityResult):
                warnings.extend(result.warnings)
        return warnings


# Sub-components will be implemented in separate files
class FeasibilityScanner:
    """Checks device readiness, protocol support, energy and time estimates."""
    
    async def start(self):
        """Start the feasibility scanner."""
        pass
    
    async def stop(self):
        """Stop the feasibility scanner."""
        pass
    
    async def check_feasibility(self, step: ExecutionStep) -> FeasibilityResult:
        """Check feasibility for a single step."""
        # Implementation will be in feasibility_scanner.py
        pass


class PlacementDecider:
    """Chooses edge, cloud, or hybrid per step based on constraints and privacy class."""
    
    def __init__(self, config: ResourceAllocatorConfig):
        self.config = config
    
    async def start(self):
        """Start the placement decider."""
        pass
    
    async def stop(self):
        """Stop the placement decider."""
        pass
    
    async def decide_placement(
        self, 
        step: ExecutionStep, 
        feasibility: FeasibilityResult,
        request: AllocationRequest
    ) -> PlacementDecision:
        """Decide placement for a single step."""
        # Implementation will be in placement_decider.py
        pass


class ResourceBinder:
    """Locks device or compute slots, avoids conflicts, sets deadlines."""
    
    async def start(self):
        """Start the resource binder."""
        pass
    
    async def stop(self):
        """Stop the resource binder."""
        pass
    
    async def bind_step(
        self, 
        step: ExecutionStep, 
        placement: PlacementDecision,
        request: AllocationRequest
    ) -> tuple[BoundStep, List[ResourceReservation]]:
        """Bind a step to resources."""
        # Implementation will be in resource_binder.py
        pass
    
    async def release_reservations(self, reservations: List[ResourceReservation]):
        """Release resource reservations."""
        # Implementation will be in resource_binder.py
        pass


class ExecutionPrepper:
    """Generates step-level run configs with consent scope and data minimization rules."""
    
    async def start(self):
        """Start the execution prepper."""
        pass
    
    async def stop(self):
        """Stop the execution prepper."""
        pass
    
    async def prepare_step(
        self, 
        bound_step: BoundStep, 
        request: AllocationRequest
    ) -> BoundStep:
        """Prepare a step for execution."""
        # Implementation will be in execution_prepper.py
        pass


class Dispatcher:
    """Hands bound steps to Scheduler and Executor."""
    
    async def start(self):
        """Start the dispatcher."""
        pass
    
    async def stop(self):
        """Stop the dispatcher."""
        pass
    
    async def dispatch_allocation(self, allocation: ResourceAllocation):
        """Dispatch an allocation to the executor."""
        # Implementation will be in dispatcher.py
        pass


class AdaptiveRebinder:
    """Reallocates on failure, jitter, or state drift within policy limits."""
    
    def __init__(self, config: ResourceAllocatorConfig):
        self.config = config
    
    async def start(self):
        """Start the adaptive rebinder."""
        pass
    
    async def stop(self):
        """Stop the adaptive rebinder."""
        pass
    
    async def rebind_step(
        self, 
        request: RebindingRequest, 
        allocation: ResourceAllocation
    ) -> AllocationResponse:
        """Rebind a step to new resources."""
        # Implementation will be in adaptive_rebinder.py
        pass
