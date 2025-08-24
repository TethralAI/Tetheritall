"""
Orchestration Adapter
Converts recommendations into executable plans and interfaces with the orchestration system.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json

from .models import (
    ExecutionPlan, RecommendationCard, CombinationCandidate, CapabilityType,
    PrivacyLevel, SafetyLevel
)

logger = logging.getLogger(__name__)


class OrchestrationAdapter:
    """
    Adapter for converting recommendations into orchestration plans.
    
    Implements B5 from the spec:
    - Convert plans into orchestration tasks
    - Register triggers and schedules
    - Emit activation summaries
    - Monitor execution and collect signals
    """
    
    def __init__(self):
        self._orchestration_client = None  # Would connect to orchestration system
        self._execution_history: Dict[str, Dict[str, Any]] = {}
        
    async def execute_plan(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """
        Execute a plan through the orchestration system.
        
        Args:
            plan: Execution plan to execute
            
        Returns:
            Execution result
        """
        try:
            logger.info(f"Executing plan {plan.plan_id}")
            
            # Step 1: Validate plan
            validation_result = await self._validate_plan(plan)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": f"Plan validation failed: {validation_result['reason']}"
                }
            
            # Step 2: Convert to orchestration format
            orchestration_tasks = await self._convert_to_orchestration_format(plan)
            
            # Step 3: Submit to orchestration system
            execution_result = await self._submit_to_orchestration(orchestration_tasks)
            
            # Step 4: Monitor execution
            monitoring_result = await self._monitor_execution(plan.plan_id)
            
            # Step 5: Record execution history
            self._record_execution(plan.plan_id, execution_result, monitoring_result)
            
            return {
                "success": execution_result["success"],
                "plan_id": plan.plan_id,
                "execution_id": execution_result.get("execution_id"),
                "status": monitoring_result.get("status", "unknown"),
                "details": monitoring_result.get("details", {})
            }
            
        except Exception as e:
            logger.error(f"Error executing plan {plan.plan_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def create_execution_plan(
        self,
        recommendation: RecommendationCard,
        user_id: str
    ) -> ExecutionPlan:
        """
        Create an execution plan from a recommendation.
        
        Args:
            recommendation: Recommendation card
            user_id: User identifier
            
        Returns:
            Execution plan
        """
        plan = ExecutionPlan(
            plan_id=f"plan_{recommendation.recommendation_id}",
            recommendation_id=recommendation.recommendation_id
        )
        
        # Step 1: Create execution steps
        plan.steps = await self._create_execution_steps(recommendation)
        
        # Step 2: Create triggers
        plan.triggers = await self._create_triggers(recommendation)
        
        # Step 3: Create schedules
        plan.schedules = await self._create_schedules(recommendation)
        
        # Step 4: Create fallbacks
        plan.fallbacks = await self._create_fallbacks(recommendation)
        
        # Step 5: Add privacy and safety annotations
        plan.privacy_annotations = await self._create_privacy_annotations(recommendation)
        plan.safety_annotations = await self._create_safety_annotations(recommendation)
        
        # Step 6: Estimate duration
        plan.estimated_duration = await self._estimate_duration(plan)
        
        return plan
    
    async def _validate_plan(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Validate an execution plan."""
        issues = []
        
        # Check if plan has steps
        if not plan.steps:
            issues.append("No execution steps defined")
        
        # Check if plan has triggers or schedules
        if not plan.triggers and not plan.schedules:
            issues.append("No triggers or schedules defined")
        
        # Check for safety violations
        for step_id, safety_level in plan.safety_annotations.items():
            if safety_level == SafetyLevel.RESTRICTED:
                issues.append(f"Step {step_id} has restricted safety level")
        
        # Check for privacy violations
        for step_id, privacy_level in plan.privacy_annotations.items():
            if privacy_level == PrivacyLevel.SENSITIVE:
                issues.append(f"Step {step_id} has sensitive privacy level")
        
        return {
            "valid": len(issues) == 0,
            "reason": "; ".join(issues) if issues else None
        }
    
    async def _convert_to_orchestration_format(self, plan: ExecutionPlan) -> List[Dict[str, Any]]:
        """Convert execution plan to orchestration system format."""
        orchestration_tasks = []
        
        for step in plan.steps:
            task = {
                "task_id": f"{plan.plan_id}_{step['step_id']}",
                "type": step.get("type", "device_action"),
                "device_id": step.get("device_id"),
                "action": step.get("action"),
                "parameters": step.get("parameters", {}),
                "dependencies": step.get("dependencies", []),
                "timeout": step.get("timeout", 30),
                "retry_count": step.get("retry_count", 3),
                "privacy_level": plan.privacy_annotations.get(step['step_id'], PrivacyLevel.PERSONAL).value,
                "safety_level": plan.safety_annotations.get(step['step_id'], SafetyLevel.SAFE).value
            }
            orchestration_tasks.append(task)
        
        return orchestration_tasks
    
    async def _submit_to_orchestration(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Submit tasks to the orchestration system."""
        # This would interface with the actual orchestration system
        # For now, simulate the submission
        
        execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Simulate task submission
        submitted_tasks = []
        for task in tasks:
            submitted_task = {
                "task_id": task["task_id"],
                "status": "submitted",
                "execution_id": execution_id
            }
            submitted_tasks.append(submitted_task)
        
        return {
            "success": True,
            "execution_id": execution_id,
            "submitted_tasks": submitted_tasks
        }
    
    async def _monitor_execution(self, plan_id: str) -> Dict[str, Any]:
        """Monitor execution of a plan."""
        # This would monitor the actual execution
        # For now, simulate monitoring
        
        await asyncio.sleep(1)  # Simulate monitoring delay
        
        return {
            "status": "completed",
            "details": {
                "completed_steps": 3,
                "failed_steps": 0,
                "total_duration": 45,
                "user_interactions": 0
            }
        }
    
    def _record_execution(self, plan_id: str, execution_result: Dict[str, Any], monitoring_result: Dict[str, Any]):
        """Record execution history."""
        self._execution_history[plan_id] = {
            "execution_time": datetime.now(),
            "execution_result": execution_result,
            "monitoring_result": monitoring_result
        }
    
    async def _create_execution_steps(self, recommendation: RecommendationCard) -> List[Dict[str, Any]]:
        """Create execution steps from recommendation."""
        steps = []
        step_id = 1
        
        combination = recommendation.combination
        if not combination:
            return steps
        
        # Create steps for each device
        for device in combination.devices:
            step = await self._create_device_step(device, step_id)
            if step:
                steps.append(step)
                step_id += 1
        
        # Create steps for each service
        for service in combination.services:
            step = await self._create_service_step(service, step_id)
            if step:
                steps.append(step)
                step_id += 1
        
        return steps
    
    async def _create_device_step(self, device, step_id: int) -> Optional[Dict[str, Any]]:
        """Create execution step for a device."""
        step = {
            "step_id": f"step_{step_id}",
            "type": "device_action",
            "device_id": device.device_id,
            "device_name": device.device_name,
            "capability_type": device.capability_type.value
        }
        
        # Add action based on capability type
        if device.capability_type == CapabilityType.LIGHTING:
            step.update({
                "action": "set_lighting",
                "parameters": {
                    "brightness": 80,
                    "color_temp": 2700,
                    "duration": 120
                }
            })
        elif device.capability_type == CapabilityType.ACTUATION:
            step.update({
                "action": "set_state",
                "parameters": {
                    "state": "on",
                    "duration": 300
                }
            })
        elif device.capability_type == CapabilityType.CLIMATE:
            step.update({
                "action": "set_temperature",
                "parameters": {
                    "temperature": 22,
                    "mode": "auto"
                }
            })
        elif device.capability_type == CapabilityType.SENSING:
            step.update({
                "action": "enable_monitoring",
                "parameters": {
                    "sensitivity": 5,
                    "timeout": 30
                }
            })
        else:
            step.update({
                "action": "activate",
                "parameters": {}
            })
        
        return step
    
    async def _create_service_step(self, service, step_id: int) -> Optional[Dict[str, Any]]:
        """Create execution step for a service."""
        step = {
            "step_id": f"step_{step_id}",
            "type": "service_action",
            "service_id": service.service_id,
            "service_name": service.service_name,
            "capability_type": service.capability_type.value
        }
        
        # Add action based on capability type
        if service.capability_type == CapabilityType.WEATHER:
            step.update({
                "action": "get_weather",
                "parameters": {
                    "location": "auto"
                }
            })
        elif service.capability_type == CapabilityType.CALENDAR:
            step.update({
                "action": "check_calendar",
                "parameters": {
                    "time_window": 3600
                }
            })
        elif service.capability_type == CapabilityType.PRESENCE:
            step.update({
                "action": "check_presence",
                "parameters": {}
            })
        else:
            step.update({
                "action": "activate",
                "parameters": {}
            })
        
        return step
    
    async def _create_triggers(self, recommendation: RecommendationCard) -> List[Dict[str, Any]]:
        """Create triggers for the recommendation."""
        triggers = []
        combination = recommendation.combination
        
        if not combination:
            return triggers
        
        # Create triggers based on devices and services
        for device in combination.devices:
            if device.capability_type == CapabilityType.SENSING:
                trigger = {
                    "trigger_id": f"trigger_{device.device_id}",
                    "type": "motion_detected",
                    "device_id": device.device_id,
                    "conditions": {
                        "motion": True,
                        "timeout": 30
                    }
                }
                triggers.append(trigger)
        
        for service in combination.services:
            if service.capability_type == CapabilityType.TIME:
                trigger = {
                    "trigger_id": f"trigger_{service.service_id}",
                    "type": "time_based",
                    "service_id": service.service_id,
                    "conditions": {
                        "time": "sunset",
                        "offset": 0
                    }
                }
                triggers.append(trigger)
            elif service.capability_type == CapabilityType.WEATHER:
                trigger = {
                    "trigger_id": f"trigger_{service.service_id}",
                    "type": "weather_based",
                    "service_id": service.service_id,
                    "conditions": {
                        "condition": "rain",
                        "threshold": 0.5
                    }
                }
                triggers.append(trigger)
        
        return triggers
    
    async def _create_schedules(self, recommendation: RecommendationCard) -> List[Dict[str, Any]]:
        """Create schedules for the recommendation."""
        schedules = []
        combination = recommendation.combination
        
        if not combination:
            return schedules
        
        # Create schedules based on recommendation category
        if recommendation.category == "comfort":
            schedule = {
                "schedule_id": f"schedule_{recommendation.recommendation_id}",
                "type": "daily",
                "time": "18:00",
                "days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
                "enabled": True
            }
            schedules.append(schedule)
        elif recommendation.category == "energy":
            schedule = {
                "schedule_id": f"schedule_{recommendation.recommendation_id}",
                "type": "daily",
                "time": "22:00",
                "days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
                "enabled": True
            }
            schedules.append(schedule)
        
        return schedules
    
    async def _create_fallbacks(self, recommendation: RecommendationCard) -> List[Dict[str, Any]]:
        """Create fallback actions for the recommendation."""
        fallbacks = []
        combination = recommendation.combination
        
        if not combination:
            return fallbacks
        
        # Create fallbacks for critical actions
        for device in combination.devices:
            if device.capability_type == CapabilityType.LIGHTING:
                fallback = {
                    "fallback_id": f"fallback_{device.device_id}",
                    "trigger": "device_unreachable",
                    "device_id": device.device_id,
                    "action": "notify_user",
                    "message": f"Unable to control {device.device_name}. Please check device connectivity."
                }
                fallbacks.append(fallback)
        
        return fallbacks
    
    async def _create_privacy_annotations(self, recommendation: RecommendationCard) -> Dict[str, PrivacyLevel]:
        """Create privacy annotations for execution steps."""
        annotations = {}
        combination = recommendation.combination
        
        if not combination:
            return annotations
        
        # Annotate each device and service with privacy level
        for device in combination.devices:
            step_id = f"step_{device.device_id}"
            annotations[step_id] = device.privacy_level
        
        for service in combination.services:
            step_id = f"step_{service.service_id}"
            annotations[step_id] = service.privacy_level
        
        return annotations
    
    async def _create_safety_annotations(self, recommendation: RecommendationCard) -> Dict[str, SafetyLevel]:
        """Create safety annotations for execution steps."""
        annotations = {}
        combination = recommendation.combination
        
        if not combination:
            return annotations
        
        # Annotate each device and service with safety level
        for device in combination.devices:
            step_id = f"step_{device.device_id}"
            annotations[step_id] = device.safety_level
        
        for service in combination.services:
            step_id = f"step_{service.service_id}"
            annotations[step_id] = service.safety_level
        
        return annotations
    
    async def _estimate_duration(self, plan: ExecutionPlan) -> int:
        """Estimate execution duration for the plan."""
        # Base duration for each step
        base_duration = 15  # seconds per step
        
        # Add duration for each step
        total_duration = len(plan.steps) * base_duration
        
        # Add extra time for complex actions
        for step in plan.steps:
            if step.get("action") in ["set_lighting", "set_temperature"]:
                total_duration += 10  # Extra time for device control
        
        # Add time for service calls
        for step in plan.steps:
            if step.get("type") == "service_action":
                total_duration += 5  # Extra time for service calls
        
        return total_duration
    
    async def get_execution_status(self, plan_id: str) -> Dict[str, Any]:
        """Get execution status for a plan."""
        if plan_id in self._execution_history:
            return self._execution_history[plan_id]
        
        return {
            "status": "not_found",
            "message": f"Plan {plan_id} not found in execution history"
        }
    
    async def cancel_execution(self, plan_id: str) -> Dict[str, Any]:
        """Cancel execution of a plan."""
        try:
            # This would cancel the actual execution in the orchestration system
            logger.info(f"Cancelling execution of plan {plan_id}")
            
            return {
                "success": True,
                "message": f"Execution of plan {plan_id} cancelled"
            }
            
        except Exception as e:
            logger.error(f"Error cancelling execution of plan {plan_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
