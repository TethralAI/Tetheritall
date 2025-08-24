"""
Combination Evaluator
Evaluates combinations for feasibility and value with comprehensive scoring.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
import time

from .models import (
    CombinationCandidate, ContextSnapshot, UserOverlay, CapabilityType,
    PrivacyLevel, SafetyLevel, EffortLevel, OutcomeTemplate
)

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Result of combination evaluation."""
    combinations: List[CombinationCandidate] = field(default_factory=list)
    missing_capabilities: List[str] = field(default_factory=list)
    evaluation_time_ms: int = 0
    total_evaluated: int = 0
    feasible_count: int = 0


class CombinationEvaluator:
    """
    Evaluates combinations for feasibility and value.
    
    Implements B3 from the spec:
    - Feasibility checks (safety, contextual, reachability, service availability)
    - Value scoring (context fit, utility, preference fit, novelty, effort, risk)
    - Outcome template matching
    """
    
    def __init__(self):
        self._outcome_templates = self._initialize_outcome_templates()
        self._safety_rules = self._initialize_safety_rules()
        self._context_rules = self._initialize_context_rules()
        
    async def evaluate_combinations(
        self,
        combinations: List[CombinationCandidate],
        context_snapshot: ContextSnapshot,
        user_id: str,
        user_overlay: Optional[UserOverlay] = None
    ) -> EvaluationResult:
        """
        Evaluate combinations for feasibility and value.
        
        Args:
            combinations: List of combination candidates to evaluate
            context_snapshot: Current context snapshot
            user_id: User identifier
            user_overlay: User preferences and learning data
            
        Returns:
            EvaluationResult with scored and ranked combinations
        """
        start_time = time.time()
        evaluated_combinations = []
        missing_capabilities = set()
        
        logger.info(f"Evaluating {len(combinations)} combinations")
        
        for combination in combinations:
            try:
                # Step 1: Feasibility evaluation
                feasibility_result = await self._evaluate_feasibility(
                    combination, context_snapshot
                )
                
                if not feasibility_result["feasible"]:
                    # Track missing capabilities for what-if analysis
                    missing_capabilities.update(feasibility_result["missing_capabilities"])
                    continue
                
                # Step 2: Value evaluation
                value_result = await self._evaluate_value(
                    combination, context_snapshot, user_overlay
                )
                
                # Step 3: Outcome matching
                outcome_matches = await self._match_outcomes(combination)
                
                # Step 4: Update combination with evaluation results
                combination.feasibility_score = feasibility_result["score"]
                combination.estimated_value = value_result["total_value"]
                combination.context_fit = value_result["context_fit"]
                combination.novelty_score = value_result["novelty_score"]
                combination.effort_required = value_result["effort_required"]
                combination.privacy_level = value_result["privacy_level"]
                combination.safety_level = value_result["safety_level"]
                combination.missing_prerequisites = feasibility_result["missing_capabilities"]
                
                # Step 5: Apply user overlay adjustments
                if user_overlay:
                    await self._apply_user_overlay(combination, user_overlay, context_snapshot)
                
                evaluated_combinations.append(combination)
                
            except Exception as e:
                logger.error(f"Error evaluating combination {combination.combination_id}: {e}")
                continue
        
        # Sort by final value score
        evaluated_combinations.sort(key=lambda c: c.estimated_value, reverse=True)
        
        evaluation_time = int((time.time() - start_time) * 1000)
        
        return EvaluationResult(
            combinations=evaluated_combinations,
            missing_capabilities=list(missing_capabilities),
            evaluation_time_ms=evaluation_time,
            total_evaluated=len(combinations),
            feasible_count=len(evaluated_combinations)
        )
    
    async def _evaluate_feasibility(
        self,
        combination: CombinationCandidate,
        context_snapshot: ContextSnapshot
    ) -> Dict[str, Any]:
        """Evaluate feasibility of a combination."""
        feasibility_score = 1.0
        missing_capabilities = []
        issues = []
        
        # Check safety constraints
        safety_result = self._check_safety_constraints(combination)
        if not safety_result["safe"]:
            feasibility_score *= 0.0
            issues.append(f"Safety violation: {safety_result['reason']}")
        
        # Check contextual constraints
        context_result = self._check_contextual_constraints(combination, context_snapshot)
        if not context_result["valid"]:
            feasibility_score *= 0.5
            issues.append(f"Context violation: {context_result['reason']}")
        
        # Check device reachability
        reachability_result = self._check_device_reachability(combination)
        if not reachability_result["all_reachable"]:
            feasibility_score *= 0.8
            missing_capabilities.extend(reachability_result["unreachable_devices"])
            issues.append("Some devices are unreachable")
        
        # Check service availability
        service_result = self._check_service_availability(combination)
        if not service_result["all_available"]:
            feasibility_score *= 0.9
            missing_capabilities.extend(service_result["unavailable_services"])
            issues.append("Some services are unavailable")
        
        # Check room consistency
        room_result = self._check_room_consistency(combination)
        if not room_result["consistent"]:
            feasibility_score *= 0.7
            issues.append("Room configuration issues")
        
        return {
            "feasible": feasibility_score > 0.0,
            "score": feasibility_score,
            "missing_capabilities": missing_capabilities,
            "issues": issues
        }
    
    async def _evaluate_value(
        self,
        combination: CombinationCandidate,
        context_snapshot: ContextSnapshot,
        user_overlay: Optional[UserOverlay]
    ) -> Dict[str, Any]:
        """Evaluate value of a combination."""
        total_value = 0.0
        
        # Context fit scoring
        context_fit = self._calculate_context_fit(combination, context_snapshot)
        total_value += context_fit * 0.3
        
        # Utility scoring
        utility_score = self._calculate_utility_score(combination)
        total_value += utility_score * 0.25
        
        # Preference fit scoring
        preference_fit = self._calculate_preference_fit(combination, user_overlay, context_snapshot)
        total_value += preference_fit * 0.2
        
        # Novelty scoring
        novelty_score = self._calculate_novelty_score(combination)
        total_value += novelty_score * 0.15
        
        # Effort assessment
        effort_required = self._assess_effort_required(combination)
        
        # Risk assessment
        risk_deduction = self._assess_risk_deduction(combination)
        total_value -= risk_deduction
        
        # Privacy and safety assessment
        privacy_level = self._assess_privacy_level(combination)
        safety_level = self._assess_safety_level(combination)
        
        return {
            "total_value": max(0.0, total_value),
            "context_fit": context_fit,
            "utility_score": utility_score,
            "preference_fit": preference_fit,
            "novelty_score": novelty_score,
            "effort_required": effort_required,
            "risk_deduction": risk_deduction,
            "privacy_level": privacy_level,
            "safety_level": safety_level
        }
    
    def _check_safety_constraints(self, combination: CombinationCandidate) -> Dict[str, Any]:
        """Check safety constraints for a combination."""
        for rule in self._safety_rules:
            if self._violates_safety_rule(combination, rule):
                return {
                    "safe": False,
                    "reason": rule["description"]
                }
        
        return {"safe": True, "reason": None}
    
    def _check_contextual_constraints(
        self,
        combination: CombinationCandidate,
        context_snapshot: ContextSnapshot
    ) -> Dict[str, Any]:
        """Check contextual constraints for a combination."""
        for rule in self._context_rules:
            if self._violates_context_rule(combination, context_snapshot, rule):
                return {
                    "valid": False,
                    "reason": rule["description"]
                }
        
        return {"valid": True, "reason": None}
    
    def _check_device_reachability(self, combination: CombinationCandidate) -> Dict[str, Any]:
        """Check if all devices in combination are reachable."""
        unreachable_devices = []
        
        for device in combination.devices:
            if not device.reachable:
                unreachable_devices.append(device.device_id)
        
        return {
            "all_reachable": len(unreachable_devices) == 0,
            "unreachable_devices": unreachable_devices
        }
    
    def _check_service_availability(self, combination: CombinationCandidate) -> Dict[str, Any]:
        """Check if all services in combination are available."""
        unavailable_services = []
        
        for service in combination.services:
            if not service.available:
                unavailable_services.append(service.service_id)
        
        return {
            "all_available": len(unavailable_services) == 0,
            "unavailable_services": unavailable_services
        }
    
    def _check_room_consistency(self, combination: CombinationCandidate) -> Dict[str, Any]:
        """Check room consistency for devices in combination."""
        room_devices = {}
        
        for device in combination.devices:
            if device.room:
                if device.room not in room_devices:
                    room_devices[device.room] = []
                room_devices[device.room].append(device.capability_type)
        
        # Check for conflicts in same room
        for room, capabilities in room_devices.items():
            if len(set(capabilities)) != len(capabilities):
                return {"consistent": False, "conflict_room": room}
        
        return {"consistent": True}
    
    def _calculate_context_fit(
        self,
        combination: CombinationCandidate,
        context_snapshot: ContextSnapshot
    ) -> float:
        """Calculate how well combination fits current context."""
        fit_score = 0.0
        
        # Time of day fit
        if context_snapshot.is_quiet_hours:
            # Prefer quiet combinations during quiet hours
            if not any(d.capability_type == CapabilityType.AUDIO for d in combination.devices):
                fit_score += 0.3
            else:
                fit_score -= 0.2
        
        # Weekend vs weekday fit
        if context_snapshot.is_weekend:
            # Prefer comfort and entertainment on weekends
            if any(d.capability_type == CapabilityType.LIGHTING for d in combination.devices):
                fit_score += 0.2
            if any(d.capability_type == CapabilityType.AUDIO for d in combination.devices):
                fit_score += 0.1
        
        # Weather fit
        if context_snapshot.weather_conditions:
            weather = context_snapshot.weather_conditions.get("condition", "")
            if weather in ["rain", "snow", "cloudy"]:
                # Prefer lighting during bad weather
                if any(d.capability_type == CapabilityType.LIGHTING for d in combination.devices):
                    fit_score += 0.2
        
        # Calendar state fit
        if context_snapshot.calendar_state == "meeting":
            # Prefer quiet, non-disruptive combinations during meetings
            if not any(d.capability_type == CapabilityType.AUDIO for d in combination.devices):
                fit_score += 0.2
        
        return min(1.0, max(0.0, fit_score))
    
    def _calculate_utility_score(self, combination: CombinationCandidate) -> float:
        """Calculate utility score based on capability types."""
        utility_score = 0.0
        
        # Base utility from capability types
        capability_utilities = {
            CapabilityType.LIGHTING: 0.3,
            CapabilityType.SENSING: 0.4,
            CapabilityType.ACTUATION: 0.2,
            CapabilityType.AUDIO: 0.2,
            CapabilityType.VIDEO: 0.5,
            CapabilityType.SECURITY: 0.6,
            CapabilityType.CLIMATE: 0.4,
            CapabilityType.ENERGY: 0.3,
            CapabilityType.ACCESS_CONTROL: 0.5,
            CapabilityType.WEATHER: 0.2,
            CapabilityType.CALENDAR: 0.3,
            CapabilityType.PRESENCE: 0.4
        }
        
        for device in combination.devices:
            utility_score += capability_utilities.get(device.capability_type, 0.1)
        
        for service in combination.services:
            utility_score += capability_utilities.get(service.capability_type, 0.1)
        
        # Bonus for safety-related combinations
        if any(d.capability_type in [CapabilityType.SECURITY, CapabilityType.ACCESS_CONTROL] 
               for d in combination.devices):
            utility_score += 0.2
        
        # Bonus for energy-saving combinations
        if any(d.capability_type == CapabilityType.ENERGY for d in combination.devices):
            utility_score += 0.1
        
        return min(1.0, utility_score)
    
    def _calculate_preference_fit(
        self,
        combination: CombinationCandidate,
        user_overlay: Optional[UserOverlay],
        context_snapshot: ContextSnapshot
    ) -> float:
        """Calculate preference fit based on user overlay."""
        if not user_overlay:
            return 0.5  # Neutral score if no user data
        
        preference_score = 0.5  # Base neutral score
        
        # Device affinities
        for device in combination.devices:
            device_affinity = user_overlay.device_affinities.get(device.device_id, 0.5)
            preference_score += (device_affinity - 0.5) * 0.1
        
        # Room affinities
        for device in combination.devices:
            if device.room:
                room_affinity = user_overlay.room_affinities.get(device.room, 0.5)
                preference_score += (room_affinity - 0.5) * 0.05
        
        # Time profile preferences
        time_key = self._get_time_profile_key(context_snapshot)
        if time_key in user_overlay.time_profiles:
            time_profile = user_overlay.time_profiles[time_key]
            # Apply time-specific preferences
            if "preferred_capabilities" in time_profile:
                for device in combination.devices:
                    if device.capability_type.value in time_profile["preferred_capabilities"]:
                        preference_score += 0.1
        
        return min(1.0, max(0.0, preference_score))
    
    def _calculate_novelty_score(self, combination: CombinationCandidate) -> float:
        """Calculate novelty score for the combination."""
        novelty_score = 0.0
        
        # Diversity bonus
        capability_types = set()
        for device in combination.devices:
            capability_types.add(device.capability_type)
        for service in combination.services:
            capability_types.add(service.capability_type)
        
        # More diverse combinations get higher novelty
        novelty_score += len(capability_types) * 0.1
        
        # Device-service combination bonus
        if combination.devices and combination.services:
            novelty_score += 0.2
        
        # Cross-room combination bonus
        rooms = set()
        for device in combination.devices:
            if device.room:
                rooms.add(device.room)
        if len(rooms) > 1:
            novelty_score += 0.1
        
        return min(1.0, novelty_score)
    
    def _assess_effort_required(self, combination: CombinationCandidate) -> EffortLevel:
        """Assess effort required to implement the combination."""
        effort_score = 0
        
        # Count devices and services
        effort_score += len(combination.devices) * 1
        effort_score += len(combination.services) * 1
        
        # Complexity factors
        if len(combination.devices) > 3:
            effort_score += 2
        
        if any(d.capability_type == CapabilityType.SECURITY for d in combination.devices):
            effort_score += 1  # Security requires more setup
        
        if any(d.capability_type == CapabilityType.VIDEO for d in combination.devices):
            effort_score += 1  # Video requires more setup
        
        # Map to effort level
        if effort_score <= 2:
            return EffortLevel.NONE
        elif effort_score <= 4:
            return EffortLevel.LOW
        elif effort_score <= 6:
            return EffortLevel.MEDIUM
        else:
            return EffortLevel.HIGH
    
    def _assess_risk_deduction(self, combination: CombinationCandidate) -> float:
        """Assess risk deduction for the combination."""
        risk_deduction = 0.0
        
        # Privacy concerns
        if any(d.capability_type == CapabilityType.VIDEO for d in combination.devices):
            risk_deduction += 0.1
        
        if any(d.capability_type == CapabilityType.SENSING for d in combination.devices):
            risk_deduction += 0.05
        
        # Security risks
        if any(d.capability_type == CapabilityType.ACCESS_CONTROL for d in combination.devices):
            risk_deduction += 0.05
        
        # Fragile steps (many dependencies)
        if len(combination.devices) + len(combination.services) > 4:
            risk_deduction += 0.1
        
        return min(0.3, risk_deduction)  # Cap at 30% risk deduction
    
    def _assess_privacy_level(self, combination: CombinationCandidate) -> PrivacyLevel:
        """Assess privacy level of the combination."""
        privacy_score = 0
        
        for device in combination.devices:
            if device.capability_type == CapabilityType.VIDEO:
                privacy_score += 3
            elif device.capability_type == CapabilityType.SENSING:
                privacy_score += 2
            elif device.capability_type == CapabilityType.AUDIO:
                privacy_score += 2
            elif device.capability_type == CapabilityType.ACCESS_CONTROL:
                privacy_score += 1
        
        if privacy_score >= 3:
            return PrivacyLevel.SENSITIVE
        elif privacy_score >= 2:
            return PrivacyLevel.PRIVATE
        elif privacy_score >= 1:
            return PrivacyLevel.PERSONAL
        else:
            return PrivacyLevel.PUBLIC
    
    def _assess_safety_level(self, combination: CombinationCandidate) -> SafetyLevel:
        """Assess safety level of the combination."""
        safety_score = 0
        
        for device in combination.devices:
            if device.capability_type == CapabilityType.ACCESS_CONTROL:
                safety_score += 2
            elif device.capability_type == CapabilityType.SECURITY:
                safety_score += 1
            elif device.capability_type == CapabilityType.ACTUATION:
                safety_score += 1
        
        if safety_score >= 3:
            return SafetyLevel.RESTRICTED
        elif safety_score >= 2:
            return SafetyLevel.CAUTION
        elif safety_score >= 1:
            return SafetyLevel.SAFE
        else:
            return SafetyLevel.SAFE
    
    async def _match_outcomes(self, combination: CombinationCandidate) -> List[OutcomeTemplate]:
        """Match combination against outcome templates."""
        matches = []
        
        for template in self._outcome_templates:
            if self._combination_matches_template(combination, template):
                matches.append(template)
        
        return matches
    
    def _combination_matches_template(
        self,
        combination: CombinationCandidate,
        template: OutcomeTemplate
    ) -> bool:
        """Check if combination matches an outcome template."""
        combination_capabilities = set()
        
        for device in combination.devices:
            combination_capabilities.add(device.capability_type)
        
        for service in combination.services:
            combination_capabilities.add(service.capability_type)
        
        # Check if all required capabilities are present
        for required_capability in template.required_capabilities:
            if required_capability not in combination_capabilities:
                return False
        
        return True
    
    async def _apply_user_overlay(
        self,
        combination: CombinationCandidate,
        user_overlay: UserOverlay,
        context_snapshot: ContextSnapshot
    ):
        """Apply user overlay adjustments to combination."""
        # Adjust value based on user preferences
        preference_adjustment = 0.0
        
        # Device affinities
        for device in combination.devices:
            device_affinity = user_overlay.device_affinities.get(device.device_id, 0.5)
            preference_adjustment += (device_affinity - 0.5) * 0.1
        
        # Room affinities
        for device in combination.devices:
            if device.room:
                room_affinity = user_overlay.room_affinities.get(device.room, 0.5)
                preference_adjustment += (room_affinity - 0.5) * 0.05
        
        # Apply adjustment
        combination.estimated_value += preference_adjustment
        combination.estimated_value = max(0.0, combination.estimated_value)
    
    def _get_time_profile_key(self, context_snapshot: ContextSnapshot) -> str:
        """Get time profile key for user overlay lookup."""
        hour = context_snapshot.time_of_day.hour
        
        if context_snapshot.is_quiet_hours:
            return "quiet_hours"
        elif 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 22:
            return "evening"
        else:
            return "night"
    
    def _violates_safety_rule(self, combination: CombinationCandidate, rule: Dict[str, Any]) -> bool:
        """Check if combination violates a safety rule."""
        rule_type = rule["type"]
        
        if rule_type == "no_auto_unlock":
            return any(d.capability_type == CapabilityType.ACCESS_CONTROL for d in combination.devices)
        
        if rule_type == "no_remote_security":
            # This would check if user is away and trying to control security devices
            return False  # Simplified for now
        
        return False
    
    def _violates_context_rule(
        self,
        combination: CombinationCandidate,
        context_snapshot: ContextSnapshot,
        rule: Dict[str, Any]
    ) -> bool:
        """Check if combination violates a context rule."""
        rule_type = rule["type"]
        
        if rule_type == "quiet_hours_audio":
            if context_snapshot.is_quiet_hours:
                return any(d.capability_type == CapabilityType.AUDIO for d in combination.devices)
        
        if rule_type == "meeting_disruption":
            if context_snapshot.calendar_state == "meeting":
                return any(d.capability_type == CapabilityType.AUDIO for d in combination.devices)
        
        return False
    
    def _initialize_outcome_templates(self) -> List[OutcomeTemplate]:
        """Initialize outcome templates."""
        return [
            OutcomeTemplate(
                outcome_id="safe_arrival",
                name="Safe Arrival",
                description="Light up entry area when motion is detected",
                category="safety",
                required_capabilities={CapabilityType.LIGHTING, CapabilityType.SENSING},
                value_factors={"safety": 0.8, "comfort": 0.6}
            ),
            OutcomeTemplate(
                outcome_id="energy_saver",
                name="Energy Saver",
                description="Turn off devices when no motion is detected",
                category="energy",
                required_capabilities={CapabilityType.ACTUATION, CapabilityType.SENSING},
                value_factors={"energy": 0.9, "cost": 0.7}
            ),
            OutcomeTemplate(
                outcome_id="comfort_enhancement",
                name="Comfort Enhancement",
                description="Adjust lighting and climate for optimal comfort",
                category="comfort",
                required_capabilities={CapabilityType.LIGHTING, CapabilityType.CLIMATE},
                value_factors={"comfort": 0.8, "convenience": 0.6}
            ),
            OutcomeTemplate(
                outcome_id="security_monitoring",
                name="Security Monitoring",
                description="Monitor entry points with video and motion sensors",
                category="security",
                required_capabilities={CapabilityType.VIDEO, CapabilityType.SENSING},
                value_factors={"security": 0.9, "peace_of_mind": 0.8}
            )
        ]
    
    def _initialize_safety_rules(self) -> List[Dict[str, Any]]:
        """Initialize safety rules."""
        return [
            {
                "type": "no_auto_unlock",
                "description": "Never automatically unlock doors",
                "enabled": True
            },
            {
                "type": "no_remote_security",
                "description": "No remote security control when user is away",
                "enabled": True
            }
        ]
    
    def _initialize_context_rules(self) -> List[Dict[str, Any]]:
        """Initialize context rules."""
        return [
            {
                "type": "quiet_hours_audio",
                "description": "No disruptive audio during quiet hours",
                "enabled": True
            },
            {
                "type": "meeting_disruption",
                "description": "No disruptive actions during meetings",
                "enabled": True
            }
        ]
