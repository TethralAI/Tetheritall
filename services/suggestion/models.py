"""
Data models for the Tethral Suggestion Engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, time
from enum import Enum
import uuid


class CapabilityType(Enum):
    """Types of device and service capabilities."""
    # Device capabilities
    LIGHTING = "lighting"
    SENSING = "sensing"
    ACTUATION = "actuation"
    AUDIO = "audio"
    VIDEO = "video"
    SECURITY = "security"
    CLIMATE = "climate"
    ENERGY = "energy"
    ACCESS_CONTROL = "access_control"
    NETWORK = "network"
    
    # Service capabilities
    WEATHER = "weather"
    CALENDAR = "calendar"
    PRESENCE = "presence"
    TIME = "time"
    LOCATION = "location"
    TRAFFIC = "traffic"
    NOTIFICATION = "notification"


class PrivacyLevel(Enum):
    """Privacy levels for suggestions and actions."""
    PUBLIC = "public"
    PERSONAL = "personal"
    PRIVATE = "private"
    SENSITIVE = "sensitive"


class SafetyLevel(Enum):
    """Safety levels for suggestions and actions."""
    SAFE = "safe"
    CAUTION = "caution"
    DANGEROUS = "dangerous"
    RESTRICTED = "restricted"


class EffortLevel(Enum):
    """Effort levels for implementing suggestions."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class DeviceCapability:
    """Represents a device capability."""
    capability_type: CapabilityType
    device_id: str
    device_name: str
    device_brand: str
    device_model: str
    room: Optional[str] = None
    zone: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    energy_profile: Optional[Dict[str, Any]] = None
    reachable: bool = True
    last_seen: Optional[datetime] = None


@dataclass
class ServiceCapability:
    """Represents a service capability."""
    capability_type: CapabilityType
    service_name: str
    service_id: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    available: bool = True
    last_updated: Optional[datetime] = None


@dataclass
class SuggestionConfig:
    """Configuration for the suggestion engine."""
    max_combinations: int = 1000
    max_candidates_per_request: int = 10
    time_budget_ms: int = 5000
    enable_llm_fallback: bool = True
    local_learning_default: bool = True
    cloud_sync_optional: bool = True
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "07:00"


@dataclass
class ContextSnapshot:
    """Snapshot of current context for suggestion generation."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    time_of_day: time = field(default_factory=lambda: datetime.now().time())
    is_weekend: bool = field(default_factory=lambda: datetime.now().weekday() >= 5)
    is_quiet_hours: bool = False
    user_present: bool = True
    user_location: Optional[str] = None
    calendar_state: Optional[str] = None  # "busy", "free", "meeting", etc.
    weather_conditions: Optional[Dict[str, Any]] = None
    recent_activity: List[str] = field(default_factory=list)
    session_id: Optional[str] = None


@dataclass
class CombinationCandidate:
    """A candidate combination of devices and services."""
    combination_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    devices: List[DeviceCapability] = field(default_factory=list)
    services: List[ServiceCapability] = field(default_factory=list)
    capability_signature: str = ""  # Normalized signature for deduplication
    estimated_value: float = 0.0
    feasibility_score: float = 0.0
    context_fit: float = 0.0
    novelty_score: float = 0.0
    effort_required: EffortLevel = EffortLevel.NONE
    privacy_level: PrivacyLevel = PrivacyLevel.PERSONAL
    safety_level: SafetyLevel = SafetyLevel.SAFE
    missing_prerequisites: List[str] = field(default_factory=list)


@dataclass
class OutcomeTemplate:
    """Template for a specific outcome that can be achieved."""
    outcome_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    category: str = ""  # "safety", "comfort", "energy", "accessibility"
    required_capabilities: Set[CapabilityType] = field(default_factory=set)
    optional_capabilities: Set[CapabilityType] = field(default_factory=set)
    context_conditions: Dict[str, Any] = field(default_factory=dict)
    value_factors: Dict[str, float] = field(default_factory=dict)
    privacy_impact: PrivacyLevel = PrivacyLevel.PERSONAL
    safety_impact: SafetyLevel = SafetyLevel.SAFE
    effort_estimate: EffortLevel = EffortLevel.LOW


@dataclass
class RecommendationCard:
    """User-facing recommendation card."""
    recommendation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    rationale: List[str] = field(default_factory=list)
    category: str = ""
    confidence: float = 0.0
    privacy_badge: PrivacyLevel = PrivacyLevel.PERSONAL
    safety_badge: SafetyLevel = SafetyLevel.SAFE
    effort_rating: EffortLevel = EffortLevel.LOW
    tunable_controls: Dict[str, Any] = field(default_factory=dict)
    storyboard_preview: List[Dict[str, Any]] = field(default_factory=list)
    combination: Optional[CombinationCandidate] = None
    outcome_template: Optional[OutcomeTemplate] = None


@dataclass
class ExecutionPlan:
    """Plan for executing a recommendation."""
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    recommendation_id: str = ""
    steps: List[Dict[str, Any]] = field(default_factory=list)
    triggers: List[Dict[str, Any]] = field(default_factory=list)
    schedules: List[Dict[str, Any]] = field(default_factory=list)
    fallbacks: List[Dict[str, Any]] = field(default_factory=list)
    estimated_duration: int = 0  # seconds
    privacy_annotations: Dict[str, PrivacyLevel] = field(default_factory=dict)
    safety_annotations: Dict[str, SafetyLevel] = field(default_factory=dict)


@dataclass
class UserOverlay:
    """User-specific learning and preferences overlay."""
    user_id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Preference biases
    energy_vs_comfort_bias: float = 0.5  # 0.0 = energy focused, 1.0 = comfort focused
    safety_vs_convenience_bias: float = 0.5
    privacy_vs_functionality_bias: float = 0.5
    
    # Device and room affinities
    device_affinities: Dict[str, float] = field(default_factory=dict)
    room_affinities: Dict[str, float] = field(default_factory=dict)
    
    # Time profiles
    time_profiles: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Learned patterns
    accepted_patterns: List[Dict[str, Any]] = field(default_factory=list)
    rejected_patterns: List[Dict[str, Any]] = field(default_factory=list)
    
    # Context preferences
    quiet_hours_start: time = time(22, 0)
    quiet_hours_end: time = time(7, 0)
    meeting_behavior: str = "minimal"  # "minimal", "normal", "enhanced"
    sleep_behavior: str = "quiet"  # "quiet", "normal", "enhanced"


@dataclass
class SituationPolicy:
    """Policy that guides suggestion generation for a specific situation."""
    policy_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    context_bucket: str = ""  # "morning", "evening", "meeting", "sleep", etc.
    
    # Discovery preferences
    discovery_width: float = 0.5  # 0.0 = narrow, 1.0 = broad
    novelty_preference: float = 0.3  # 0.0 = conservative, 1.0 = experimental
    
    # Filtering rules
    min_confidence_threshold: float = 0.6
    max_effort_threshold: EffortLevel = EffortLevel.MEDIUM
    privacy_threshold: PrivacyLevel = PrivacyLevel.PERSONAL
    safety_threshold: SafetyLevel = SafetyLevel.CAUTION
    
    # Context-specific overrides
    context_overrides: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SuggestionRequest:
    """Request for generating suggestions."""
    user_id: str = ""
    session_id: Optional[str] = None
    context_hints: Dict[str, Any] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)
    discovery_width: Optional[float] = None  # Override user's default
    max_recommendations: int = 10
    include_what_if: bool = True
    enable_llm_fallback: bool = True


@dataclass
class SuggestionResponse:
    """Response containing generated suggestions."""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "completed"
    recommendations: List[RecommendationCard] = field(default_factory=list)
    what_if_items: List[Dict[str, Any]] = field(default_factory=list)
    context_snapshot: Optional[ContextSnapshot] = None
    processing_time_ms: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    llm_generated: bool = False


@dataclass
class WhatIfItem:
    """What-if analysis item for missing capabilities."""
    capability_type: CapabilityType
    capability_name: str
    description: str
    example_outcomes: List[str] = field(default_factory=list)
    estimated_benefit: str = ""
    setup_effort: EffortLevel = EffortLevel.MEDIUM
    privacy_impact: PrivacyLevel = PrivacyLevel.PERSONAL
    safety_impact: SafetyLevel = SafetyLevel.SAFE


@dataclass
class FeedbackRecord:
    """Record of user feedback for learning."""
    feedback_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    recommendation_id: str = ""
    feedback_type: str = ""  # "accept", "reject", "snooze", "edit", "execute"
    feedback_data: Dict[str, Any] = field(default_factory=dict)
    context_snapshot: Optional[ContextSnapshot] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    success: Optional[bool] = None  # For execution feedback
