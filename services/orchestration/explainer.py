"""
Plan Explainer
Attaches 'why this plan' summary and consent references.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .models import ExecutionPlan, TaskSpec, ExecutionStep, StepType, PrivacyClass, TrustTier

logger = logging.getLogger(__name__)


class PlanExplainer:
    """Explains execution plans with rationale and consent references."""
    
    def __init__(self):
        # Explanation templates
        self._explanation_templates = {
            "privacy_focused": "This plan prioritizes privacy by keeping {local_percentage}% of operations local and avoiding cloud processing for sensitive data.",
            "cost_optimized": "This plan minimizes costs by using local processing ({local_percentage}%) and selecting low-cost device operations.",
            "latency_optimized": "This plan optimizes for speed with {fast_steps} fast operations and local processing to reduce network latency.",
            "comfort_optimized": "This plan focuses on user comfort by prioritizing comfort-related devices and monitoring environmental conditions.",
            "balanced": "This plan balances privacy ({local_percentage}% local), cost (${total_cost}), and performance ({total_duration}ms) for optimal results."
        }
        
        # Step explanation templates
        self._step_explanations = {
            StepType.DEVICE_CONTROL: "Control {device_type} device {device_id} to achieve {goal}",
            StepType.DATA_COLLECTION: "Collect {data_type} data for {duration} seconds to support {goal}",
            StepType.ML_INFERENCE: "Run {model_type} inference on {input_data} to {goal}",
            StepType.NOTIFICATION: "Send {channel} notification with {priority} priority to inform about {goal}"
        }
        
        # Consent explanation templates
        self._consent_explanations = {
            "internal_read": "Read access to internal system data for device control and monitoring",
            "internal_write": "Write access to internal system settings for device configuration",
            "confidential_read": "Read access to confidential user data for personalized services",
            "confidential_write": "Write access to confidential user data for user preferences",
            "restricted_access": "Access to restricted system functions for advanced operations"
        }
    
    async def explain_plan(self, plan: ExecutionPlan, task_spec: TaskSpec) -> str:
        """
        Generate a comprehensive explanation for the execution plan.
        
        Args:
            plan: The execution plan to explain
            task_spec: The original task specification
            
        Returns:
            Human-readable explanation of the plan
        """
        logger.debug(f"Explaining plan {plan.plan_id}")
        
        explanation_parts = []
        
        # Overall plan summary
        summary = self._generate_plan_summary(plan, task_spec)
        explanation_parts.append(summary)
        
        # Step-by-step explanation
        steps_explanation = self._explain_steps(plan.steps, task_spec)
        explanation_parts.append(steps_explanation)
        
        # Privacy and security explanation
        privacy_explanation = self._explain_privacy_aspects(plan)
        explanation_parts.append(privacy_explanation)
        
        # Consent explanation
        consent_explanation = self._explain_consent_requirements(plan.consent_references)
        explanation_parts.append(consent_explanation)
        
        # Cost and performance explanation
        performance_explanation = self._explain_performance_aspects(plan)
        explanation_parts.append(performance_explanation)
        
        # Guardrails explanation
        guardrails_explanation = self._explain_guardrails(plan.steps)
        explanation_parts.append(guardrails_explanation)
        
        return "\n\n".join(explanation_parts)
    
    def _generate_plan_summary(self, plan: ExecutionPlan, task_spec: TaskSpec) -> str:
        """Generate a high-level summary of the plan."""
        # Calculate key metrics
        total_steps = len(plan.steps)
        local_steps = sum(1 for step in plan.steps if step.local_execution)
        local_percentage = (local_steps / total_steps * 100) if total_steps > 0 else 0
        total_cost = sum(step.estimated_cost for step in plan.steps)
        total_duration = sum(step.estimated_duration_ms for step in plan.steps)
        fast_steps = sum(1 for step in plan.steps if step.estimated_duration_ms < 1000)
        
        # Determine plan type
        plan_type = self._determine_plan_type(plan, task_spec)
        
        # Get template and fill in values
        template = self._explanation_templates.get(plan_type, self._explanation_templates["balanced"])
        
        summary = template.format(
            local_percentage=int(local_percentage),
            total_cost=f"{total_cost:.3f}",
            total_duration=total_duration,
            fast_steps=fast_steps
        )
        
        return f"## Plan Summary\n\n{summary}\n\nThis plan contains {total_steps} steps and will take approximately {total_duration}ms to complete."
    
    def _explain_steps(self, steps: List[ExecutionStep], task_spec: TaskSpec) -> str:
        """Explain each step in the plan."""
        if not steps:
            return "## Steps\n\nNo steps in this plan."
        
        step_explanations = []
        step_explanations.append("## Steps\n")
        
        for i, step in enumerate(steps, 1):
            step_explanation = self._explain_single_step(step, i, task_spec)
            step_explanations.append(step_explanation)
        
        return "\n".join(step_explanations)
    
    def _explain_single_step(self, step: ExecutionStep, step_number: int, task_spec: TaskSpec) -> str:
        """Explain a single step."""
        # Get base explanation
        template = self._step_explanations.get(step.step_type, "Execute {step_type} operation")
        
        # Extract relevant goal for this step
        relevant_goal = self._find_relevant_goal(step, task_spec.goals)
        
        # Fill template with step-specific information
        explanation = template.format(
            device_type=step.parameters.get("device_type", "unknown"),
            device_id=step.device_id or "unknown",
            goal=relevant_goal or "task objectives",
            data_type=step.parameters.get("data_type", "sensor"),
            duration=step.parameters.get("duration", 300),
            model_type=step.parameters.get("model_type", "prediction"),
            input_data=step.parameters.get("input_data", "data"),
            channel=step.parameters.get("channel", "push"),
            priority=step.parameters.get("priority", "normal"),
            step_type=step.step_type.value
        )
        
        # Add execution details
        execution_details = []
        if step.local_execution:
            execution_details.append("local execution")
        else:
            execution_details.append("cloud execution")
        
        execution_details.append(f"~{step.estimated_duration_ms}ms")
        execution_details.append(f"~${step.estimated_cost:.3f}")
        
        # Add privacy class
        privacy_info = f"privacy: {step.privacy_class.value}"
        execution_details.append(privacy_info)
        
        # Format the complete step explanation
        step_text = f"**Step {step_number}:** {explanation}\n"
        step_text += f"*Execution: {', '.join(execution_details)}*\n"
        
        # Add guardrails if any
        if step.guardrails:
            guardrail_texts = []
            for guardrail in step.guardrails:
                guardrail_texts.append(f"{guardrail['type']}: {guardrail['action']}")
            step_text += f"*Guardrails: {', '.join(guardrail_texts)}*\n"
        
        return step_text
    
    def _explain_privacy_aspects(self, plan: ExecutionPlan) -> str:
        """Explain privacy and security aspects of the plan."""
        local_steps = sum(1 for step in plan.steps if step.local_execution)
        total_steps = len(plan.steps)
        local_percentage = (local_steps / total_steps * 100) if total_steps > 0 else 0
        
        privacy_classes = {}
        for step in plan.steps:
            privacy_class = step.privacy_class.value
            privacy_classes[privacy_class] = privacy_classes.get(privacy_class, 0) + 1
        
        privacy_text = "## Privacy & Security\n\n"
        privacy_text += f"This plan keeps {local_percentage:.1f}% of operations local to protect your privacy.\n\n"
        
        privacy_text += "**Privacy Classification:**\n"
        for privacy_class, count in privacy_classes.items():
            privacy_text += f"- {privacy_class}: {count} steps\n"
        
        # Add security notes
        high_privacy_steps = sum(1 for step in plan.steps 
                               if step.privacy_class in [PrivacyClass.CONFIDENTIAL, PrivacyClass.RESTRICTED])
        if high_privacy_steps > 0:
            privacy_text += f"\n⚠️ **Security Note:** {high_privacy_steps} steps involve sensitive data and will be processed locally with enhanced security measures.\n"
        
        return privacy_text
    
    def _explain_consent_requirements(self, consent_refs: List['ConsentReference']) -> str:
        """Explain consent requirements for the plan."""
        if not consent_refs:
            return "## Consent\n\nNo additional consent required for this plan."
        
        consent_text = "## Consent Requirements\n\n"
        consent_text += "This plan requires the following permissions:\n\n"
        
        for consent_ref in consent_refs:
            for scope in consent_ref.scopes:
                explanation = self._consent_explanations.get(scope, f"Access to {scope}")
                consent_text += f"- **{scope}**: {explanation}\n"
                
                if consent_ref.dynamic_consent:
                    consent_text += "  *(Dynamic consent - will be requested when needed)*\n"
                
                if consent_ref.expires_at:
                    consent_text += f"  *(Expires: {consent_ref.expires_at.strftime('%Y-%m-%d %H:%M:%S')})*\n"
        
        return consent_text
    
    def _explain_performance_aspects(self, plan: ExecutionPlan) -> str:
        """Explain performance and cost aspects of the plan."""
        total_cost = sum(step.estimated_cost for step in plan.steps)
        total_duration = sum(step.estimated_duration_ms for step in plan.steps)
        
        # Calculate performance metrics
        fast_steps = sum(1 for step in plan.steps if step.estimated_duration_ms < 1000)
        slow_steps = sum(1 for step in plan.steps if step.estimated_duration_ms > 3000)
        
        performance_text = "## Performance & Cost\n\n"
        performance_text += f"**Estimated Performance:**\n"
        performance_text += f"- Total execution time: {total_duration}ms\n"
        performance_text += f"- Fast operations (<1s): {fast_steps}\n"
        performance_text += f"- Slow operations (>3s): {slow_steps}\n"
        performance_text += f"- Average step time: {total_duration/len(plan.steps):.0f}ms\n\n"
        
        performance_text += f"**Estimated Cost:**\n"
        performance_text += f"- Total cost: ${total_cost:.3f}\n"
        performance_text += f"- Average cost per step: ${total_cost/len(plan.steps):.3f}\n"
        
        # Add cost optimization notes
        if total_cost < 0.05:
            performance_text += "\n✅ **Cost Efficient:** This plan uses low-cost operations.\n"
        elif total_cost > 0.2:
            performance_text += "\n⚠️ **High Cost:** This plan involves expensive operations.\n"
        
        return performance_text
    
    def _explain_guardrails(self, steps: List[ExecutionStep]) -> str:
        """Explain safety guardrails in the plan."""
        all_guardrails = []
        for step in steps:
            for guardrail in step.guardrails:
                all_guardrails.append({
                    "step": step.step_id,
                    "type": guardrail["type"],
                    "action": guardrail["action"],
                    "reason": guardrail["reason"]
                })
        
        if not all_guardrails:
            return "## Safety Guardrails\n\nNo specific guardrails required for this plan."
        
        guardrails_text = "## Safety Guardrails\n\n"
        guardrails_text += "The following safety measures are in place:\n\n"
        
        # Group guardrails by type
        guardrail_types = {}
        for guardrail in all_guardrails:
            guardrail_type = guardrail["type"]
            if guardrail_type not in guardrail_types:
                guardrail_types[guardrail_type] = []
            guardrail_types[guardrail_type].append(guardrail)
        
        for guardrail_type, guardrails in guardrail_types.items():
            guardrails_text += f"**{guardrail_type.title()} Guardrails:**\n"
            for guardrail in guardrails:
                guardrails_text += f"- {guardrail['action']}: {guardrail['reason']}\n"
            guardrails_text += "\n"
        
        return guardrails_text
    
    def _determine_plan_type(self, plan: ExecutionPlan, task_spec: TaskSpec) -> str:
        """Determine the type of plan based on its characteristics."""
        # Calculate metrics
        local_steps = sum(1 for step in plan.steps if step.local_execution)
        total_steps = len(plan.steps)
        local_percentage = (local_steps / total_steps * 100) if total_steps > 0 else 0
        total_cost = sum(step.estimated_cost for step in plan.steps)
        total_duration = sum(step.estimated_duration_ms for step in plan.steps)
        
        # Check goal priorities
        goal_weights = {goal.target: goal.weight for goal in task_spec.goals}
        
        # Determine plan type based on characteristics
        if local_percentage > 90:
            return "privacy_focused"
        elif total_cost < 0.05:
            return "cost_optimized"
        elif total_duration < 2000:
            return "latency_optimized"
        elif "comfort" in goal_weights and goal_weights["comfort"] > 0.7:
            return "comfort_optimized"
        else:
            return "balanced"
    
    def _find_relevant_goal(self, step: ExecutionStep, goals: List['Goal']) -> Optional[str]:
        """Find the most relevant goal for a step."""
        if not goals:
            return None
        
        # Simple heuristic: match step type with goal target
        step_type = step.step_type.value
        
        for goal in goals:
            goal_target = goal.target.lower()
            
            if step_type == "device_control" and any(device in goal_target for device in ["thermostat", "light", "device"]):
                return goal_target
            elif step_type == "data_collection" and any(data in goal_target for data in ["data", "monitor", "collect"]):
                return goal_target
            elif step_type == "ml_inference" and any(ml in goal_target for ml in ["prediction", "inference", "learning"]):
                return goal_target
            elif step_type == "notification" and any(notif in goal_target for notif in ["notify", "alert", "message"]):
                return goal_target
        
        # Return the highest weight goal if no specific match
        return max(goals, key=lambda g: g.weight).target
    
    async def generate_approval_summary(self, plan: ExecutionPlan) -> str:
        """Generate a summary for user approval."""
        summary_parts = []
        
        # Quick overview
        total_steps = len(plan.steps)
        local_steps = sum(1 for step in plan.steps if step.local_execution)
        total_cost = sum(step.estimated_cost for step in plan.steps)
        total_duration = sum(step.estimated_duration_ms for step in plan.steps)
        
        summary_parts.append(f"**Plan Overview:**")
        summary_parts.append(f"- {total_steps} steps")
        summary_parts.append(f"- {local_steps}/{total_steps} local operations")
        summary_parts.append(f"- Estimated cost: ${total_cost:.3f}")
        summary_parts.append(f"- Estimated time: {total_duration}ms")
        
        # Key actions
        key_actions = []
        for step in plan.steps:
            if step.step_type == StepType.DEVICE_CONTROL:
                device_type = step.parameters.get("device_type", "device")
                key_actions.append(f"Control {device_type}")
            elif step.step_type == StepType.NOTIFICATION:
                key_actions.append("Send notification")
        
        if key_actions:
            summary_parts.append(f"\n**Key Actions:**")
            summary_parts.extend([f"- {action}" for action in set(key_actions)])
        
        # Privacy summary
        high_privacy_steps = sum(1 for step in plan.steps 
                               if step.privacy_class in [PrivacyClass.CONFIDENTIAL, PrivacyClass.RESTRICTED])
        if high_privacy_steps > 0:
            summary_parts.append(f"\n**Privacy:** {high_privacy_steps} steps involve sensitive data")
        
        return "\n".join(summary_parts)
    
    async def generate_debug_info(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Generate debug information for the plan."""
        return {
            "plan_id": plan.plan_id,
            "total_steps": len(plan.steps),
            "step_types": [step.step_type.value for step in plan.steps],
            "privacy_classes": [step.privacy_class.value for step in plan.steps],
            "local_execution_count": sum(1 for step in plan.steps if step.local_execution),
            "total_estimated_cost": sum(step.estimated_cost for step in plan.steps),
            "total_estimated_duration": sum(step.estimated_duration_ms for step in plan.steps),
            "consent_scopes": [scope for consent in plan.consent_references for scope in consent.scopes],
            "guardrails_count": sum(len(step.guardrails) for step in plan.steps)
        }
