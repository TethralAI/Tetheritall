"""
Experience Goals for Orchestration System

This module defines the core experience goals and metrics that the orchestration
system should maximize to deliver the best user experience.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
import time


class ExperienceGoal(Enum):
    """Core experience goals for the orchestration system."""
    LOW_FRICTION = "low_friction"
    FAST_RESPONSE = "fast_response"
    TRUSTWORTHY = "trustworthy"
    PROACTIVE_CORRECT = "proactive_correct"


class FrictionType(Enum):
    """Types of friction that should be minimized."""
    APPROVAL_TAPS = "approval_taps"
    CONFIRMATION_DIALOGS = "confirmation_dialogs"
    SETUP_STEPS = "setup_steps"
    ERROR_RECOVERY = "error_recovery"
    MANUAL_INTERVENTION = "manual_intervention"


class ResponseTimeTarget(Enum):
    """Target response times for different operations."""
    LOCAL_REACTION = 150  # ms - for common tasks
    PLAN_PREVIEW = 800  # ms - for plan previews
    CONTEXT_QUERY = 50  # ms - for context snapshots
    PLACEMENT_DECISION = 100  # ms - per step
    EXECUTION_START = 200  # ms - for execution initiation


class TrustworthinessMetric(Enum):
    """Metrics for measuring trustworthiness."""
    EXPLANATION_QUALITY = "explanation_quality"
    CONSENT_COMPLIANCE = "consent_compliance"
    SAFE_DEFAULTS = "safe_defaults"
    PRIVACY_RESPECT = "privacy_respect"
    AUDIT_TRAIL = "audit_trail"


class ProactivityMetric(Enum):
    """Metrics for measuring proactive behavior."""
    FALSE_SUGGESTIONS = "false_suggestions"
    SUGGESTION_ACCURACY = "suggestion_accuracy"
    CONTEXT_AWARENESS = "context_awareness"
    TIMING_APPROPRIATENESS = "timing_appropriateness"


@dataclass
class ExperienceMetrics:
    """Comprehensive metrics for measuring experience goals."""
    
    # Low Friction Metrics
    approval_taps_per_week: int = 0
    confirmation_dialogs_per_week: int = 0
    setup_steps_remaining: int = 0
    error_recovery_actions: int = 0
    manual_interventions: int = 0
    
    # Fast Response Metrics
    local_reaction_time_ms: float = 0.0
    plan_preview_time_ms: float = 0.0
    context_query_time_ms: float = 0.0
    placement_decision_time_ms: float = 0.0
    execution_start_time_ms: float = 0.0
    
    # Trustworthiness Metrics
    explanation_quality_score: float = 0.0  # 0-1
    consent_compliance_rate: float = 0.0  # 0-1
    safe_defaults_usage: float = 0.0  # 0-1
    privacy_respect_score: float = 0.0  # 0-1
    audit_trail_completeness: float = 0.0  # 0-1
    
    # Proactive Correctness Metrics
    false_suggestions_per_week: int = 0
    suggestion_accuracy_rate: float = 0.0  # 0-1
    context_awareness_score: float = 0.0  # 0-1
    timing_appropriateness: float = 0.0  # 0-1
    
    # Overall Experience Score
    overall_experience_score: float = 0.0  # 0-1
    
    # Timestamps
    last_updated: datetime = field(default_factory=datetime.utcnow)
    measurement_period_start: datetime = field(default_factory=datetime.utcnow)
    
    def calculate_overall_score(self) -> float:
        """Calculate overall experience score based on all metrics."""
        # Weight the different aspects
        friction_score = self._calculate_friction_score()
        speed_score = self._calculate_speed_score()
        trust_score = self._calculate_trust_score()
        proactivity_score = self._calculate_proactivity_score()
        
        # Combine scores (equal weighting for now)
        self.overall_experience_score = (
            friction_score * 0.25 +
            speed_score * 0.25 +
            trust_score * 0.25 +
            proactivity_score * 0.25
        )
        
        return self.overall_experience_score
    
    def _calculate_friction_score(self) -> float:
        """Calculate friction score (lower friction = higher score)."""
        # Target: 1-2 taps for approval, near-zero nags
        target_taps_per_week = 2
        target_dialogs_per_week = 1
        
        taps_score = max(0, 1 - (self.approval_taps_per_week / target_taps_per_week))
        dialogs_score = max(0, 1 - (self.confirmation_dialogs_per_week / target_dialogs_per_week))
        
        return (taps_score + dialogs_score) / 2
    
    def _calculate_speed_score(self) -> float:
        """Calculate speed score based on response time targets."""
        scores = []
        
        # Local reaction time (target: <150ms)
        if self.local_reaction_time_ms <= ResponseTimeTarget.LOCAL_REACTION.value:
            scores.append(1.0)
        else:
            scores.append(max(0, 1 - (self.local_reaction_time_ms - ResponseTimeTarget.LOCAL_REACTION.value) / 1000))
        
        # Plan preview time (target: <800ms)
        if self.plan_preview_time_ms <= ResponseTimeTarget.PLAN_PREVIEW.value:
            scores.append(1.0)
        else:
            scores.append(max(0, 1 - (self.plan_preview_time_ms - ResponseTimeTarget.PLAN_PREVIEW.value) / 2000))
        
        # Context query time (target: <50ms)
        if self.context_query_time_ms <= ResponseTimeTarget.CONTEXT_QUERY.value:
            scores.append(1.0)
        else:
            scores.append(max(0, 1 - (self.context_query_time_ms - ResponseTimeTarget.CONTEXT_QUERY.value) / 100))
        
        return sum(scores) / len(scores)
    
    def _calculate_trust_score(self) -> float:
        """Calculate trustworthiness score."""
        return (
            self.explanation_quality_score +
            self.consent_compliance_rate +
            self.safe_defaults_usage +
            self.privacy_respect_score +
            self.audit_trail_completeness
        ) / 5
    
    def _calculate_proactivity_score(self) -> float:
        """Calculate proactive correctness score."""
        # Target: fewer than 1 false proactive suggestion per week
        false_suggestion_penalty = min(1.0, self.false_suggestions_per_week)
        
        base_score = (
            self.suggestion_accuracy_rate +
            self.context_awareness_score +
            self.timing_appropriateness
        ) / 3
        
        return max(0, base_score - false_suggestion_penalty)


@dataclass
class ExperienceTargets:
    """Target values for experience goals."""
    
    # Low Friction Targets
    max_approval_taps_per_week: int = 2
    max_confirmation_dialogs_per_week: int = 1
    max_setup_steps: int = 3
    max_error_recovery_actions: int = 1
    max_manual_interventions: int = 0
    
    # Fast Response Targets
    max_local_reaction_time_ms: int = 150
    max_plan_preview_time_ms: int = 800
    max_context_query_time_ms: int = 50
    max_placement_decision_time_ms: int = 100
    max_execution_start_time_ms: int = 200
    
    # Trustworthiness Targets
    min_explanation_quality: float = 0.8
    min_consent_compliance: float = 0.95
    min_safe_defaults_usage: float = 0.9
    min_privacy_respect: float = 0.9
    min_audit_trail_completeness: float = 0.95
    
    # Proactive Correctness Targets
    max_false_suggestions_per_week: int = 1
    min_suggestion_accuracy: float = 0.9
    min_context_awareness: float = 0.8
    min_timing_appropriateness: float = 0.8
    
    # Overall Experience Target
    min_overall_experience_score: float = 0.85


@dataclass
class ExperienceOptimizer:
    """Optimizer for improving user experience."""
    
    current_metrics: ExperienceMetrics
    targets: ExperienceTargets
    optimization_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def analyze_experience_gaps(self) -> Dict[str, float]:
        """Analyze gaps between current metrics and targets."""
        gaps = {}
        
        # Friction gaps
        gaps["approval_taps"] = max(0, self.current_metrics.approval_taps_per_week - self.targets.max_approval_taps_per_week)
        gaps["confirmation_dialogs"] = max(0, self.current_metrics.confirmation_dialogs_per_week - self.targets.max_confirmation_dialogs_per_week)
        
        # Speed gaps
        gaps["local_reaction"] = max(0, self.current_metrics.local_reaction_time_ms - self.targets.max_local_reaction_time_ms)
        gaps["plan_preview"] = max(0, self.current_metrics.plan_preview_time_ms - self.targets.max_plan_preview_time_ms)
        gaps["context_query"] = max(0, self.current_metrics.context_query_time_ms - self.targets.max_context_query_time_ms)
        
        # Trust gaps
        gaps["explanation_quality"] = max(0, self.targets.min_explanation_quality - self.current_metrics.explanation_quality_score)
        gaps["consent_compliance"] = max(0, self.targets.min_consent_compliance - self.current_metrics.consent_compliance_rate)
        
        # Proactivity gaps
        gaps["false_suggestions"] = max(0, self.current_metrics.false_suggestions_per_week - self.targets.max_false_suggestions_per_week)
        gaps["suggestion_accuracy"] = max(0, self.targets.min_suggestion_accuracy - self.current_metrics.suggestion_accuracy_rate)
        
        return gaps
    
    def generate_optimization_recommendations(self) -> List[str]:
        """Generate recommendations for improving experience."""
        gaps = self.analyze_experience_gaps()
        recommendations = []
        
        if gaps["approval_taps"] > 0:
            recommendations.append("Reduce approval requirements by improving consent pre-approval")
        
        if gaps["local_reaction"] > 0:
            recommendations.append("Optimize local execution paths and reduce network calls")
        
        if gaps["plan_preview"] > 0:
            recommendations.append("Cache common plan templates and optimize planning algorithms")
        
        if gaps["explanation_quality"] > 0:
            recommendations.append("Enhance explanation generation with more context and examples")
        
        if gaps["false_suggestions"] > 0:
            recommendations.append("Improve context awareness and suggestion filtering")
        
        return recommendations
    
    def should_trigger_optimization(self) -> bool:
        """Determine if optimization should be triggered."""
        current_score = self.current_metrics.calculate_overall_score()
        return current_score < self.targets.min_overall_experience_score
    
    def _calculate_friction_score(self) -> float:
        """Calculate friction score based on approval requirements."""
        # Normalize approval taps and confirmation dialogs
        approval_score = max(0, 1 - (self.current_metrics.approval_taps_per_week / self.targets.max_approval_taps_per_week))
        confirmation_score = max(0, 1 - (self.current_metrics.confirmation_dialogs_per_week / self.targets.max_confirmation_dialogs_per_week))
        
        return (approval_score + confirmation_score) / 2
    
    def _calculate_speed_score(self) -> float:
        """Calculate speed score based on response times."""
        # Normalize response times against targets
        local_score = max(0, 1 - (self.current_metrics.local_reaction_time_ms / self.targets.max_local_reaction_time_ms))
        plan_score = max(0, 1 - (self.current_metrics.plan_preview_time_ms / self.targets.max_plan_preview_time_ms))
        
        return (local_score + plan_score) / 2
    
    def _calculate_trust_score(self) -> float:
        """Calculate trustworthiness score."""
        return (
            self.current_metrics.explanation_quality_score +
            self.current_metrics.consent_compliance_rate +
            self.current_metrics.safe_defaults_usage +
            self.current_metrics.privacy_respect_score +
            self.current_metrics.audit_trail_completeness
        ) / 5


@dataclass
class ExperienceMonitor:
    """Monitor for tracking experience metrics in real-time."""
    
    metrics: ExperienceMetrics
    targets: ExperienceTargets
    optimizer: ExperienceOptimizer
    
    def __init__(self):
        self.metrics = ExperienceMetrics()
        self.targets = ExperienceTargets()
        self.optimizer = ExperienceOptimizer(self.metrics, self.targets)
        self.measurement_start = datetime.utcnow()
    
    def record_approval_tap(self):
        """Record an approval tap event."""
        self.metrics.approval_taps_per_week += 1
    
    def record_confirmation_dialog(self):
        """Record a confirmation dialog event."""
        self.metrics.confirmation_dialogs_per_week += 1
    
    def record_response_time(self, operation: str, time_ms: float):
        """Record response time for an operation."""
        if operation == "local_reaction":
            self.metrics.local_reaction_time_ms = time_ms
        elif operation == "plan_preview":
            self.metrics.plan_preview_time_ms = time_ms
        elif operation == "context_query":
            self.metrics.context_query_time_ms = time_ms
        elif operation == "placement_decision":
            self.metrics.placement_decision_time_ms = time_ms
        elif operation == "execution_start":
            self.metrics.execution_start_time_ms = time_ms
    
    def record_false_suggestion(self):
        """Record a false proactive suggestion."""
        self.metrics.false_suggestions_per_week += 1
    
    def update_trust_metrics(self, **kwargs):
        """Update trustworthiness metrics."""
        for key, value in kwargs.items():
            if hasattr(self.metrics, key):
                setattr(self.metrics, key, value)
    
    def get_experience_report(self) -> Dict[str, Any]:
        """Get a comprehensive experience report."""
        self.metrics.calculate_overall_score()
        
        return {
            "overall_score": self.metrics.overall_experience_score,
            "friction_score": self.optimizer._calculate_friction_score(),
            "speed_score": self.optimizer._calculate_speed_score(),
            "trust_score": self.optimizer._calculate_trust_score(),
            "proactivity_score": self.optimizer._calculate_proactivity_score(),
            "gaps": self.optimizer.analyze_experience_gaps(),
            "recommendations": self.optimizer.generate_optimization_recommendations(),
            "needs_optimization": self.optimizer.should_trigger_optimization(),
            "measurement_period": {
                "start": self.measurement_start.isoformat(),
                "current": datetime.utcnow().isoformat()
            }
        }
    
    def reset_weekly_metrics(self):
        """Reset weekly metrics (should be called weekly)."""
        self.metrics.approval_taps_per_week = 0
        self.metrics.confirmation_dialogs_per_week = 0
        self.metrics.false_suggestions_per_week = 0
        self.measurement_start = datetime.utcnow()


# Global experience monitor instance
experience_monitor = ExperienceMonitor()


def get_experience_monitor() -> ExperienceMonitor:
    """Get the global experience monitor instance."""
    return experience_monitor


def record_experience_event(event_type: str, **kwargs):
    """Record an experience event for monitoring."""
    monitor = get_experience_monitor()
    
    if event_type == "approval_tap":
        monitor.record_approval_tap()
    elif event_type == "confirmation_dialog":
        monitor.record_confirmation_dialog()
    elif event_type == "response_time":
        operation = kwargs.get("operation")
        time_ms = kwargs.get("time_ms")
        if operation and time_ms:
            monitor.record_response_time(operation, time_ms)
    elif event_type == "false_suggestion":
        monitor.record_false_suggestion()
    elif event_type == "trust_metrics":
        monitor.update_trust_metrics(**kwargs)
