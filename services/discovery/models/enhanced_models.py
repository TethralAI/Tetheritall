"""
Enhanced Data Models for IoT Discovery System

This module contains all the enhanced data models needed to support
the 14 planned enhancements to the IoT discovery system.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
import uuid


# ============================================================================
# ENHANCEMENT 1: Smart Device Recognition & Auto-Detection
# ============================================================================

class RecognitionType(str, Enum):
    """Types of device recognition methods."""
    CAMERA = "camera"
    VOICE = "voice"
    NFC = "nfc"
    QR_CODE = "qr_code"
    BLUETOOTH = "bluetooth"
    WIFI = "wifi"
    MANUAL = "manual"


@dataclass
class DeviceRecognitionResult:
    """Result from device recognition process."""
    device_id: str
    confidence: float
    recognition_type: RecognitionType
    raw_data: Dict[str, Any]
    processing_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CameraRecognitionData:
    """Data from camera-based device recognition."""
    image_path: str
    detected_text: List[str]
    detected_objects: List[str]
    device_brand: Optional[str] = None
    device_model: Optional[str] = None
    serial_number: Optional[str] = None


@dataclass
class VoiceRecognitionData:
    """Data from voice-based device recognition."""
    audio_path: str
    transcribed_text: str
    intent: str
    entities: Dict[str, str]
    confidence: float


@dataclass
class NFCData:
    """Data from NFC-based device recognition."""
    tag_id: str
    tag_type: str
    payload: bytes
    manufacturer: Optional[str] = None


# ============================================================================
# ENHANCEMENT 2: Proactive Discovery Intelligence
# ============================================================================

class DiscoverySource(str, Enum):
    """Sources of proactive device discovery."""
    NETWORK_SCAN = "network_scan"
    BLUETOOTH_BEACON = "bluetooth_beacon"
    EMAIL_PARSING = "email_parsing"
    HUB_INTEGRATION = "hub_integration"
    WIFI_MONITORING = "wifi_monitoring"


@dataclass
class ProactiveDiscoveryEvent:
    """Event from proactive discovery."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: DiscoverySource = DiscoverySource.NETWORK_SCAN
    timestamp: datetime = field(default_factory=datetime.utcnow)
    device_hints: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NetworkDiscoveryData:
    """Data from network monitoring."""
    ip_address: str
    mac_address: str
    hostname: Optional[str] = None
    services: List[str] = field(default_factory=list)
    device_type: Optional[str] = None
    manufacturer: Optional[str] = None


@dataclass
class EmailDiscoveryData:
    """Data from email parsing."""
    email_id: str
    sender: str
    subject: str
    order_number: Optional[str] = None
    device_brand: Optional[str] = None
    device_model: Optional[str] = None
    tracking_number: Optional[str] = None


# ============================================================================
# ENHANCEMENT 3: Guided Onboarding Wizards
# ============================================================================

class WizardStepType(str, Enum):
    """Types of wizard steps."""
    INFORMATION = "information"
    ACTION = "action"
    VERIFICATION = "verification"
    TROUBLESHOOTING = "troubleshooting"
    COMPLETION = "completion"


@dataclass
class WizardStep:
    """A step in the onboarding wizard."""
    step_id: str
    step_type: WizardStepType
    title: str
    description: str
    instructions: List[str]
    expected_duration: int  # seconds
    required: bool = True
    completed: bool = False
    error_message: Optional[str] = None
    help_resources: List[str] = field(default_factory=list)


@dataclass
class BrandWizard:
    """Brand-specific onboarding wizard."""
    brand_id: str
    brand_name: str
    device_types: List[str]
    steps: List[WizardStep]
    estimated_total_time: int  # seconds
    success_rate: float
    common_issues: List[str] = field(default_factory=list)
    video_tutorials: List[str] = field(default_factory=list)


@dataclass
class WizardProgress:
    """Progress tracking for onboarding wizard."""
    wizard_id: str
    current_step: int
    completed_steps: List[str]
    total_steps: int
    start_time: datetime
    estimated_completion: datetime
    paused: bool = False
    error_count: int = 0


# ============================================================================
# ENHANCEMENT 4: Predictive Device Suggestions
# ============================================================================

class SuggestionType(str, Enum):
    """Types of device suggestions."""
    COMPLEMENTARY = "complementary"
    ROOM_OPTIMIZATION = "room_optimization"
    ROUTINE_ENHANCEMENT = "routine_enhancement"
    REPLACEMENT = "replacement"
    UPGRADE = "upgrade"


@dataclass
class DeviceSuggestion:
    """A device suggestion for the user."""
    suggestion_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    suggestion_type: SuggestionType = SuggestionType.COMPLEMENTARY
    device_brand: str
    device_model: str
    device_type: str
    reason: str
    confidence: float
    estimated_value: float  # 0-1 scale
    estimated_effort: float  # 0-1 scale
    compatibility_score: float
    price_range: Optional[str] = None
    availability: bool = True


@dataclass
class RoomOptimizationSuggestion:
    """Suggestion for room-specific device optimization."""
    room_name: str
    current_devices: List[str]
    suggested_devices: List[DeviceSuggestion]
    optimization_score: float
    reasoning: str


# ============================================================================
# ENHANCEMENT 5: Intelligent Error Recovery
# ============================================================================

class ErrorSeverity(str, Enum):
    """Severity levels for errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Context information for error recovery."""
    error_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    error_type: str
    severity: ErrorSeverity
    device_id: Optional[str] = None
    step_id: Optional[str] = None
    user_actions: List[str] = field(default_factory=list)
    system_state: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RecoveryAction:
    """A recovery action for an error."""
    action_id: str
    description: str
    success_probability: float
    estimated_time: int  # seconds
    user_effort: float  # 0-1 scale
    automated: bool = False
    prerequisites: List[str] = field(default_factory=list)


@dataclass
class ErrorRecoveryPlan:
    """Plan for recovering from an error."""
    error_context: ErrorContext
    recovery_actions: List[RecoveryAction]
    estimated_total_time: int
    success_probability: float
    alternative_paths: List[str] = field(default_factory=list)


# ============================================================================
# ENHANCEMENT 6: Granular Privacy Controls
# ============================================================================

class PrivacyLevel(str, Enum):
    """Privacy levels for device data."""
    MINIMAL = "minimal"
    STANDARD = "standard"
    ENHANCED = "enhanced"
    MAXIMUM = "maximum"


@dataclass
class PrivacyPermission:
    """A privacy permission for a device."""
    permission_id: str
    device_id: str
    data_type: str
    access_level: PrivacyLevel
    purpose: str
    retention_period: timedelta
    shared_with: List[str] = field(default_factory=list)
    user_consent: bool = False
    consent_date: Optional[datetime] = None


@dataclass
class PrivacyProfile:
    """Privacy profile for a user or device."""
    profile_id: str
    name: str
    default_level: PrivacyLevel
    permissions: List[PrivacyPermission]
    data_retention_policy: Dict[str, timedelta]
    sharing_preferences: Dict[str, bool]


# ============================================================================
# ENHANCEMENT 7: Security Hardening
# ============================================================================

class SecurityThreatLevel(str, Enum):
    """Security threat levels."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DeviceFingerprint:
    """Security fingerprint for a device."""
    device_id: str
    hardware_signature: str
    software_signature: str
    network_signature: str
    behavior_pattern: Dict[str, Any]
    last_updated: datetime
    threat_level: SecurityThreatLevel = SecurityThreatLevel.NONE


@dataclass
class SecurityAlert:
    """Security alert for a device or network."""
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    device_id: Optional[str] = None
    threat_type: str
    threat_level: SecurityThreatLevel
    description: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False
    recommended_actions: List[str] = field(default_factory=list)


# ============================================================================
# ENHANCEMENT 8: Simplified Interface
# ============================================================================

class InterfaceMode(str, Enum):
    """Interface modes for different user types."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    ACCESSIBLE = "accessible"


@dataclass
class OneTapAction:
    """A one-tap action for device setup."""
    action_id: str
    title: str
    description: str
    icon: str
    success_probability: float
    estimated_time: int
    prerequisites: List[str] = field(default_factory=list)
    fallback_actions: List[str] = field(default_factory=list)


@dataclass
class BulkOperation:
    """Bulk operation for multiple devices."""
    operation_id: str
    operation_type: str
    device_ids: List[str]
    total_devices: int
    completed_devices: int
    failed_devices: List[str] = field(default_factory=list)
    estimated_completion: datetime
    status: str = "pending"


# ============================================================================
# ENHANCEMENT 9: Smart Notifications
# ============================================================================

class NotificationType(str, Enum):
    """Types of smart notifications."""
    SETUP_REMINDER = "setup_reminder"
    SUCCESS_CELEBRATION = "success_celebration"
    HELPFUL_TIP = "helpful_tip"
    COMMUNITY_ALERT = "community_alert"
    SECURITY_ALERT = "security_alert"
    MAINTENANCE_REMINDER = "maintenance_reminder"


@dataclass
class SmartNotification:
    """A smart notification for the user."""
    notification_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    notification_type: NotificationType
    title: str
    message: str
    priority: int  # 1-5, higher is more important
    timestamp: datetime = field(default_factory=datetime.utcnow)
    read: bool = False
    action_required: bool = False
    action_url: Optional[str] = None
    expires_at: Optional[datetime] = None


# ============================================================================
# ENHANCEMENT 10: Performance Optimizations
# ============================================================================

@dataclass
class DiscoveryCache:
    """Cache for discovery results."""
    cache_key: str
    data: Any
    timestamp: datetime
    ttl: timedelta
    hit_count: int = 0


@dataclass
class ParallelTask:
    """A task for parallel processing."""
    task_id: str
    task_type: str
    priority: int
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None


# ============================================================================
# ENHANCEMENT 11: Integration Ecosystem
# ============================================================================

class IntegrationType(str, Enum):
    """Types of integrations."""
    VOICE_ASSISTANT = "voice_assistant"
    SMART_HOME_HUB = "smart_home_hub"
    CLOUD_SERVICE = "cloud_service"
    AUTOMATION_PLATFORM = "automation_platform"


@dataclass
class IntegrationConfig:
    """Configuration for an integration."""
    integration_id: str
    integration_type: IntegrationType
    name: str
    enabled: bool
    config: Dict[str, Any]
    last_sync: Optional[datetime] = None
    sync_status: str = "unknown"


# ============================================================================
# ENHANCEMENT 12: Setup Analytics
# ============================================================================

@dataclass
class SetupMetrics:
    """Metrics for device setup."""
    setup_id: str
    device_id: str
    start_time: datetime
    completion_time: Optional[datetime] = None
    total_duration: Optional[int] = None  # seconds
    steps_completed: int
    total_steps: int
    errors_encountered: int
    user_abandoned: bool = False
    success: bool = False


@dataclass
class UserBehaviorEvent:
    """User behavior event for analytics."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    event_type: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    context: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None


# ============================================================================
# ENHANCEMENT 13: Device Management
# ============================================================================

@dataclass
class DeviceGroup:
    """A group of devices."""
    group_id: str
    name: str
    description: str
    device_ids: List[str]
    group_type: str  # room, function, brand, etc.
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MaintenanceTask:
    """A maintenance task for a device."""
    task_id: str
    device_id: str
    task_type: str
    description: str
    due_date: datetime
    completed: bool = False
    completed_date: Optional[datetime] = None
    priority: int = 1


# ============================================================================
# ENHANCEMENT 14: Community Features
# ============================================================================

@dataclass
class CommunitySetup:
    """A community-shared device setup."""
    setup_id: str
    user_id: str
    device_brand: str
    device_model: str
    setup_steps: List[str]
    tips: List[str]
    rating: float
    review_count: int
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CommunityReview:
    """A community review for a device or setup."""
    review_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    target_id: str  # device_id or setup_id
    target_type: str  # device or setup
    rating: int  # 1-5
    title: str
    content: str
    helpful_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TroubleshootingThread:
    """A troubleshooting thread in the community forum."""
    thread_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str
    description: str
    device_brand: Optional[str] = None
    device_model: Optional[str] = None
    status: str = "open"  # open, resolved, closed
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    reply_count: int = 0
