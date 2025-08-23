"""
Policy Gate
Evaluates required scopes and trust tier for task execution.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from .models import TaskSpec, ConsentReference, PrivacyClass, TrustTier

logger = logging.getLogger(__name__)


@dataclass
class PolicyCheckResult:
    """Result of policy and consent evaluation."""
    approved: bool
    reason: str = ""
    requires_approval: bool = False
    consent_refs: List[ConsentReference] = None
    redacted_fields: List[str] = None
    routing_target: Optional[str] = None
    
    def __post_init__(self):
        if self.consent_refs is None:
            self.consent_refs = []
        if self.redacted_fields is None:
            self.redacted_fields = []


class PolicyGate:
    """Evaluates required scopes and trust tier for task execution."""
    
    def __init__(self):
        # Policy rules for different privacy classes and trust tiers
        self._policy_rules = {
            PrivacyClass.PUBLIC: {
                TrustTier.UNTRUSTED: {"approval_required": False, "scope_required": []},
                TrustTier.BASIC: {"approval_required": False, "scope_required": []},
                TrustTier.VERIFIED: {"approval_required": False, "scope_required": []},
                TrustTier.TRUSTED: {"approval_required": False, "scope_required": []},
                TrustTier.PRIVILEGED: {"approval_required": False, "scope_required": []}
            },
            PrivacyClass.INTERNAL: {
                TrustTier.UNTRUSTED: {"approval_required": True, "scope_required": ["internal_read"]},
                TrustTier.BASIC: {"approval_required": False, "scope_required": ["internal_read"]},
                TrustTier.VERIFIED: {"approval_required": False, "scope_required": ["internal_read", "internal_write"]},
                TrustTier.TRUSTED: {"approval_required": False, "scope_required": ["internal_read", "internal_write"]},
                TrustTier.PRIVILEGED: {"approval_required": False, "scope_required": ["internal_read", "internal_write"]}
            },
            PrivacyClass.CONFIDENTIAL: {
                TrustTier.UNTRUSTED: {"approval_required": True, "scope_required": ["confidential_read"]},
                TrustTier.BASIC: {"approval_required": True, "scope_required": ["confidential_read"]},
                TrustTier.VERIFIED: {"approval_required": False, "scope_required": ["confidential_read", "confidential_write"]},
                TrustTier.TRUSTED: {"approval_required": False, "scope_required": ["confidential_read", "confidential_write"]},
                TrustTier.PRIVILEGED: {"approval_required": False, "scope_required": ["confidential_read", "confidential_write"]}
            },
            PrivacyClass.RESTRICTED: {
                TrustTier.UNTRUSTED: {"approval_required": True, "scope_required": ["restricted_access"]},
                TrustTier.BASIC: {"approval_required": True, "scope_required": ["restricted_access"]},
                TrustTier.VERIFIED: {"approval_required": True, "scope_required": ["restricted_access"]},
                TrustTier.TRUSTED: {"approval_required": False, "scope_required": ["restricted_access"]},
                TrustTier.PRIVILEGED: {"approval_required": False, "scope_required": ["restricted_access"]}
            }
        }
        
        # Scope definitions
        self._scope_definitions = {
            "internal_read": {
                "description": "Read internal system data",
                "permissions": ["read_device_state", "read_system_metrics"],
                "expires_in_hours": 24
            },
            "internal_write": {
                "description": "Modify internal system settings",
                "permissions": ["write_device_state", "modify_system_config"],
                "expires_in_hours": 12
            },
            "confidential_read": {
                "description": "Read confidential user data",
                "permissions": ["read_user_data", "read_personal_info"],
                "expires_in_hours": 6
            },
            "confidential_write": {
                "description": "Modify confidential user data",
                "permissions": ["write_user_data", "modify_personal_info"],
                "expires_in_hours": 3
            },
            "restricted_access": {
                "description": "Access to restricted system functions",
                "permissions": ["admin_access", "system_control"],
                "expires_in_hours": 1
            }
        }
        
        # Trust tier requirements for different operations
        self._operation_requirements = {
            "device_control": {
                "min_trust_tier": TrustTier.VERIFIED,
                "required_scopes": ["device_control"],
                "approval_required": False
            },
            "data_collection": {
                "min_trust_tier": TrustTier.BASIC,
                "required_scopes": ["data_read"],
                "approval_required": False
            },
            "ml_inference": {
                "min_trust_tier": TrustTier.VERIFIED,
                "required_scopes": ["ml_access"],
                "approval_required": False
            },
            "system_config": {
                "min_trust_tier": TrustTier.TRUSTED,
                "required_scopes": ["system_config"],
                "approval_required": True
            }
        }
    
    async def evaluate(self, task_spec: TaskSpec) -> PolicyCheckResult:
        """
        Evaluate required scopes and trust tier for a task.
        
        Args:
            task_spec: Task specification to evaluate
            
        Returns:
            PolicyCheckResult with approval status and consent references
        """
        logger.debug(f"Evaluating policy for task {task_spec.task_id}")
        
        # Check privacy class and trust tier compatibility
        privacy_check = self._check_privacy_trust_compatibility(task_spec)
        if not privacy_check.approved:
            return privacy_check
        
        # Check operation-specific requirements
        operation_check = self._check_operation_requirements(task_spec)
        if not operation_check.approved:
            return operation_check
        
        # Generate consent references
        consent_refs = await self._generate_consent_references(task_spec)
        
        # Check if approval is required
        approval_required = self._determine_approval_requirement(task_spec)
        
        # Check for redaction requirements
        redacted_fields = self._determine_redaction_fields(task_spec)
        
        # Determine routing target if needed
        routing_target = self._determine_routing_target(task_spec)
        
        return PolicyCheckResult(
            approved=True,
            reason="Policy check passed",
            requires_approval=approval_required,
            consent_refs=consent_refs,
            redacted_fields=redacted_fields,
            routing_target=routing_target
        )
    
    def _check_privacy_trust_compatibility(self, task_spec: TaskSpec) -> PolicyCheckResult:
        """Check if privacy class and trust tier are compatible."""
        privacy_class = task_spec.privacy_class
        trust_tier = task_spec.trust_tier
        
        if privacy_class not in self._policy_rules:
            return PolicyCheckResult(
                approved=False,
                reason=f"Unknown privacy class: {privacy_class}"
            )
        
        if trust_tier not in self._policy_rules[privacy_class]:
            return PolicyCheckResult(
                approved=False,
                reason=f"Trust tier {trust_tier} not allowed for privacy class {privacy_class}"
            )
        
        policy_rule = self._policy_rules[privacy_class][trust_tier]
        
        return PolicyCheckResult(
            approved=True,
            requires_approval=policy_rule["approval_required"],
            reason="Privacy and trust tier compatible"
        )
    
    def _check_operation_requirements(self, task_spec: TaskSpec) -> PolicyCheckResult:
        """Check operation-specific requirements."""
        # Extract operation type from goals and constraints
        operation_type = self._extract_operation_type(task_spec)
        
        if operation_type not in self._operation_requirements:
            # Default to basic requirements
            return PolicyCheckResult(
                approved=True,
                reason="No specific operation requirements"
            )
        
        requirements = self._operation_requirements[operation_type]
        min_trust_tier = requirements["min_trust_tier"]
        
        # Check trust tier requirement
        if self._compare_trust_tiers(task_spec.trust_tier, min_trust_tier) < 0:
            return PolicyCheckResult(
                approved=False,
                reason=f"Operation {operation_type} requires minimum trust tier {min_trust_tier}, got {task_spec.trust_tier}"
            )
        
        return PolicyCheckResult(
            approved=True,
            requires_approval=requirements["approval_required"],
            reason=f"Operation {operation_type} requirements met"
        )
    
    async def _generate_consent_references(self, task_spec: TaskSpec) -> List[ConsentReference]:
        """Generate consent references for the task."""
        consent_refs = []
        
        # Get required scopes from policy rules
        policy_rule = self._policy_rules[task_spec.privacy_class][task_spec.trust_tier]
        required_scopes = policy_rule["scope_required"]
        
        # Add operation-specific scopes
        operation_type = self._extract_operation_type(task_spec)
        if operation_type in self._operation_requirements:
            operation_scopes = self._operation_requirements[operation_type]["required_scopes"]
            required_scopes.extend(operation_scopes)
        
        # Generate consent reference for each scope
        for scope in required_scopes:
            if scope in self._scope_definitions:
                scope_def = self._scope_definitions[scope]
                expires_at = datetime.utcnow() + timedelta(hours=scope_def["expires_in_hours"])
                
                consent_ref = ConsentReference(
                    consent_token=f"consent_{task_spec.task_id}_{scope}",
                    scopes=[scope],
                    trust_tier=task_spec.trust_tier,
                    expires_at=expires_at,
                    dynamic_consent=True
                )
                consent_refs.append(consent_ref)
        
        return consent_refs
    
    def _determine_approval_requirement(self, task_spec: TaskSpec) -> bool:
        """Determine if approval is required for the task."""
        # Check privacy class and trust tier policy
        policy_rule = self._policy_rules[task_spec.privacy_class][task_spec.trust_tier]
        if policy_rule["approval_required"]:
            return True
        
        # Check operation-specific requirements
        operation_type = self._extract_operation_type(task_spec)
        if operation_type in self._operation_requirements:
            return self._operation_requirements[operation_type]["approval_required"]
        
        # Check for high-risk operations
        if self._is_high_risk_operation(task_spec):
            return True
        
        return False
    
    def _determine_redaction_fields(self, task_spec: TaskSpec) -> List[str]:
        """Determine which fields should be redacted."""
        redacted_fields = []
        
        # Redact sensitive information based on privacy class
        if task_spec.privacy_class in [PrivacyClass.CONFIDENTIAL, PrivacyClass.RESTRICTED]:
            redacted_fields.extend([
                "user_id",
                "personal_data",
                "location_data",
                "biometric_data"
            ])
        
        # Redact based on trust tier
        if task_spec.trust_tier in [TrustTier.UNTRUSTED, TrustTier.BASIC]:
            redacted_fields.extend([
                "system_config",
                "internal_metrics",
                "debug_info"
            ])
        
        return redacted_fields
    
    def _determine_routing_target(self, task_spec: TaskSpec) -> Optional[str]:
        """Determine if task should be routed to a specific target."""
        # Route high-privacy tasks to local processing
        if task_spec.privacy_class in [PrivacyClass.CONFIDENTIAL, PrivacyClass.RESTRICTED]:
            return "local_processing"
        
        # Route low-trust tasks to sandboxed environment
        if task_spec.trust_tier in [TrustTier.UNTRUSTED, TrustTier.BASIC]:
            return "sandboxed_environment"
        
        # Route ML tasks to ML orchestrator
        if self._is_ml_operation(task_spec):
            return "ml_orchestrator"
        
        return None
    
    def _extract_operation_type(self, task_spec: TaskSpec) -> str:
        """Extract operation type from task specification."""
        # Analyze goals to determine operation type
        goal_targets = [goal.target for goal in task_spec.goals]
        
        if "energy" in goal_targets:
            return "energy_optimization"
        elif "security" in goal_targets:
            return "security_monitoring"
        elif "comfort" in goal_targets:
            return "comfort_control"
        elif "data_quality" in goal_targets:
            return "data_collection"
        elif "efficiency" in goal_targets:
            return "automation"
        else:
            return "general"
    
    def _is_high_risk_operation(self, task_spec: TaskSpec) -> bool:
        """Check if the operation is high-risk."""
        # Check for system-level operations
        if any("system" in goal.target for goal in task_spec.goals):
            return True
        
        # Check for financial operations
        if any("cost" in goal.target for goal in task_spec.goals):
            return True
        
        # Check for security operations
        if any("security" in goal.target for goal in task_spec.goals):
            return True
        
        return False
    
    def _is_ml_operation(self, task_spec: TaskSpec) -> bool:
        """Check if the operation involves ML."""
        # Check for ML-related goals
        ml_keywords = ["prediction", "inference", "learning", "model", "ai", "ml"]
        for goal in task_spec.goals:
            if any(keyword in goal.target.lower() for keyword in ml_keywords):
                return True
        
        return False
    
    def _compare_trust_tiers(self, tier1: TrustTier, tier2: TrustTier) -> int:
        """Compare two trust tiers. Returns -1 if tier1 < tier2, 0 if equal, 1 if tier1 > tier2."""
        tier_order = [
            TrustTier.UNTRUSTED,
            TrustTier.BASIC,
            TrustTier.VERIFIED,
            TrustTier.TRUSTED,
            TrustTier.PRIVILEGED
        ]
        
        index1 = tier_order.index(tier1)
        index2 = tier_order.index(tier2)
        
        if index1 < index2:
            return -1
        elif index1 > index2:
            return 1
        else:
            return 0
    
    async def validate_consent(self, consent_token: str, required_scopes: List[str]) -> bool:
        """Validate if a consent token covers the required scopes."""
        # TODO: Implement actual consent validation
        # This would typically check against a consent database
        logger.debug(f"Validating consent token {consent_token} for scopes {required_scopes}")
        return True
    
    async def revoke_consent(self, consent_token: str) -> bool:
        """Revoke a consent token."""
        # TODO: Implement actual consent revocation
        logger.debug(f"Revoking consent token {consent_token}")
        return True
    
    def get_policy_summary(self, task_spec: TaskSpec) -> Dict[str, Any]:
        """Get a summary of the policy requirements for a task."""
        policy_rule = self._policy_rules[task_spec.privacy_class][task_spec.trust_tier]
        operation_type = self._extract_operation_type(task_spec)
        
        summary = {
            "privacy_class": task_spec.privacy_class.value,
            "trust_tier": task_spec.trust_tier.value,
            "operation_type": operation_type,
            "approval_required": policy_rule["approval_required"],
            "required_scopes": policy_rule["scope_required"],
            "redacted_fields": self._determine_redaction_fields(task_spec),
            "routing_target": self._determine_routing_target(task_spec)
        }
        
        if operation_type in self._operation_requirements:
            operation_req = self._operation_requirements[operation_type]
            summary["operation_requirements"] = {
                "min_trust_tier": operation_req["min_trust_tier"].value,
                "operation_scopes": operation_req["required_scopes"],
                "operation_approval_required": operation_req["approval_required"]
            }
        
        return summary
