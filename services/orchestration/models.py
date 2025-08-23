"""
Orchestration Models
Core data structures for the orchestration system.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from enum import Enum
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
import uuid


class PrivacyClass(Enum):
    """Privacy classification levels."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class TrustTier(Enum):
    """Trust tier levels for device and user access."""
    UNTRUSTED = "untrusted"
    BASIC = "basic"
    VERIFIED = "verified"
    TRUSTED = "trusted"
    PRIVILEGED = "privileged"


class ExecutionStatus(Enum):
    """Execution plan status."""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepType(Enum):
    """Types of execution steps."""
    DEVICE_CONTROL = "device_control"
    DATA_COLLECTION = "data_collection"
    ML_INFERENCE = "ml_inference"
    NOTIFICATION = "notification"
    CONDITIONAL = "conditional"
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    FALLBACK = "fallback"


class TriggerType(Enum):
    """Types of orchestration triggers."""
    USER_REQUEST = "user_request"
    SCHEDULED_ROUTINE = "scheduled_routine"
    INSIGHT_RECOMMENDATION = "insight_recommendation"
    STATE_DRIFT = "state_drift"
    DEVICE_FAILURE = "device_failure"
    CONSENT_CHANGE = "consent_change"
    PREVIEW_REQUEST = "preview_request"


@dataclass
class Constraint:
    """Execution constraint."""
    type: str  # "privacy", "latency", "cost", "energy", "security"
    value: Any
    operator: str = "lte"  # "lte", "gte", "eq", "neq"
    priority: int = 1  # 1-10, higher is more important


@dataclass
class Goal:
    """Execution goal."""
    type: str  # "optimize", "minimize", "maximize", "achieve"
    target: str  # "privacy", "efficiency", "comfort", "cost"
    value: Any
    weight: float = 1.0


@dataclass
class DeviceCapability:
    """Device capability information."""
    device_id: str
    capability_type: str
    parameters: Dict[str, Any]
    privacy_class: PrivacyClass
    trust_tier: TrustTier
    local_processing: bool = True
    cloud_required: bool = False


class SignalDomain(Enum):
    """Domains of contextual signals."""
    PRESENCE_OCCUPANCY = "presence_occupancy"
    TIME_SCHEDULES = "time_schedules"
    SPACE_ZONES = "space_zones"
    ENVIRONMENT = "environment"
    ENERGY_POWER = "energy_power"
    WATER_GAS = "water_gas"
    NETWORK_HEALTH = "network_health"
    DEVICE_LIFECYCLE = "device_lifecycle"
    SECURITY_POSTURE = "security_posture"
    EXTERNAL_CONTEXT = "external_context"


class ConfidenceLevel(Enum):
    """Confidence levels for contextual data."""
    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class FreshnessStatus(Enum):
    """Freshness status of contextual data."""
    STALE = "stale"
    RECENT = "recent"
    CURRENT = "current"
    REAL_TIME = "real_time"


class PrivacySensitivity(Enum):
    """Privacy sensitivity levels."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


@dataclass
class SignalSource:
    """Source of a contextual signal."""
    source_id: str
    source_type: str  # device, app, service
    domain: SignalDomain
    consent_scope: str
    update_cadence_ms: int
    last_update: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedSignal:
    """Normalized contextual signal."""
    signal_id: str
    source: SignalSource
    domain: SignalDomain
    field_name: str
    value: Any
    unit: str
    timestamp: datetime
    confidence: ConfidenceLevel
    freshness: FreshnessStatus
    provenance: str
    consent_class: PrivacySensitivity
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Entity:
    """Entity in the system (device, user, zone)."""
    entity_id: str
    entity_type: str  # device, user, zone, room
    name: str
    zone_id: Optional[str] = None
    owner_id: Optional[str] = None
    traits: List[str] = field(default_factory=list)
    sensitivity_class: PrivacySensitivity = PrivacySensitivity.INTERNAL
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityRelationship:
    """Relationship between entities."""
    relationship_id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: str  # controls, located_in, owned_by, etc.
    confidence: ConfidenceLevel
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CapabilityNode:
    """Node in the capability graph."""
    node_id: str
    entity_id: str
    capability_type: str
    limits: Dict[str, Any] = field(default_factory=dict)
    latency_ms: int = 0
    cost_per_hour: float = 0.0
    dependencies: List[str] = field(default_factory=list)
    freshness: FreshnessStatus = FreshnessStatus.CURRENT
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    consent_class: PrivacySensitivity = PrivacySensitivity.INTERNAL
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CapabilityEdge:
    """Edge in the capability graph."""
    edge_id: str
    source_node_id: str
    target_node_id: str
    edge_type: str  # depends_on, communicates_with, etc.
    attributes: Dict[str, Any] = field(default_factory=dict)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CapabilityGraph:
    """Complete capability graph."""
    nodes: List[CapabilityNode] = field(default_factory=list)
    edges: List[CapabilityEdge] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DerivedFlag:
    """Derived contextual flag."""
    flag_id: str
    name: str
    value: bool
    inputs: List[str] = field(default_factory=list)  # List of signal IDs
    logic_reference: str = ""
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    expiry: Optional[datetime] = None
    explanation: str = ""
    privacy_class: PrivacySensitivity = PrivacySensitivity.INTERNAL
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextSnapshot:
    """Complete context snapshot."""
    snapshot_id: str
    timestamp: datetime
    signals: List[NormalizedSignal] = field(default_factory=list)
    derived_flags: List[DerivedFlag] = field(default_factory=list)
    capability_graph: CapabilityGraph = field(default_factory=CapabilityGraph)
    entities: List[Entity] = field(default_factory=list)
    relationships: List[EntityRelationship] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextQuery:
    """Query for contextual information."""
    query_id: str
    consumer: str
    required_domains: List[SignalDomain] = field(default_factory=list)
    required_flags: List[str] = field(default_factory=list)
    required_entities: List[str] = field(default_factory=list)
    max_age_ms: int = 5000
    privacy_scope: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextResponse:
    """Response to a context query."""
    query_id: str
    snapshot: ContextSnapshot
    freshness_score: float
    confidence_score: float
    privacy_compliance_score: float
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextEvent:
    """Context change event."""
    event_id: str
    event_type: str  # flag_changed, signal_updated, entity_added, etc.
    timestamp: datetime
    entity_id: Optional[str] = None
    flag_name: Optional[str] = None
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    explanation: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextMetrics:
    """Metrics for contextual awareness performance."""
    snapshot_id: str
    freshness_percentile_by_domain: Dict[SignalDomain, float] = field(default_factory=dict)
    confidence_distribution: Dict[ConfidenceLevel, int] = field(default_factory=dict)
    false_positive_rate: float = 0.0
    false_negative_rate: float = 0.0
    mean_detection_time_ms: int = 0
    data_minimization_score: float = 1.0
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class IngestionConfig:
    """Configuration for signal ingestion."""
    source_id: str
    enabled: bool = True
    push_enabled: bool = True
    pull_interval_ms: int = 5000
    adaptive_polling: bool = True
    importance_weight: float = 1.0
    change_rate_threshold: float = 0.1
    consent_scope: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FusionRule:
    """Rule for signal fusion and state estimation."""
    rule_id: str
    name: str
    output_field: str
    fusion_strategy: str  # weighted_voting, hysteresis, bayesian, windowed_average
    input_signals: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence_threshold: float = 0.7
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DerivedFlagRecipe:
    """Recipe for creating derived flags."""
    recipe_id: str
    flag_name: str
    logic: str  # Python expression or reference to logic function
    inputs: List[str] = field(default_factory=list)
    thresholds: Dict[str, Any] = field(default_factory=dict)
    privacy_class: PrivacySensitivity = PrivacySensitivity.INTERNAL
    expiry_window_ms: int = 300000  # 5 minutes default
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsentReference:
    """Reference to consent and permissions."""
    consent_token: str
    scopes: List[str]
    trust_tier: TrustTier
    expires_at: Optional[datetime] = None
    dynamic_consent: bool = False


@dataclass
class ExecutionStep:
    """Single step in an execution plan."""
    step_id: str
    step_type: StepType
    device_id: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    fallback_steps: List[str] = field(default_factory=list)
    guardrails: List[Dict[str, Any]] = field(default_factory=list)
    privacy_class: PrivacyClass = PrivacyClass.INTERNAL
    local_execution: bool = True
    estimated_duration_ms: int = 1000
    estimated_cost: float = 0.0


@dataclass
class ExecutionPlan:
    """Complete execution plan."""
    plan_id: str
    task_spec: 'TaskSpec'
    steps: List[ExecutionStep]
    constraints: List[Constraint]
    goals: List[Goal]
    context_snapshot: ContextSnapshot
    consent_references: List[ConsentReference]
    status: ExecutionStatus = ExecutionStatus.DRAFT
    rationale: str = ""
    approval_required: bool = False
    slas: Dict[str, Any] = field(default_factory=dict)
    budget: Dict[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        if not self.plan_id:
            self.plan_id = str(uuid.uuid4())
        self.updated_at = datetime.utcnow()


@dataclass
class TaskSpec:
    """Task specification from intent translation."""
    task_id: str
    trigger_type: TriggerType
    intent: str
    goals: List[Goal]
    constraints: List[Constraint]
    privacy_class: PrivacyClass
    trust_tier: TrustTier
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        if not self.task_id:
            self.task_id = str(uuid.uuid4())


@dataclass
class PlanMetrics:
    """Metrics for plan execution."""
    plan_id: str
    success_rate: float = 0.0
    time_to_plan_ms: int = 0
    approval_rate: float = 0.0
    user_overrides: int = 0
    privacy_score: float = 0.0  # percentage of steps kept local
    replan_frequency: int = 0
    total_executions: int = 0
    failed_executions: int = 0
    average_execution_time_ms: int = 0
    cost_per_execution: float = 0.0


class OrchestrationRequest(BaseModel):
    """Request to create an execution plan."""
    trigger_type: TriggerType
    intent: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    context_hints: Dict[str, Any] = Field(default_factory=dict)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    preview_mode: bool = False


class OrchestrationResponse(BaseModel):
    """Response from orchestration system."""
    plan_id: str
    status: ExecutionStatus
    plan: Optional[ExecutionPlan] = None
    rationale: str = ""
    approval_required: bool = False
    alternatives: List[ExecutionPlan] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class AllocationStatus(Enum):
    """Resource allocation status."""
    PENDING = "pending"
    FEASIBILITY_CHECK = "feasibility_check"
    PLACEMENT_DECISION = "placement_decision"
    BINDING = "binding"
    RESERVED = "reserved"
    DISPATCHED = "dispatched"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REBINDING = "rebinding"


class ResourceType(Enum):
    """Types of resources that can be allocated."""
    DEVICE = "device"
    EDGE_COMPUTE = "edge_compute"
    CLOUD_COMPUTE = "cloud_compute"
    NETWORK = "network"
    STORAGE = "storage"
    SENSOR = "sensor"
    ACTUATOR = "actuator"


class PlacementTarget(Enum):
    """Where a step can be placed."""
    LOCAL_DEVICE = "local_device"
    EDGE_GATEWAY = "edge_gateway"
    EDGE_CLUSTER = "edge_cluster"
    CLOUD_REGION = "cloud_region"
    HYBRID = "hybrid"


class FeasibilityStatus(Enum):
    """Feasibility check result."""
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class ResourceCapability:
    """Capability of a specific resource."""
    resource_id: str
    resource_type: ResourceType
    capabilities: List[str]
    protocols: List[str]
    power_state: str
    network_quality: float
    bandwidth_mbps: float
    latency_ms: float
    cost_per_hour: float
    available_slots: int
    current_load: float
    last_heartbeat: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FeasibilityResult:
    """Result of feasibility check for a step."""
    step_id: str
    status: FeasibilityStatus
    compatible_resources: List[ResourceCapability]
    estimated_energy_wh: float
    estimated_time_ms: int
    protocol_support: bool
    power_requirement_met: bool
    network_requirement_met: bool
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class PlacementDecision:
    """Decision about where to place a step."""
    step_id: str
    target: PlacementTarget
    primary_resource: ResourceCapability
    fallback_resources: List[ResourceCapability] = field(default_factory=list)
    rationale: str = ""
    expected_cost: float = 0.0
    expected_latency_ms: int = 0
    privacy_score: float = 1.0
    energy_efficiency: float = 1.0
    reliability_score: float = 1.0


@dataclass
class ResourceReservation:
    """Reservation of a resource for a specific time window."""
    reservation_id: str
    resource_id: str
    step_id: str
    start_time: datetime
    end_time: datetime
    priority: int
    exclusive: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BoundStep:
    """A step bound to specific resources."""
    step_id: str
    original_step: ExecutionStep
    placement: PlacementDecision
    reservation: ResourceReservation
    run_config: Dict[str, Any]
    consent_scope: str
    data_minimization_rules: List[str] = field(default_factory=list)
    retry_policy: Dict[str, Any] = field(default_factory=dict)
    rollback_hooks: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ResourceAllocation:
    """Complete resource allocation for an execution plan."""
    allocation_id: str
    plan_id: str
    status: AllocationStatus
    bound_steps: List[BoundStep]
    reservations: List[ResourceReservation]
    placement_rationale: str
    expected_total_cost: float
    expected_total_latency_ms: int
    privacy_score: float
    energy_efficiency: float
    reliability_score: float
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AllocationRequest:
    """Request to allocate resources for an execution plan."""
    plan_id: str
    execution_plan: ExecutionPlan
    user_id: str
    priority: int = 1
    deadline: Optional[datetime] = None
    cost_budget: Optional[float] = None
    latency_budget_ms: Optional[int] = None
    privacy_requirements: Dict[str, Any] = field(default_factory=dict)
    energy_constraints: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AllocationResponse:
    """Response from resource allocation."""
    allocation_id: str
    status: AllocationStatus
    bound_steps: List[BoundStep]
    placement_rationale: str
    expected_cost: float
    expected_latency_ms: int
    privacy_score: float
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RebindingRequest:
    """Request to rebind resources due to failure or drift."""
    allocation_id: str
    step_id: str
    reason: str
    current_resource_id: str
    new_requirements: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AllocationMetrics:
    """Metrics for resource allocation performance."""
    allocation_id: str
    placement_accuracy: float
    rebinding_rate: float
    local_execution_ratio: float
    device_utilization: float
    average_binding_time_ms: int
    cost_variance: float
    latency_variance: float
    privacy_compliance_score: float
    energy_efficiency_score: float
    created_at: datetime = field(default_factory=datetime.utcnow)
