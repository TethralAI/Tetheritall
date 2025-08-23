"""
Orchestration Engine
Handles workflow management, task scheduling, and service coordination.
Enhanced with the new orchestration agent for intent-based planning.
"""

from __future__ import annotations

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from enum import Enum

from shared.config.settings import settings
from .agent import OrchestrationAgent, OrchestrationConfig
from .models import OrchestrationRequest, OrchestrationResponse, ExecutionStatus

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """Workflow status options."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OrchestrationEngine:
    """Enhanced workflow orchestration engine with intent-based planning."""
    
    def __init__(self):
        self._running = False
        self._workflows: Dict[str, Dict[str, Any]] = {}
        self._workflow_tasks: List[asyncio.Task] = []
        
        # Initialize the orchestration agent
        config = OrchestrationConfig(
            max_planning_time_ms=5000,
            max_plan_alternatives=3,
            enable_preview_mode=True,
            enable_replanning=True,
            privacy_first=True,
            local_execution_preference=0.8,
            cost_budget_default=1.0,
            latency_budget_default_ms=5000
        )
        self._agent = OrchestrationAgent(config)
        
    async def start(self):
        """Start the orchestration engine and agent."""
        self._running = True
        await self._agent.start()
        logger.info("Orchestration engine started")
        
    async def stop(self):
        """Stop the orchestration engine and agent."""
        self._running = False
        await self._agent.stop()
        
        # Cancel all workflow tasks
        for task in self._workflow_tasks:
            task.cancel()
        logger.info("Orchestration engine stopped")
        
    def is_running(self) -> bool:
        """Check if the engine is running."""
        return self._running
        
    async def create_execution_plan(self, request: OrchestrationRequest) -> OrchestrationResponse:
        """
        Create an execution plan using the orchestration agent.
        
        Args:
            request: Orchestration request with intent and parameters
            
        Returns:
            OrchestrationResponse with the created plan
        """
        if not self._running:
            raise RuntimeError("Orchestration engine is not running")
        
        return await self._agent.create_execution_plan(request)
    
    async def get_plan_status(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a specific plan."""
        plan = await self._agent.get_plan_status(plan_id)
        if plan:
            return {
                "plan_id": plan.plan_id,
                "status": plan.status.value,
                "rationale": plan.rationale,
                "approval_required": plan.approval_required,
                "created_at": plan.created_at.isoformat(),
                "updated_at": plan.updated_at.isoformat()
            }
        return None
    
    async def get_plan_metrics(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific plan."""
        metrics = await self._agent.get_plan_metrics(plan_id)
        if metrics:
            return {
                "plan_id": metrics.plan_id,
                "success_rate": metrics.success_rate,
                "time_to_plan_ms": metrics.time_to_plan_ms,
                "approval_rate": metrics.approval_rate,
                "user_overrides": metrics.user_overrides,
                "privacy_score": metrics.privacy_score,
                "replan_frequency": metrics.replan_frequency,
                "total_executions": metrics.total_executions,
                "failed_executions": metrics.failed_executions,
                "average_execution_time_ms": metrics.average_execution_time_ms,
                "cost_per_execution": metrics.cost_per_execution
            }
        return None
    
    async def cancel_plan(self, plan_id: str) -> bool:
        """Cancel a running plan."""
        return await self._agent.cancel_plan(plan_id)
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get overall system metrics."""
        agent_metrics = await self._agent.get_system_metrics()
        
        # Combine with workflow metrics
        workflow_metrics = {
            "total_workflows": len(self._workflows),
            "active_workflows": sum(1 for w in self._workflows.values() if w["status"] == WorkflowStatus.RUNNING.value),
            "completed_workflows": sum(1 for w in self._workflows.values() if w["status"] == WorkflowStatus.COMPLETED.value),
            "failed_workflows": sum(1 for w in self._workflows.values() if w["status"] == WorkflowStatus.FAILED.value)
        }
        
        return {
            **agent_metrics,
            **workflow_metrics
        }
        
    # Legacy workflow methods for backward compatibility
    async def list_workflows(self) -> List[Dict[str, Any]]:
        """List all workflows."""
        return [
            {
                "id": workflow_id,
                **workflow_info
            }
            for workflow_id, workflow_info in self._workflows.items()
        ]
        
    async def create_workflow(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new workflow."""
        if not self._running:
            raise RuntimeError("Orchestration engine is not running")
            
        workflow_id = f"workflow_{len(self._workflows) + 1}"
        
        workflow_info = {
            "name": workflow.get("name", "Unnamed Workflow"),
            "description": workflow.get("description", ""),
            "steps": workflow.get("steps", []),
            "status": WorkflowStatus.PENDING.value,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "execution_count": 0
        }
        
        self._workflows[workflow_id] = workflow_info
        
        # Start workflow execution
        task = asyncio.create_task(self._execute_workflow(workflow_id))
        self._workflow_tasks.append(task)
        
        logger.info(f"Created workflow {workflow_id}: {workflow_info['name']}")
        
        return {
            "workflow_id": workflow_id,
            "status": "created",
            **workflow_info
        }
        
    async def _execute_workflow(self, workflow_id: str):
        """Execute a workflow."""
        try:
            workflow = self._workflows[workflow_id]
            workflow["status"] = WorkflowStatus.RUNNING.value
            workflow["updated_at"] = datetime.utcnow().isoformat()
            
            logger.info(f"Executing workflow {workflow_id}")
            
            steps = workflow.get("steps", [])
            results = []
            
            for i, step in enumerate(steps):
                step_id = step.get("id", f"step_{i}")
                step_type = step.get("type", "unknown")
                
                logger.info(f"Executing step {step_id} ({step_type})")
                
                # Execute step based on type
                result = await self._execute_step(step)
                results.append({
                    "step_id": step_id,
                    "step_type": step_type,
                    "result": result,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # Check if workflow should continue
                if result.get("status") == "failed":
                    workflow["status"] = WorkflowStatus.FAILED.value
                    break
                    
            # Update workflow status
            if workflow["status"] != WorkflowStatus.FAILED.value:
                workflow["status"] = WorkflowStatus.COMPLETED.value
                
            workflow["updated_at"] = datetime.utcnow().isoformat()
            workflow["execution_count"] += 1
            workflow["last_results"] = results
            
            logger.info(f"Workflow {workflow_id} completed with status: {workflow['status']}")
            
        except Exception as e:
            logger.error(f"Error executing workflow {workflow_id}: {e}")
            workflow["status"] = WorkflowStatus.FAILED.value
            workflow["error"] = str(e)
            workflow["updated_at"] = datetime.utcnow().isoformat()
            
    async def _execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single workflow step."""
        step_type = step.get("type", "unknown")
        
        try:
            if step_type == "discovery":
                return await self._execute_discovery_step(step)
            elif step_type == "ml_inference":
                return await self._execute_ml_step(step)
            elif step_type == "notification":
                return await self._execute_notification_step(step)
            elif step_type == "wait":
                return await self._execute_wait_step(step)
            else:
                return {
                    "status": "failed",
                    "error": f"Unknown step type: {step_type}"
                }
                
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }
            
    async def _execute_discovery_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a discovery step."""
        # TODO: Integrate with discovery service
        await asyncio.sleep(1)  # Simulate discovery time
        return {
            "status": "completed",
            "devices_found": 5,
            "scan_duration_ms": 1000
        }
        
    async def _execute_ml_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an ML inference step."""
        # TODO: Integrate with ML orchestrator
        await asyncio.sleep(2)  # Simulate ML processing time
        return {
            "status": "completed",
            "model_used": step.get("model_id", "unknown"),
            "inference_time_ms": 2000,
            "confidence": 0.95
        }
        
    async def _execute_notification_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a notification step."""
        # TODO: Integrate with notification service
        await asyncio.sleep(0.5)  # Simulate notification time
        return {
            "status": "completed",
            "notification_sent": True,
            "recipients": step.get("recipients", [])
        }
        
    async def _execute_wait_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a wait step."""
        wait_time = step.get("duration_seconds", 1)
        await asyncio.sleep(wait_time)
        return {
            "status": "completed",
            "waited_seconds": wait_time
        }
        
    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific workflow."""
        if workflow_id not in self._workflows:
            return None
            
        workflow = self._workflows[workflow_id]
        return {
            "id": workflow_id,
            **workflow
        }
        
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow."""
        if workflow_id not in self._workflows:
            return False
            
        workflow = self._workflows[workflow_id]
        if workflow["status"] == WorkflowStatus.RUNNING.value:
            workflow["status"] = WorkflowStatus.CANCELLED.value
            workflow["updated_at"] = datetime.utcnow().isoformat()
            logger.info(f"Cancelled workflow {workflow_id}")
            return True
            
        return False
