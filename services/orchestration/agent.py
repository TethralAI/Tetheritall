"""
Orchestration Agent
Main agent for translating intents into safe, efficient, explainable execution plans.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import time
import uuid
from dataclasses import dataclass

from .models import (
    TaskSpec, ExecutionPlan, ExecutionStep, ContextSnapshot, ConsentReference,
    Constraint, Goal, PrivacyClass, TrustTier, ExecutionStatus, StepType,
    TriggerType, PlanMetrics, OrchestrationRequest, OrchestrationResponse
)
from .intent_translator import IntentTranslator
from .policy_gate import PolicyGate
from .context_puller import ContextPuller
from .planner import ExecutionPlanner
from .explainer import PlanExplainer
from shared.config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class OrchestrationConfig:
    """Configuration for the orchestration agent."""
    max_planning_time_ms: int = 5000
    max_plan_alternatives: int = 3
    enable_preview_mode: bool = True
    enable_replanning: bool = True
    privacy_first: bool = True
    local_execution_preference: float = 0.8
    cost_budget_default: float = 1.0
    latency_budget_default_ms: int = 5000


class OrchestrationAgent:
    """
    Main orchestration agent that translates intents into execution plans.
    
    Mission: Translate an intent into a safe, efficient, explainable Execution Plan.
    """
    
    def __init__(self, config: Optional[OrchestrationConfig] = None):
        self.config = config or OrchestrationConfig()
        self._running = False
        
        # Core components
        self.intent_translator = IntentTranslator()
        self.policy_gate = PolicyGate()
        self.context_puller = ContextPuller()
        self.planner = ExecutionPlanner()
        self.explainer = PlanExplainer()
        
        # State management
        self._plans: Dict[str, ExecutionPlan] = {}
        self._metrics: Dict[str, PlanMetrics] = {}
        self._active_plans: Dict[str, asyncio.Task] = {}
        
        # Monitoring and observability
        self._plan_history: List[Dict[str, Any]] = []
        self._replan_events: List[Dict[str, Any]] = []
        
    async def start(self):
        """Start the orchestration agent."""
        self._running = True
        logger.info("Orchestration agent started")
        
        # Start background tasks
        asyncio.create_task(self._monitor_plan_execution())
        asyncio.create_task(self._cleanup_completed_plans())
        
    async def stop(self):
        """Stop the orchestration agent."""
        self._running = False
        
        # Cancel active plan executions
        for task in self._active_plans.values():
            task.cancel()
            
        logger.info("Orchestration agent stopped")
        
    async def create_execution_plan(
        self, 
        request: OrchestrationRequest
    ) -> OrchestrationResponse:
        """
        Main entry point for creating execution plans.
        
        This method implements the complete orchestration workflow:
        1. Intake and Normalization
        2. Policy and Consent Gate
        3. Context Pull
        4. Planning
        5. Explainability
        6. Handover
        """
        start_time = time.time()
        plan_id = str(uuid.uuid4())
        
        try:
            logger.info(f"Creating execution plan {plan_id} for intent: {request.intent}")
            
            # 1. Intake and Normalization
            task_spec = await self._normalize_request(request)
            
            # 2. Policy and Consent Gate
            consent_check = await self._check_policy_and_consent(task_spec)
            if not consent_check.approved:
                return OrchestrationResponse(
                    plan_id=plan_id,
                    status=ExecutionStatus.FAILED,
                    errors=[f"Policy check failed: {consent_check.reason}"],
                    approval_required=consent_check.requires_approval
                )
            
            # 3. Context Pull
            context = await self._pull_context(task_spec)
            
            # 4. Planning
            plan_result = await self._create_plan(task_spec, context, consent_check.consent_refs)
            
            if not plan_result.success:
                return OrchestrationResponse(
                    plan_id=plan_id,
                    status=ExecutionStatus.FAILED,
                    errors=plan_result.errors,
                    warnings=plan_result.warnings
                )
            
            # 5. Explainability
            rationale = await self._explain_plan(plan_result.plan, task_spec)
            plan_result.plan.rationale = rationale
            
            # 6. Handover preparation
            await self._prepare_handover(plan_result.plan)
            
            # Store plan and metrics
            self._plans[plan_id] = plan_result.plan
            self._metrics[plan_id] = PlanMetrics(
                plan_id=plan_id,
                time_to_plan_ms=int((time.time() - start_time) * 1000)
            )
            
            # Start execution if not preview mode
            if not request.preview_mode and plan_result.plan.status == ExecutionStatus.APPROVED:
                execution_task = asyncio.create_task(
                    self._execute_plan(plan_id, plan_result.plan)
                )
                self._active_plans[plan_id] = execution_task
            
            return OrchestrationResponse(
                plan_id=plan_id,
                status=plan_result.plan.status,
                plan=plan_result.plan,
                rationale=rationale,
                approval_required=plan_result.plan.approval_required,
                alternatives=plan_result.alternatives,
                warnings=plan_result.warnings
            )
            
        except Exception as e:
            logger.error(f"Error creating execution plan {plan_id}: {e}")
            return OrchestrationResponse(
                plan_id=plan_id,
                status=ExecutionStatus.FAILED,
                errors=[f"Internal error: {str(e)}"]
            )
    
    async def _normalize_request(self, request: OrchestrationRequest) -> TaskSpec:
        """Convert request into normalized TaskSpec."""
        logger.debug(f"Normalizing request: {request.intent}")
        
        # Use intent translator to extract goals and constraints
        translation = await self.intent_translator.translate(request.intent)
        
        # Determine privacy class and trust tier
        privacy_class = self._determine_privacy_class(request, translation)
        trust_tier = self._determine_trust_tier(request)
        
        return TaskSpec(
            task_id=str(uuid.uuid4()),
            trigger_type=request.trigger_type,
            intent=request.intent,
            goals=translation.goals,
            constraints=translation.constraints,
            privacy_class=privacy_class,
            trust_tier=trust_tier,
            user_id=request.user_id,
            session_id=request.session_id,
            metadata={
                "context_hints": request.context_hints,
                "preferences": request.preferences,
                "preview_mode": request.preview_mode
            }
        )
    
    async def _check_policy_and_consent(self, task_spec: TaskSpec) -> 'PolicyCheckResult':
        """Evaluate required scopes and trust tier."""
        logger.debug(f"Checking policy and consent for task {task_spec.task_id}")
        
        return await self.policy_gate.evaluate(task_spec)
    
    async def _pull_context(self, task_spec: TaskSpec) -> ContextSnapshot:
        """Query current device graph, environment, occupancy, tariffs, and quiet hours."""
        logger.debug(f"Pulling context for task {task_spec.task_id}")
        
        return await self.context_puller.get_snapshot(task_spec)
    
    async def _create_plan(
        self, 
        task_spec: TaskSpec, 
        context: ContextSnapshot,
        consent_refs: List[ConsentReference]
    ) -> 'PlanResult':
        """Produce an Execution Plan (DAG) with steps, ordering, fallbacks, guardrails."""
        logger.debug(f"Creating execution plan for task {task_spec.task_id}")
        
        return await self.planner.create_plan(
            task_spec=task_spec,
            context=context,
            consent_refs=consent_refs,
            config=self.config
        )
    
    async def _explain_plan(self, plan: ExecutionPlan, task_spec: TaskSpec) -> str:
        """Attach 'why this plan' summary and consent references."""
        logger.debug(f"Explaining plan {plan.plan_id}")
        
        return await self.explainer.explain_plan(plan, task_spec)
    
    async def _prepare_handover(self, plan: ExecutionPlan):
        """Prepare plan for handover to allocation system."""
        logger.debug(f"Preparing handover for plan {plan.plan_id}")
        
        # Calculate SLAs and budgets
        plan.slas = self._calculate_slas(plan)
        plan.budget = self._calculate_budget(plan)
        
        # Emit plan to allocation system (placeholder)
        await self._emit_to_allocation(plan)
    
    async def _execute_plan(self, plan_id: str, plan: ExecutionPlan):
        """Execute a plan."""
        try:
            logger.info(f"Executing plan {plan_id}")
            plan.status = ExecutionStatus.EXECUTING
            
            # Execute steps according to dependencies
            results = await self._execute_steps(plan)
            
            if all(result.get("status") == "completed" for result in results):
                plan.status = ExecutionStatus.COMPLETED
                self._update_metrics(plan_id, success=True)
            else:
                plan.status = ExecutionStatus.FAILED
                self._update_metrics(plan_id, success=False)
                
        except Exception as e:
            logger.error(f"Error executing plan {plan_id}: {e}")
            plan.status = ExecutionStatus.FAILED
            self._update_metrics(plan_id, success=False)
        finally:
            # Clean up
            if plan_id in self._active_plans:
                del self._active_plans[plan_id]
    
    async def _execute_steps(self, plan: ExecutionPlan) -> List[Dict[str, Any]]:
        """Execute all steps in the plan."""
        results = []
        
        # Build dependency graph and execute in order
        step_map = {step.step_id: step for step in plan.steps}
        executed = set()
        
        while len(executed) < len(plan.steps):
            # Find steps ready to execute
            ready_steps = [
                step for step in plan.steps
                if step.step_id not in executed and
                all(dep in executed for dep in step.dependencies)
            ]
            
            if not ready_steps:
                # Circular dependency or missing step
                break
            
            # Execute ready steps in parallel
            step_tasks = [
                self._execute_single_step(step) for step in ready_steps
            ]
            step_results = await asyncio.gather(*step_tasks, return_exceptions=True)
            
            for step, result in zip(ready_steps, step_results):
                if isinstance(result, Exception):
                    result = {"status": "failed", "error": str(result)}
                
                results.append(result)
                executed.add(step.step_id)
        
        return results
    
    async def _execute_single_step(self, step: ExecutionStep) -> Dict[str, Any]:
        """Execute a single step."""
        logger.debug(f"Executing step {step.step_id} ({step.step_type.value})")
        
        try:
            if step.step_type == StepType.DEVICE_CONTROL:
                return await self._execute_device_control(step)
            elif step.step_type == StepType.DATA_COLLECTION:
                return await self._execute_data_collection(step)
            elif step.step_type == StepType.ML_INFERENCE:
                return await self._execute_ml_inference(step)
            elif step.step_type == StepType.NOTIFICATION:
                return await self._execute_notification(step)
            else:
                return {"status": "failed", "error": f"Unknown step type: {step.step_type}"}
                
        except Exception as e:
            logger.error(f"Error executing step {step.step_id}: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def _execute_device_control(self, step: ExecutionStep) -> Dict[str, Any]:
        """Execute device control step."""
        # TODO: Integrate with device control service
        await asyncio.sleep(step.estimated_duration_ms / 1000)
        return {
            "status": "completed",
            "step_id": step.step_id,
            "device_id": step.device_id,
            "result": "device_controlled"
        }
    
    async def _execute_data_collection(self, step: ExecutionStep) -> Dict[str, Any]:
        """Execute data collection step."""
        # TODO: Integrate with data collection service
        await asyncio.sleep(step.estimated_duration_ms / 1000)
        return {
            "status": "completed",
            "step_id": step.step_id,
            "data_collected": True
        }
    
    async def _execute_ml_inference(self, step: ExecutionStep) -> Dict[str, Any]:
        """Execute ML inference step."""
        # TODO: Integrate with ML orchestrator
        await asyncio.sleep(step.estimated_duration_ms / 1000)
        return {
            "status": "completed",
            "step_id": step.step_id,
            "inference_result": "sample_result"
        }
    
    async def _execute_notification(self, step: ExecutionStep) -> Dict[str, Any]:
        """Execute notification step."""
        # TODO: Integrate with notification service
        await asyncio.sleep(step.estimated_duration_ms / 1000)
        return {
            "status": "completed",
            "step_id": step.step_id,
            "notification_sent": True
        }
    
    def _determine_privacy_class(self, request: OrchestrationRequest, translation: Any) -> PrivacyClass:
        """Determine privacy class based on request and translation."""
        # Simple heuristic - can be enhanced with ML
        if "private" in request.intent.lower() or "personal" in request.intent.lower():
            return PrivacyClass.CONFIDENTIAL
        elif "public" in request.intent.lower():
            return PrivacyClass.PUBLIC
        else:
            return PrivacyClass.INTERNAL
    
    def _determine_trust_tier(self, request: OrchestrationRequest) -> TrustTier:
        """Determine trust tier based on request."""
        # Simple heuristic - can be enhanced with user profile
        if request.user_id:
            return TrustTier.VERIFIED
        else:
            return TrustTier.BASIC
    
    def _calculate_slas(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Calculate SLAs for the plan."""
        total_duration = sum(step.estimated_duration_ms for step in plan.steps)
        return {
            "max_execution_time_ms": total_duration,
            "max_latency_ms": self.config.latency_budget_default_ms,
            "privacy_score_target": 0.9 if self.config.privacy_first else 0.7
        }
    
    def _calculate_budget(self, plan: ExecutionPlan) -> Dict[str, float]:
        """Calculate budget for the plan."""
        total_cost = sum(step.estimated_cost for step in plan.steps)
        return {
            "max_cost": min(total_cost * 1.2, self.config.cost_budget_default),
            "energy_budget": total_cost * 0.5,
            "cloud_budget": total_cost * 0.3
        }
    
    async def _emit_to_allocation(self, plan: ExecutionPlan):
        """Emit plan to allocation system."""
        # TODO: Integrate with allocation service
        logger.debug(f"Emitting plan {plan.plan_id} to allocation system")
    
    def _update_metrics(self, plan_id: str, success: bool):
        """Update plan metrics."""
        if plan_id in self._metrics:
            metrics = self._metrics[plan_id]
            metrics.total_executions += 1
            if success:
                metrics.success_rate = metrics.total_executions / (metrics.total_executions + metrics.failed_executions)
            else:
                metrics.failed_executions += 1
    
    async def _monitor_plan_execution(self):
        """Monitor active plan executions."""
        while self._running:
            try:
                # Check for replan events
                await self._check_replan_events()
                await asyncio.sleep(10)  # Check every 10 seconds
            except Exception as e:
                logger.error(f"Error in plan monitoring: {e}")
    
    async def _check_replan_events(self):
        """Check for events that require replanning."""
        # TODO: Implement replan event detection
        pass
    
    async def _cleanup_completed_plans(self):
        """Clean up completed plans."""
        while self._running:
            try:
                # Remove old completed plans
                current_time = datetime.utcnow()
                to_remove = []
                
                for plan_id, plan in self._plans.items():
                    if (plan.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED] and
                        (current_time - plan.updated_at) > timedelta(hours=24)):
                        to_remove.append(plan_id)
                
                for plan_id in to_remove:
                    del self._plans[plan_id]
                    if plan_id in self._metrics:
                        del self._metrics[plan_id]
                
                await asyncio.sleep(3600)  # Clean up every hour
            except Exception as e:
                logger.error(f"Error in cleanup: {e}")
    
    # Public API methods
    async def get_plan_status(self, plan_id: str) -> Optional[ExecutionPlan]:
        """Get the status of a specific plan."""
        return self._plans.get(plan_id)
    
    async def get_plan_metrics(self, plan_id: str) -> Optional[PlanMetrics]:
        """Get metrics for a specific plan."""
        return self._metrics.get(plan_id)
    
    async def cancel_plan(self, plan_id: str) -> bool:
        """Cancel a running plan."""
        if plan_id in self._plans:
            plan = self._plans[plan_id]
            if plan.status == ExecutionStatus.EXECUTING:
                plan.status = ExecutionStatus.CANCELLED
                if plan_id in self._active_plans:
                    self._active_plans[plan_id].cancel()
                    del self._active_plans[plan_id]
                return True
        return False
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get overall system metrics."""
        total_plans = len(self._plans)
        active_plans = len(self._active_plans)
        completed_plans = sum(1 for p in self._plans.values() if p.status == ExecutionStatus.COMPLETED)
        failed_plans = sum(1 for p in self._plans.values() if p.status == ExecutionStatus.FAILED)
        
        return {
            "total_plans": total_plans,
            "active_plans": active_plans,
            "completed_plans": completed_plans,
            "failed_plans": failed_plans,
            "success_rate": completed_plans / max(total_plans, 1),
            "average_planning_time_ms": sum(m.time_to_plan_ms for m in self._metrics.values()) / max(len(self._metrics), 1)
        }


# Placeholder classes for components that will be implemented next
@dataclass
class PolicyCheckResult:
    approved: bool
    reason: str = ""
    requires_approval: bool = False
    consent_refs: List[ConsentReference] = None
    
    def __post_init__(self):
        if self.consent_refs is None:
            self.consent_refs = []


@dataclass
class PlanResult:
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
