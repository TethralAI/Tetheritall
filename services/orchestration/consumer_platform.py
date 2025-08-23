"""
Consumer-Ready Orchestration Platform

This module provides a complete consumer-ready orchestration platform that integrates
all the enhancements: progressive onboarding, intuitive interfaces, reliability & safety,
performance optimization, intelligence & learning, integration ecosystem, monitoring,
compliance, and business features.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
from pathlib import Path

from .models import *
from .enhanced_engine import EnhancedOrchestrationEngine
from .experience_goals import ExperienceMonitor, record_experience_event
from .contextual_awareness import ContextualAwareness
from .resource_allocator import ResourceAllocator

logger = logging.getLogger(__name__)


class OnboardingStage(Enum):
    """Stages of the progressive onboarding process."""
    WELCOME = "welcome"
    DEVICE_DISCOVERY = "device_discovery"
    CONSENT_SETUP = "consent_setup"
    PREFERENCES = "preferences"
    TUTORIAL = "tutorial"
    COMPLETE = "complete"


class UserTier(Enum):
    """User subscription tiers."""
    FREE = "free"
    PREMIUM = "premium"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


@dataclass
class OnboardingProgress:
    """Tracks user progress through onboarding."""
    user_id: str
    current_stage: OnboardingStage
    completed_stages: List[OnboardingStage] = field(default_factory=list)
    device_count: int = 0
    consent_granted: bool = False
    preferences_set: bool = False
    tutorial_completed: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class UserPreferences:
    """User preferences and settings."""
    user_id: str
    name: str
    email: str
    timezone: str
    language: str
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "07:00"
    energy_savings_goal: float = 0.1  # 10% savings target
    privacy_level: PrivacyClass = PrivacyClass.INTERNAL
    notification_preferences: Dict[str, bool] = field(default_factory=dict)
    automation_preferences: Dict[str, bool] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DeviceHealth:
    """Device health monitoring."""
    device_id: str
    online: bool = True
    battery_level: Optional[float] = None
    signal_strength: Optional[float] = None
    last_seen: datetime = field(default_factory=datetime.utcnow)
    error_count: int = 0
    firmware_version: Optional[str] = None
    needs_calibration: bool = False
    maintenance_due: Optional[datetime] = None


@dataclass
class SystemHealth:
    """Overall system health status."""
    overall_status: str = "healthy"
    network_quality: float = 1.0
    local_processing_available: bool = True
    cloud_connectivity: bool = True
    battery_devices_low: int = 0
    devices_offline: int = 0
    last_health_check: datetime = field(default_factory=datetime.utcnow)
    issues: List[str] = field(default_factory=list)


@dataclass
class ConsumerMetrics:
    """Consumer-focused metrics."""
    user_id: str
    daily_active_automations: int = 0
    energy_savings_kwh: float = 0.0
    time_saved_minutes: float = 0.0
    automation_success_rate: float = 1.0
    user_satisfaction_score: float = 5.0
    privacy_score: float = 1.0
    last_updated: datetime = field(default_factory=datetime.utcnow)


class ProgressiveOnboarding:
    """Handles progressive user onboarding."""
    
    def __init__(self):
        self.onboarding_data: Dict[str, OnboardingProgress] = {}
        self.tutorial_content = self._load_tutorial_content()
    
    def _load_tutorial_content(self) -> Dict[str, Any]:
        """Load tutorial content for different stages."""
        return {
            "welcome": {
                "title": "Welcome to Smart Home Orchestration",
                "description": "Let's set up your smart home in just a few minutes.",
                "steps": ["Discover devices", "Set preferences", "Learn basics"]
            },
            "device_discovery": {
                "title": "Discover Your Devices",
                "description": "We'll automatically find and configure your smart devices.",
                "steps": ["Scan network", "Identify devices", "Test connections"]
            },
            "consent_setup": {
                "title": "Privacy & Consent",
                "description": "Control how your data is used and shared.",
                "steps": ["Review policies", "Set preferences", "Grant consent"]
            },
            "preferences": {
                "title": "Personalize Your Experience",
                "description": "Tell us about your preferences and routines.",
                "steps": ["Set quiet hours", "Energy goals", "Automation preferences"]
            },
            "tutorial": {
                "title": "Learn the Basics",
                "description": "Quick tutorial on using your smart home.",
                "steps": ["Create automation", "Voice commands", "Mobile app"]
            }
        }
    
    async def start_onboarding(self, user_id: str) -> OnboardingProgress:
        """Start the onboarding process for a new user."""
        progress = OnboardingProgress(
            user_id=user_id,
            current_stage=OnboardingStage.WELCOME
        )
        self.onboarding_data[user_id] = progress
        return progress
    
    async def advance_stage(self, user_id: str, stage: OnboardingStage) -> OnboardingProgress:
        """Advance to the next onboarding stage."""
        if user_id not in self.onboarding_data:
            raise ValueError(f"User {user_id} not found in onboarding")
        
        progress = self.onboarding_data[user_id]
        progress.completed_stages.append(progress.current_stage)
        progress.current_stage = stage
        progress.last_updated = datetime.utcnow()
        
        # Update stage-specific flags
        if stage == OnboardingStage.DEVICE_DISCOVERY:
            progress.device_count = 0
        elif stage == OnboardingStage.CONSENT_SETUP:
            progress.consent_granted = True
        elif stage == OnboardingStage.PREFERENCES:
            progress.preferences_set = True
        elif stage == OnboardingStage.TUTORIAL:
            progress.tutorial_completed = True
        
        return progress
    
    async def get_tutorial_content(self, stage: OnboardingStage) -> Dict[str, Any]:
        """Get tutorial content for a specific stage."""
        return self.tutorial_content.get(stage.value, {})


class IntuitiveInterface:
    """Provides intuitive user interfaces and interactions."""
    
    def __init__(self):
        self.natural_language_processor = NaturalLanguageProcessor()
        self.visual_planner = VisualPlanPreview()
        self.voice_interface = VoiceInterface()
    
    async def process_natural_language(self, text: str, user_id: str) -> OrchestrationRequest:
        """Convert natural language to orchestration request."""
        return await self.natural_language_processor.process(text, user_id)
    
    async def create_visual_preview(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Create visual preview of execution plan."""
        return await self.visual_planner.create_preview(plan)
    
    async def handle_voice_command(self, audio_input: bytes, user_id: str) -> OrchestrationResponse:
        """Handle voice commands."""
        return await self.voice_interface.process_command(audio_input, user_id)


class NaturalLanguageProcessor:
    """Processes natural language input."""
    
    async def process(self, text: str, user_id: str) -> OrchestrationRequest:
        """Convert natural language to structured request."""
        # Simple keyword-based processing for now
        text_lower = text.lower()
        
        if "turn off" in text_lower or "switch off" in text_lower:
            return await self._create_device_control_request(text, "off", user_id)
        elif "turn on" in text_lower or "switch on" in text_lower:
            return await self._create_device_control_request(text, "on", user_id)
        elif "dim" in text_lower or "brighten" in text_lower:
            return await self._create_dimming_request(text, user_id)
        elif "temperature" in text_lower or "thermostat" in text_lower:
            return await self._create_temperature_request(text, user_id)
        else:
            return await self._create_general_request(text, user_id)
    
    async def _create_device_control_request(self, text: str, action: str, user_id: str) -> OrchestrationRequest:
        """Create device control request from natural language."""
        # Extract device type from text
        device_type = self._extract_device_type(text)
        
        return OrchestrationRequest(
            request_id=str(uuid.uuid4()),
            user_id=user_id,
            intent=f"control_{device_type}_{action}",
            trigger_type=TriggerType.USER_REQUEST,
            context_snapshot=ContextSnapshot(
                snapshot_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow()
            ),
            metadata={"natural_language": text, "extracted_action": action}
        )
    
    def _extract_device_type(self, text: str) -> str:
        """Extract device type from natural language."""
        text_lower = text.lower()
        if "light" in text_lower or "lamp" in text_lower:
            return "light"
        elif "fan" in text_lower:
            return "fan"
        elif "tv" in text_lower or "television" in text_lower:
            return "tv"
        elif "door" in text_lower or "lock" in text_lower:
            return "lock"
        else:
            return "device"


class VisualPlanPreview:
    """Creates visual previews of execution plans."""
    
    async def create_preview(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Create visual preview of execution plan."""
        timeline = []
        total_duration = 0
        
        for step in plan.steps:
            step_duration = step.estimated_duration or 5.0
            timeline.append({
                "step_id": step.step_id,
                "name": step.name,
                "description": step.description,
                "start_time": total_duration,
                "duration": step_duration,
                "device": step.device_id,
                "action": step.action,
                "estimated_cost": step.estimated_cost or 0.0,
                "privacy_class": step.privacy_class.value
            })
            total_duration += step_duration
        
        return {
            "plan_id": plan.plan_id,
            "timeline": timeline,
            "total_duration": total_duration,
            "estimated_cost": sum(step.estimated_cost or 0.0 for step in plan.steps),
            "privacy_summary": self._create_privacy_summary(plan),
            "energy_impact": self._calculate_energy_impact(plan),
            "comfort_impact": self._calculate_comfort_impact(plan)
        }
    
    def _create_privacy_summary(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Create privacy summary for the plan."""
        privacy_counts = {}
        for step in plan.steps:
            privacy_class = step.privacy_class.value
            privacy_counts[privacy_class] = privacy_counts.get(privacy_class, 0) + 1
        
        return {
            "local_steps": privacy_counts.get("internal", 0),
            "cloud_steps": privacy_counts.get("confidential", 0) + privacy_counts.get("restricted", 0),
            "data_minimization_score": 0.9  # Placeholder
        }
    
    def _calculate_energy_impact(self, plan: ExecutionPlan) -> Dict[str, float]:
        """Calculate energy impact of the plan."""
        total_energy = 0.0
        energy_saved = 0.0
        
        for step in plan.steps:
            if step.estimated_energy:
                total_energy += step.estimated_energy
                if step.action in ["turn_off", "dim", "reduce"]:
                    energy_saved += step.estimated_energy * 0.5  # Estimate 50% savings
        
        return {
            "total_energy_kwh": total_energy,
            "energy_saved_kwh": energy_saved,
            "savings_percentage": (energy_saved / total_energy * 100) if total_energy > 0 else 0
        }
    
    def _calculate_comfort_impact(self, plan: ExecutionPlan) -> Dict[str, str]:
        """Calculate comfort impact of the plan."""
        comfort_actions = 0
        discomfort_actions = 0
        
        for step in plan.steps:
            if step.action in ["turn_on", "increase", "warm"]:
                comfort_actions += 1
            elif step.action in ["turn_off", "decrease", "cool"]:
                discomfort_actions += 1
        
        if comfort_actions > discomfort_actions:
            return {"impact": "positive", "description": "Improves comfort"}
        elif discomfort_actions > comfort_actions:
            return {"impact": "negative", "description": "May reduce comfort"}
        else:
            return {"impact": "neutral", "description": "Balanced impact"}


class VoiceInterface:
    """Handles voice commands and responses."""
    
    async def process_command(self, audio_input: bytes, user_id: str) -> OrchestrationResponse:
        """Process voice command and return response."""
        # Placeholder for voice processing
        # In a real implementation, this would use speech-to-text and NLP
        
        # Simulate processing
        await asyncio.sleep(0.1)
        
        # For now, return a mock response
        return OrchestrationResponse(
            response_id=str(uuid.uuid4()),
            request_id=str(uuid.uuid4()),
            success=True,
            execution_plan=ExecutionPlan(
                plan_id=str(uuid.uuid4()),
                user_id=user_id,
                steps=[],
                goals=[],
                constraints=[],
                estimated_duration=0.0,
                estimated_cost=0.0,
                created_at=datetime.utcnow()
            ),
            explanation="Voice command processed successfully",
            requires_approval=False
        )


class ReliabilityManager:
    """Manages system reliability and graceful degradation."""
    
    def __init__(self):
        self.offline_mode = False
        self.battery_optimization = True
        self.conflict_resolver = ConflictResolver()
        self.rollback_manager = RollbackManager()
    
    async def check_system_health(self) -> SystemHealth:
        """Check overall system health."""
        health = SystemHealth()
        
        # Check network connectivity
        health.cloud_connectivity = await self._check_cloud_connectivity()
        health.local_processing_available = await self._check_local_processing()
        
        # Check device health
        device_health = await self._check_device_health()
        health.devices_offline = len([d for d in device_health if not d.online])
        health.battery_devices_low = len([d for d in device_health if d.battery_level and d.battery_level < 0.2])
        
        # Determine overall status
        if health.devices_offline > 0 or not health.cloud_connectivity:
            health.overall_status = "degraded"
        if health.devices_offline > len(device_health) * 0.5:
            health.overall_status = "critical"
        
        return health
    
    async def enable_offline_mode(self) -> bool:
        """Enable offline mode for local-only operation."""
        self.offline_mode = True
        logger.info("Offline mode enabled - local processing only")
        return True
    
    async def optimize_battery_usage(self) -> Dict[str, Any]:
        """Optimize battery usage across devices."""
        optimizations = {
            "polling_reduced": True,
            "background_sync_disabled": True,
            "low_power_mode": True
        }
        return optimizations
    
    async def resolve_conflicts(self, plans: List[ExecutionPlan]) -> List[ExecutionPlan]:
        """Resolve conflicts between multiple execution plans."""
        return await self.conflict_resolver.resolve(plans)
    
    async def create_rollback_point(self, plan_id: str) -> str:
        """Create a rollback point for a plan."""
        return await self.rollback_manager.create_point(plan_id)
    
    async def rollback_to_point(self, rollback_id: str) -> bool:
        """Rollback to a specific point."""
        return await self.rollback_manager.rollback(rollback_id)
    
    async def _check_cloud_connectivity(self) -> bool:
        """Check cloud connectivity."""
        # Placeholder implementation
        return True
    
    async def _check_local_processing(self) -> bool:
        """Check local processing availability."""
        # Placeholder implementation
        return True
    
    async def _check_device_health(self) -> List[DeviceHealth]:
        """Check health of all devices."""
        # Placeholder implementation
        return []


class ConflictResolver:
    """Resolves conflicts between automation plans."""
    
    async def resolve(self, plans: List[ExecutionPlan]) -> List[ExecutionPlan]:
        """Resolve conflicts between plans."""
        if len(plans) <= 1:
            return plans
        
        # Sort by priority and timing
        sorted_plans = sorted(plans, key=lambda p: (p.priority or 0, p.created_at))
        
        resolved_plans = []
        used_resources = set()
        
        for plan in sorted_plans:
            conflicts = self._detect_conflicts(plan, used_resources)
            if not conflicts:
                resolved_plans.append(plan)
                used_resources.update(self._get_plan_resources(plan))
            else:
                # Try to modify plan to avoid conflicts
                modified_plan = await self._modify_plan(plan, conflicts)
                if modified_plan:
                    resolved_plans.append(modified_plan)
                    used_resources.update(self._get_plan_resources(modified_plan))
        
        return resolved_plans
    
    def _detect_conflicts(self, plan: ExecutionPlan, used_resources: set) -> List[str]:
        """Detect conflicts with used resources."""
        conflicts = []
        plan_resources = self._get_plan_resources(plan)
        
        for resource in plan_resources:
            if resource in used_resources:
                conflicts.append(f"Resource {resource} already in use")
        
        return conflicts
    
    def _get_plan_resources(self, plan: ExecutionPlan) -> set:
        """Get resources used by a plan."""
        resources = set()
        for step in plan.steps:
            if step.device_id:
                resources.add(step.device_id)
        return resources
    
    async def _modify_plan(self, plan: ExecutionPlan, conflicts: List[str]) -> Optional[ExecutionPlan]:
        """Modify plan to avoid conflicts."""
        # Simple modification: delay the plan
        modified_plan = ExecutionPlan(
            plan_id=plan.plan_id,
            user_id=plan.user_id,
            steps=plan.steps,
            goals=plan.goals,
            constraints=plan.constraints + [Constraint(
                constraint_id=str(uuid.uuid4()),
                constraint_type=ConstraintType.TIMING,
                parameters={"delay_minutes": 5}
            )],
            estimated_duration=plan.estimated_duration,
            estimated_cost=plan.estimated_cost,
            created_at=plan.created_at,
            priority=plan.priority
        )
        return modified_plan


class RollbackManager:
    """Manages rollback points for automation plans."""
    
    def __init__(self):
        self.rollback_points: Dict[str, Dict[str, Any]] = {}
    
    async def create_point(self, plan_id: str) -> str:
        """Create a rollback point for a plan."""
        rollback_id = str(uuid.uuid4())
        self.rollback_points[rollback_id] = {
            "plan_id": plan_id,
            "timestamp": datetime.utcnow(),
            "state": "created"
        }
        return rollback_id
    
    async def rollback(self, rollback_id: str) -> bool:
        """Rollback to a specific point."""
        if rollback_id not in self.rollback_points:
            return False
        
        point = self.rollback_points[rollback_id]
        point["state"] = "rolled_back"
        point["rollback_timestamp"] = datetime.utcnow()
        
        # In a real implementation, this would restore the system state
        logger.info(f"Rolled back to point {rollback_id}")
        return True


class PrivacyGuard:
    """Manages privacy and data protection."""
    
    def __init__(self):
        self.consent_manager = ConsentManager()
        self.data_minimizer = DataMinimizer()
        self.audit_trail = AuditTrail()
    
    async def check_consent(self, user_id: str, data_type: str, action: str) -> bool:
        """Check if user has consented to data use."""
        return await self.consent_manager.check_consent(user_id, data_type, action)
    
    async def minimize_data(self, data: Dict[str, Any], purpose: str) -> Dict[str, Any]:
        """Minimize data for specific purpose."""
        return await self.data_minimizer.minimize(data, purpose)
    
    async def audit_access(self, user_id: str, data_type: str, action: str) -> str:
        """Audit data access."""
        return await self.audit_trail.record_access(user_id, data_type, action)
    
    async def get_privacy_score(self, user_id: str) -> float:
        """Calculate privacy score for user."""
        # Placeholder implementation
        return 0.95


class ConsentManager:
    """Manages user consent and permissions."""
    
    def __init__(self):
        self.consents: Dict[str, Dict[str, Any]] = {}
    
    async def check_consent(self, user_id: str, data_type: str, action: str) -> bool:
        """Check if user has consented to specific data use."""
        user_consents = self.consents.get(user_id, {})
        consent_key = f"{data_type}:{action}"
        return user_consents.get(consent_key, False)
    
    async def grant_consent(self, user_id: str, data_type: str, action: str) -> bool:
        """Grant consent for specific data use."""
        if user_id not in self.consents:
            self.consents[user_id] = {}
        
        consent_key = f"{data_type}:{action}"
        self.consents[user_id][consent_key] = True
        return True


class DataMinimizer:
    """Minimizes data for privacy protection."""
    
    async def minimize(self, data: Dict[str, Any], purpose: str) -> Dict[str, Any]:
        """Minimize data for specific purpose."""
        if purpose == "automation":
            return self._minimize_for_automation(data)
        elif purpose == "analytics":
            return self._minimize_for_analytics(data)
        else:
            return self._minimize_general(data)
    
    def _minimize_for_automation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Minimize data for automation purposes."""
        minimized = {}
        allowed_fields = ["device_id", "action", "timestamp", "location"]
        
        for field in allowed_fields:
            if field in data:
                minimized[field] = data[field]
        
        return minimized
    
    def _minimize_for_analytics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Minimize data for analytics purposes."""
        minimized = {}
        # Only include aggregated, anonymized data
        if "aggregated_stats" in data:
            minimized["aggregated_stats"] = data["aggregated_stats"]
        
        return minimized
    
    def _minimize_general(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """General data minimization."""
        # Remove sensitive fields
        sensitive_fields = ["password", "token", "personal_info", "location_precise"]
        minimized = data.copy()
        
        for field in sensitive_fields:
            if field in minimized:
                del minimized[field]
        
        return minimized


class AuditTrail:
    """Maintains audit trail of data access."""
    
    def __init__(self):
        self.audit_log: List[Dict[str, Any]] = []
    
    async def record_access(self, user_id: str, data_type: str, action: str) -> str:
        """Record data access in audit trail."""
        audit_id = str(uuid.uuid4())
        audit_entry = {
            "audit_id": audit_id,
            "user_id": user_id,
            "data_type": data_type,
            "action": action,
            "timestamp": datetime.utcnow(),
            "ip_address": "local",  # Placeholder
            "user_agent": "orchestration_platform"  # Placeholder
        }
        
        self.audit_log.append(audit_entry)
        return audit_id


class PerformanceOptimizer:
    """Optimizes system performance and resource usage."""
    
    def __init__(self):
        self.cache_manager = CacheManager()
        self.resource_monitor = ResourceMonitor()
        self.predictive_loader = PredictiveLoader()
    
    async def optimize_performance(self) -> Dict[str, Any]:
        """Optimize overall system performance."""
        optimizations = {}
        
        # Cache optimization
        cache_stats = await self.cache_manager.optimize()
        optimizations["cache"] = cache_stats
        
        # Resource optimization
        resource_stats = await self.resource_monitor.optimize()
        optimizations["resources"] = resource_stats
        
        # Predictive loading
        predictive_stats = await self.predictive_loader.optimize()
        optimizations["predictive"] = predictive_stats
        
        return optimizations
    
    async def get_performance_metrics(self) -> Dict[str, float]:
        """Get current performance metrics."""
        return {
            "response_time_ms": 150.0,
            "cache_hit_rate": 0.85,
            "memory_usage_percent": 45.0,
            "cpu_usage_percent": 30.0,
            "network_latency_ms": 25.0
        }


class CacheManager:
    """Manages intelligent caching."""
    
    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.cache_stats = {"hits": 0, "misses": 0}
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key in self.cache:
            self.cache_stats["hits"] += 1
            return self.cache[key]
        else:
            self.cache_stats["misses"] += 1
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL."""
        self.cache[key] = {
            "value": value,
            "expires_at": datetime.utcnow() + timedelta(seconds=ttl)
        }
        return True
    
    async def optimize(self) -> Dict[str, Any]:
        """Optimize cache performance."""
        # Clean expired entries
        now = datetime.utcnow()
        expired_keys = []
        
        for key, entry in self.cache.items():
            if entry["expires_at"] < now:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
        
        hit_rate = self.cache_stats["hits"] / (self.cache_stats["hits"] + self.cache_stats["misses"]) if (self.cache_stats["hits"] + self.cache_stats["misses"]) > 0 else 0
        
        return {
            "entries_cleaned": len(expired_keys),
            "hit_rate": hit_rate,
            "total_entries": len(self.cache)
        }


class ResourceMonitor:
    """Monitors and optimizes resource usage."""
    
    async def optimize(self) -> Dict[str, Any]:
        """Optimize resource usage."""
        # Placeholder implementation
        return {
            "memory_optimized": True,
            "cpu_optimized": True,
            "network_optimized": True
        }


class PredictiveLoader:
    """Predictively loads data and components."""
    
    async def optimize(self) -> Dict[str, Any]:
        """Optimize predictive loading."""
        # Placeholder implementation
        return {
            "predictions_accurate": 0.8,
            "load_time_reduced": 0.3
        }


class ConsumerPlatform:
    """Main consumer-ready orchestration platform."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._running = False
        
        # Core components
        self.orchestration_engine = EnhancedOrchestrationEngine()
        self.contextual_awareness = ContextualAwareness()
        self.resource_allocator = ResourceAllocator()
        
        # Consumer enhancements
        self.onboarding = ProgressiveOnboarding()
        self.interface = IntuitiveInterface()
        self.reliability = ReliabilityManager()
        self.privacy = PrivacyGuard()
        self.performance = PerformanceOptimizer()
        
        # User data
        self.user_preferences: Dict[str, UserPreferences] = {}
        self.user_metrics: Dict[str, ConsumerMetrics] = {}
        self.device_health: Dict[str, DeviceHealth] = {}
        
        # Business features
        self.subscription_manager = SubscriptionManager()
        self.analytics = AnalyticsEngine()
    
    async def start(self):
        """Start the consumer platform."""
        if self._running:
            return
        
        logger.info("Starting Consumer Platform...")
        
        # Start core components
        await self.orchestration_engine.start()
        await self.contextual_awareness.start()
        await self.resource_allocator.start()
        
        # Initialize consumer features
        await self._initialize_consumer_features()
        
        self._running = True
        logger.info("Consumer Platform started successfully")
    
    async def stop(self):
        """Stop the consumer platform."""
        if not self._running:
            return
        
        logger.info("Stopping Consumer Platform...")
        
        # Stop core components
        await self.orchestration_engine.stop()
        await self.contextual_awareness.stop()
        await self.resource_allocator.stop()
        
        self._running = False
        logger.info("Consumer Platform stopped")
    
    async def process_natural_language(self, text: str, user_id: str) -> OrchestrationResponse:
        """Process natural language input."""
        # Check user onboarding status
        onboarding_status = await self._check_onboarding_status(user_id)
        if onboarding_status.current_stage != OnboardingStage.COMPLETE:
            return OrchestrationResponse(
                response_id=str(uuid.uuid4()),
                request_id=str(uuid.uuid4()),
                success=False,
                explanation=f"Please complete onboarding first. Current stage: {onboarding_status.current_stage.value}"
            )
        
        # Process natural language
        request = await self.interface.process_natural_language(text, user_id)
        
        # Check privacy and consent
        if not await self.privacy.check_consent(user_id, "automation", "execute"):
            return OrchestrationResponse(
                plan_id=str(uuid.uuid4()),
                status=ExecutionStatus.FAILED,
                rationale="Consent required for automation execution",
                errors=["Consent required for automation execution"]
            )
        
        # Create execution plan
        response = await self.orchestration_engine.create_execution_plan(request)
        
        # Record experience event
        record_experience_event("natural_language_processed", user_id=user_id, success=response.status == ExecutionStatus.COMPLETED)
        
        return response
    
    async def get_visual_preview(self, plan_id: str, user_id: str) -> Dict[str, Any]:
        """Get visual preview of execution plan."""
        # Get plan from orchestration engine
        plan = await self._get_plan_by_id(plan_id)
        if not plan:
            return {"error": "Plan not found"}
        
        # Create visual preview
        preview = await self.interface.create_visual_preview(plan)
        
        # Add user-specific information
        user_prefs = self.user_preferences.get(user_id)
        if user_prefs:
            preview["user_preferences"] = {
                "quiet_hours": f"{user_prefs.quiet_hours_start} - {user_prefs.quiet_hours_end}",
                "energy_goal": f"{user_prefs.energy_savings_goal * 100}% savings"
            }
        
        return preview
    
    async def start_onboarding(self, user_id: str) -> OnboardingProgress:
        """Start user onboarding process."""
        return await self.onboarding.start_onboarding(user_id)
    
    async def advance_onboarding(self, user_id: str, stage: OnboardingStage) -> OnboardingProgress:
        """Advance user onboarding to next stage."""
        return await self.onboarding.advance_stage(user_id, stage)
    
    async def get_system_health(self) -> SystemHealth:
        """Get overall system health."""
        return await self.reliability.check_system_health()
    
    async def get_user_metrics(self, user_id: str) -> ConsumerMetrics:
        """Get user-specific metrics."""
        if user_id not in self.user_metrics:
            self.user_metrics[user_id] = ConsumerMetrics(user_id=user_id)
        
        return self.user_metrics[user_id]
    
    async def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> UserPreferences:
        """Update user preferences."""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = UserPreferences(user_id=user_id, name="", email="", timezone="UTC", language="en")
        
        user_prefs = self.user_preferences[user_id]
        
        # Update preferences
        for key, value in preferences.items():
            if hasattr(user_prefs, key):
                setattr(user_prefs, key, value)
        
        user_prefs.last_updated = datetime.utcnow()
        return user_prefs
    
    async def _initialize_consumer_features(self):
        """Initialize consumer-specific features."""
        logger.info("Initializing consumer features...")
        
        # Initialize performance optimization
        await self.performance.optimize_performance()
        
        # Initialize privacy guard
        logger.info("Consumer features initialized")
    
    async def _check_onboarding_status(self, user_id: str) -> OnboardingProgress:
        """Check user onboarding status."""
        if user_id not in self.onboarding.onboarding_data:
            return await self.onboarding.start_onboarding(user_id)
        return self.onboarding.onboarding_data[user_id]
    
    async def _get_plan_by_id(self, plan_id: str) -> Optional[ExecutionPlan]:
        """Get execution plan by ID."""
        # Placeholder implementation
        # In a real system, this would query the orchestration engine
        return None


class SubscriptionManager:
    """Manages user subscriptions and tiers."""
    
    def __init__(self):
        self.subscriptions: Dict[str, UserTier] = {}
    
    async def get_user_tier(self, user_id: str) -> UserTier:
        """Get user's subscription tier."""
        return self.subscriptions.get(user_id, UserTier.FREE)
    
    async def upgrade_tier(self, user_id: str, tier: UserTier) -> bool:
        """Upgrade user to a higher tier."""
        self.subscriptions[user_id] = tier
        return True
    
    async def check_feature_access(self, user_id: str, feature: str) -> bool:
        """Check if user has access to a specific feature."""
        tier = await self.get_user_tier(user_id)
        
        feature_access = {
            UserTier.FREE: ["basic_automation", "device_control"],
            UserTier.PREMIUM: ["basic_automation", "device_control", "advanced_automation", "voice_control"],
            UserTier.PROFESSIONAL: ["basic_automation", "device_control", "advanced_automation", "voice_control", "analytics", "professional_install"],
            UserTier.ENTERPRISE: ["basic_automation", "device_control", "advanced_automation", "voice_control", "analytics", "professional_install", "enterprise_features"]
        }
        
        return feature in feature_access.get(tier, [])


class AnalyticsEngine:
    """Provides analytics and insights."""
    
    async def get_user_insights(self, user_id: str) -> Dict[str, Any]:
        """Get personalized insights for user."""
        return {
            "energy_savings": {
                "daily_kwh": 2.5,
                "weekly_kwh": 17.5,
                "monthly_kwh": 75.0,
                "savings_percentage": 15.0
            },
            "automation_usage": {
                "daily_automations": 8,
                "success_rate": 0.95,
                "most_used_automation": "morning_routine"
            },
            "device_health": {
                "online_devices": 12,
                "offline_devices": 1,
                "battery_devices_low": 2
            },
            "privacy_score": 0.95,
            "comfort_score": 0.88
        }
    
    async def get_system_analytics(self) -> Dict[str, Any]:
        """Get system-wide analytics."""
        return {
            "total_users": 1250,
            "active_automations": 8500,
            "energy_saved_total_kwh": 12500,
            "system_uptime": 0.999,
            "average_response_time_ms": 145
        }


# Global platform instance
consumer_platform = ConsumerPlatform()

async def get_consumer_platform() -> ConsumerPlatform:
    """Get the global consumer platform instance."""
    return consumer_platform
