"""
Execution Planner
Produces execution plans with steps, ordering, fallbacks, and guardrails.
"""

from __future__ import annotations

import logging
import uuid
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .models import (
    TaskSpec, ExecutionPlan, ExecutionStep, ContextSnapshot, ConsentReference,
    Constraint, Goal, PrivacyClass, TrustTier, ExecutionStatus, StepType
)
from .agent import OrchestrationConfig

logger = logging.getLogger(__name__)


@dataclass
class PlanResult:
    """Result of plan creation."""
    success: bool
    plan: Optional[ExecutionPlan] = None
    alternatives: List[ExecutionPlan] = None
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.alternatives is None:
            self.alternatives = []
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class ExecutionPlanner:
    """Creates execution plans with optimization for privacy, local-first, cost, latency, and user comfort."""
    
    def __init__(self):
        # Planning strategies
        self._strategies = {
            "privacy_first": self._plan_privacy_first,
            "cost_optimized": self._plan_cost_optimized,
            "latency_optimized": self._plan_latency_optimized,
            "comfort_optimized": self._plan_comfort_optimized,
            "balanced": self._plan_balanced
        }
        
        # Step templates for common operations
        self._step_templates = {
            "thermostat_control": {
                "type": StepType.DEVICE_CONTROL,
                "parameters": {"device_type": "thermostat", "action": "set_temperature"},
                "estimated_duration_ms": 2000,
                "estimated_cost": 0.01
            },
            "lighting_control": {
                "type": StepType.DEVICE_CONTROL,
                "parameters": {"device_type": "lighting", "action": "set_brightness"},
                "estimated_duration_ms": 1000,
                "estimated_cost": 0.005
            },
            "data_collection": {
                "type": StepType.DATA_COLLECTION,
                "parameters": {"data_type": "sensor_data", "duration": 300},
                "estimated_duration_ms": 5000,
                "estimated_cost": 0.02
            },
            "ml_inference": {
                "type": StepType.ML_INFERENCE,
                "parameters": {"model_type": "prediction", "input_data": "sensor_data"},
                "estimated_duration_ms": 3000,
                "estimated_cost": 0.05
            },
            "notification": {
                "type": StepType.NOTIFICATION,
                "parameters": {"channel": "push", "priority": "normal"},
                "estimated_duration_ms": 500,
                "estimated_cost": 0.001
            }
        }
    
    async def create_plan(
        self,
        task_spec: TaskSpec,
        context: ContextSnapshot,
        consent_refs: List[ConsentReference],
        config: OrchestrationConfig
    ) -> PlanResult:
        """
        Create an execution plan for the task.
        
        Args:
            task_spec: Task specification
            context: Current system context
            consent_refs: Consent references
            config: Orchestration configuration
            
        Returns:
            PlanResult with the created plan and alternatives
        """
        logger.debug(f"Creating execution plan for task {task_spec.task_id}")
        
        try:
            # Determine planning strategy
            strategy = self._determine_planning_strategy(task_spec, context)
            
            # Create primary plan
            plan = await self._create_primary_plan(task_spec, context, consent_refs, strategy, config)
            
            if not plan:
                return PlanResult(
                    success=False,
                    errors=["Failed to create primary plan"]
                )
            
            # Create alternative plans
            alternatives = await self._create_alternative_plans(
                task_spec, context, consent_refs, config
            )
            
            # Validate plan
            validation_result = self._validate_plan(plan, task_spec, context)
            if not validation_result["valid"]:
                return PlanResult(
                    success=False,
                    errors=validation_result["errors"],
                    warnings=validation_result["warnings"]
                )
            
            return PlanResult(
                success=True,
                plan=plan,
                alternatives=alternatives,
                warnings=validation_result["warnings"]
            )
            
        except Exception as e:
            logger.error(f"Error creating execution plan: {e}")
            return PlanResult(
                success=False,
                errors=[f"Planning error: {str(e)}"]
            )
    
    def _determine_planning_strategy(self, task_spec: TaskSpec, context: ContextSnapshot) -> str:
        """Determine the best planning strategy based on task and context."""
        # Analyze goals to determine strategy
        goal_targets = [goal.target for goal in task_spec.goals]
        goal_weights = {goal.target: goal.weight for goal in task_spec.goals}
        
        # Check for privacy-focused goals
        if "privacy" in goal_targets and goal_weights.get("privacy", 0) > 0.8:
            return "privacy_first"
        
        # Check for cost-focused goals
        if "cost" in goal_targets and goal_weights.get("cost", 0) > 0.8:
            return "cost_optimized"
        
        # Check for latency-focused goals
        if "latency" in goal_targets and goal_weights.get("latency", 0) > 0.8:
            return "latency_optimized"
        
        # Check for comfort-focused goals
        if "comfort" in goal_targets and goal_weights.get("comfort", 0) > 0.8:
            return "comfort_optimized"
        
        # Default to balanced strategy
        return "balanced"
    
    async def _create_primary_plan(
        self,
        task_spec: TaskSpec,
        context: ContextSnapshot,
        consent_refs: List[ConsentReference],
        strategy: str,
        config: OrchestrationConfig
    ) -> Optional[ExecutionPlan]:
        """Create the primary execution plan."""
        strategy_func = self._strategies.get(strategy, self._plan_balanced)
        
        # Generate steps using the selected strategy
        steps = await strategy_func(task_spec, context, config)
        
        if not steps:
            return None
        
        # Create the execution plan
        plan = ExecutionPlan(
            plan_id=str(uuid.uuid4()),
            task_spec=task_spec,
            steps=steps,
            constraints=task_spec.constraints,
            goals=task_spec.goals,
            context_snapshot=context,
            consent_references=consent_refs,
            status=ExecutionStatus.DRAFT
        )
        
        return plan
    
    async def _create_alternative_plans(
        self,
        task_spec: TaskSpec,
        context: ContextSnapshot,
        consent_refs: List[ConsentReference],
        config: OrchestrationConfig
    ) -> List[ExecutionPlan]:
        """Create alternative execution plans."""
        alternatives = []
        
        # Create alternatives using different strategies
        for strategy in self._strategies.keys():
            if strategy == "balanced":  # Skip balanced as it's the primary
                continue
            
            try:
                steps = await self._strategies[strategy](task_spec, context, config)
                if steps:
                    plan = ExecutionPlan(
                        plan_id=str(uuid.uuid4()),
                        task_spec=task_spec,
                        steps=steps,
                        constraints=task_spec.constraints,
                        goals=task_spec.goals,
                        context_snapshot=context,
                        consent_references=consent_refs,
                        status=ExecutionStatus.DRAFT
                    )
                    alternatives.append(plan)
            except Exception as e:
                logger.warning(f"Failed to create alternative plan with strategy {strategy}: {e}")
        
        return alternatives[:config.max_plan_alternatives]
    
    async def _plan_privacy_first(
        self,
        task_spec: TaskSpec,
        context: ContextSnapshot,
        config: OrchestrationConfig
    ) -> List[ExecutionStep]:
        """Create a plan optimized for privacy (local-first execution)."""
        steps = []
        
        # Prioritize local processing
        for device_id, capability in context.device_graph.items():
            if capability.local_processing:
                step = self._create_device_step(device_id, capability, task_spec)
                if step:
                    steps.append(step)
        
        # Add local ML inference if needed
        if self._requires_ml_inference(task_spec):
            ml_step = self._create_ml_step(local_only=True)
            steps.append(ml_step)
        
        # Add local notification if needed
        if self._requires_notification(task_spec):
            notif_step = self._create_notification_step(local_only=True)
            steps.append(notif_step)
        
        return steps
    
    async def _plan_cost_optimized(
        self,
        task_spec: TaskSpec,
        context: ContextSnapshot,
        config: OrchestrationConfig
    ) -> List[ExecutionStep]:
        """Create a plan optimized for cost."""
        steps = []
        
        # Use lowest-cost devices and operations
        for device_id, capability in context.device_graph.items():
            if capability.estimated_cost < 0.02:  # Low-cost threshold
                step = self._create_device_step(device_id, capability, task_spec)
                if step:
                    steps.append(step)
        
        # Use local processing to avoid cloud costs
        if self._requires_ml_inference(task_spec):
            ml_step = self._create_ml_step(local_only=True, cost_optimized=True)
            steps.append(ml_step)
        
        return steps
    
    async def _plan_latency_optimized(
        self,
        task_spec: TaskSpec,
        context: ContextSnapshot,
        config: OrchestrationConfig
    ) -> List[ExecutionStep]:
        """Create a plan optimized for low latency."""
        steps = []
        
        # Use fastest devices and operations
        for device_id, capability in context.device_graph.items():
            if capability.estimated_duration_ms < 1000:  # Fast threshold
                step = self._create_device_step(device_id, capability, task_spec)
                if step:
                    steps.append(step)
        
        # Use local processing for speed
        if self._requires_ml_inference(task_spec):
            ml_step = self._create_ml_step(local_only=True, fast_inference=True)
            steps.append(ml_step)
        
        return steps
    
    async def _plan_comfort_optimized(
        self,
        task_spec: TaskSpec,
        context: ContextSnapshot,
        config: OrchestrationConfig
    ) -> List[ExecutionStep]:
        """Create a plan optimized for user comfort."""
        steps = []
        
        # Prioritize comfort-related devices
        comfort_devices = ["thermostat", "lighting", "air_purifier"]
        
        for device_id, capability in context.device_graph.items():
            if capability.capability_type in comfort_devices:
                step = self._create_device_step(device_id, capability, task_spec)
                if step:
                    steps.append(step)
        
        # Add comfort monitoring
        monitoring_step = self._create_monitoring_step(comfort_focused=True)
        steps.append(monitoring_step)
        
        return steps
    
    async def _plan_balanced(
        self,
        task_spec: TaskSpec,
        context: ContextSnapshot,
        config: OrchestrationConfig
    ) -> List[ExecutionStep]:
        """Create a balanced plan considering all factors."""
        steps = []
        
        # Include all relevant devices
        for device_id, capability in context.device_graph.items():
            step = self._create_device_step(device_id, capability, task_spec)
            if step:
                steps.append(step)
        
        # Add ML inference if needed
        if self._requires_ml_inference(task_spec):
            ml_step = self._create_ml_step()
            steps.append(ml_step)
        
        # Add notification if needed
        if self._requires_notification(task_spec):
            notif_step = self._create_notification_step()
            steps.append(notif_step)
        
        return steps
    
    def _create_device_step(
        self,
        device_id: str,
        capability: 'DeviceCapability',
        task_spec: TaskSpec
    ) -> Optional[ExecutionStep]:
        """Create a device control step."""
        # Determine step type based on device capability
        if capability.capability_type == "thermostat":
            template = self._step_templates["thermostat_control"]
        elif capability.capability_type == "lighting":
            template = self._step_templates["lighting_control"]
        else:
            template = self._step_templates["data_collection"]
        
        # Create step with device-specific parameters
        step = ExecutionStep(
            step_id=f"step_{device_id}_{uuid.uuid4().hex[:8]}",
            step_type=template["type"],
            device_id=device_id,
            parameters={
                **template["parameters"],
                "device_id": device_id,
                "capability_type": capability.capability_type
            },
            privacy_class=capability.privacy_class,
            local_execution=capability.local_processing,
            estimated_duration_ms=template["estimated_duration_ms"],
            estimated_cost=template["estimated_cost"]
        )
        
        # Add guardrails based on privacy and trust
        step.guardrails = self._create_guardrails(capability, task_spec)
        
        return step
    
    def _create_ml_step(self, local_only: bool = False, **kwargs) -> ExecutionStep:
        """Create an ML inference step."""
        template = self._step_templates["ml_inference"]
        
        parameters = template["parameters"].copy()
        if local_only:
            parameters["execution_mode"] = "local_only"
        if kwargs.get("cost_optimized"):
            parameters["model_complexity"] = "low"
        if kwargs.get("fast_inference"):
            parameters["inference_mode"] = "fast"
        
        return ExecutionStep(
            step_id=f"step_ml_{uuid.uuid4().hex[:8]}",
            step_type=template["type"],
            parameters=parameters,
            privacy_class=PrivacyClass.INTERNAL,
            local_execution=local_only,
            estimated_duration_ms=template["estimated_duration_ms"],
            estimated_cost=template["estimated_cost"]
        )
    
    def _create_notification_step(self, local_only: bool = False) -> ExecutionStep:
        """Create a notification step."""
        template = self._step_templates["notification"]
        
        parameters = template["parameters"].copy()
        if local_only:
            parameters["channel"] = "local"
        
        return ExecutionStep(
            step_id=f"step_notif_{uuid.uuid4().hex[:8]}",
            step_type=template["type"],
            parameters=parameters,
            privacy_class=PrivacyClass.PUBLIC,
            local_execution=local_only,
            estimated_duration_ms=template["estimated_duration_ms"],
            estimated_cost=template["estimated_cost"]
        )
    
    def _create_monitoring_step(self, comfort_focused: bool = False) -> ExecutionStep:
        """Create a monitoring step."""
        template = self._step_templates["data_collection"]
        
        parameters = template["parameters"].copy()
        if comfort_focused:
            parameters["data_type"] = "comfort_metrics"
            parameters["sensors"] = ["temperature", "humidity", "air_quality"]
        
        return ExecutionStep(
            step_id=f"step_monitor_{uuid.uuid4().hex[:8]}",
            step_type=template["type"],
            parameters=parameters,
            privacy_class=PrivacyClass.INTERNAL,
            local_execution=True,
            estimated_duration_ms=template["estimated_duration_ms"],
            estimated_cost=template["estimated_cost"]
        )
    
    def _create_guardrails(self, capability: 'DeviceCapability', task_spec: TaskSpec) -> List[Dict[str, Any]]:
        """Create guardrails for a step."""
        guardrails = []
        
        # Privacy guardrails
        if capability.privacy_class in [PrivacyClass.CONFIDENTIAL, PrivacyClass.RESTRICTED]:
            guardrails.append({
                "type": "privacy",
                "action": "local_only",
                "reason": "High privacy requirement"
            })
        
        # Trust guardrails
        if capability.trust_tier in [TrustTier.UNTRUSTED, TrustTier.BASIC]:
            guardrails.append({
                "type": "trust",
                "action": "sandboxed",
                "reason": "Low trust tier"
            })
        
        # Safety guardrails for critical devices
        if capability.capability_type in ["thermostat", "security"]:
            guardrails.append({
                "type": "safety",
                "action": "validate_before_execute",
                "reason": "Critical device operation"
            })
        
        return guardrails
    
    def _requires_ml_inference(self, task_spec: TaskSpec) -> bool:
        """Check if the task requires ML inference."""
        ml_keywords = ["prediction", "inference", "learning", "model", "ai", "ml"]
        for goal in task_spec.goals:
            if any(keyword in goal.target.lower() for keyword in ml_keywords):
                return True
        return False
    
    def _requires_notification(self, task_spec: TaskSpec) -> bool:
        """Check if the task requires notification."""
        notif_keywords = ["notify", "alert", "message", "report"]
        for goal in task_spec.goals:
            if any(keyword in goal.target.lower() for keyword in notif_keywords):
                return True
        return False
    
    def _validate_plan(self, plan: ExecutionPlan, task_spec: TaskSpec, context: ContextSnapshot) -> Dict[str, Any]:
        """Validate the execution plan."""
        errors = []
        warnings = []
        
        # Check if plan has steps
        if not plan.steps:
            errors.append("Plan has no execution steps")
        
        # Check privacy compliance
        privacy_score = self._calculate_privacy_score(plan)
        if privacy_score < 0.7:
            warnings.append(f"Low privacy score: {privacy_score:.2f}")
        
        # Check cost compliance
        total_cost = sum(step.estimated_cost for step in plan.steps)
        cost_constraint = next((c for c in task_spec.constraints if c.type == "cost"), None)
        if cost_constraint and total_cost > cost_constraint.value:
            errors.append(f"Plan cost {total_cost} exceeds constraint {cost_constraint.value}")
        
        # Check latency compliance
        total_duration = sum(step.estimated_duration_ms for step in plan.steps)
        latency_constraint = next((c for c in task_spec.constraints if c.type == "latency"), None)
        if latency_constraint and total_duration > latency_constraint.value:
            errors.append(f"Plan duration {total_duration}ms exceeds constraint {latency_constraint.value}ms")
        
        # Check device availability
        required_devices = self._get_required_devices(task_spec)
        available_devices = set(context.device_graph.keys())
        missing_devices = required_devices - available_devices
        if missing_devices:
            warnings.append(f"Missing devices: {missing_devices}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _calculate_privacy_score(self, plan: ExecutionPlan) -> float:
        """Calculate privacy score (percentage of local execution)."""
        if not plan.steps:
            return 0.0
        
        local_steps = sum(1 for step in plan.steps if step.local_execution)
        return local_steps / len(plan.steps)
    
    def _get_required_devices(self, task_spec: TaskSpec) -> set:
        """Get set of required device types."""
        required = set()
        
        # Extract from goals
        for goal in task_spec.goals:
            if "thermostat" in goal.target.lower():
                required.add("thermostat")
            elif "light" in goal.target.lower():
                required.add("lighting")
            elif "security" in goal.target.lower():
                required.add("security")
        
        # Extract from constraints
        for constraint in task_spec.constraints:
            if constraint.type == "device_availability" and isinstance(constraint.value, list):
                required.update(constraint.value)
        
        return required
