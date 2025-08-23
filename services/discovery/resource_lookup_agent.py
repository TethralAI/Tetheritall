"""
Resource Lookup Agent (RLA)

ML-focused agent that finds and distills everything needed to connect a user's devices and services.
Implements entity linking, RAG over docs, flow planning, troubleshooting, and consent reasoning.

Goal: Get the user from "I own X" to "X is ready to connect" with the fewest steps and highest success rate.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Set
from enum import Enum
import json
import re
from pathlib import Path

from pydantic import BaseModel, Field
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from shared.config.policy import ConsentPolicy
from shared.database.api_database import get_session_factory, session_scope
from shared.database.models import Device, ApiEndpoint, ScanResult


logger = logging.getLogger(__name__)


class TriggerType(Enum):
    FIRST_RUN = "first_run"
    DEVICE_DECLARATION = "device_declaration"
    DEVICE_SCAN = "device_scan"
    FAILED_CONNECTION = "failed_connection"
    TROUBLESHOOTING = "troubleshooting"


class PrivacyTier(Enum):
    MINIMAL = "minimal"  # Local only, no cloud
    STANDARD = "standard"  # Basic cloud features
    ENHANCED = "enhanced"  # Full cloud integration


class DeviceHint(BaseModel):
    """Input hints for device identification."""
    brand: Optional[str] = None
    model: Optional[str] = None
    qr_code: Optional[str] = None
    mac_address: Optional[str] = None
    ble_advertisement: Optional[Dict[str, Any]] = None
    matter_code: Optional[str] = None
    serial_number: Optional[str] = None
    firmware_version: Optional[str] = None


class AccountHint(BaseModel):
    """Input hints for account/provider information."""
    provider: Optional[str] = None
    region: Optional[str] = None
    auth_capability: Optional[str] = None  # oauth, api_key, username_password, etc.
    existing_accounts: List[str] = Field(default_factory=list)


class EnvironmentContext(BaseModel):
    """Environment information for connection planning."""
    ssid: Optional[str] = None
    band: Optional[str] = None  # 2.4GHz, 5GHz, 6GHz
    dhcp_enabled: bool = True
    nat_type: Optional[str] = None
    ipv6_available: bool = False
    thread_border_router: bool = False
    matter_commissioning_available: bool = False
    bluetooth_available: bool = False
    wifi_6_available: bool = False


class UserPreferences(BaseModel):
    """User preferences for connection flow."""
    privacy_tier: PrivacyTier = PrivacyTier.STANDARD
    approval_threshold: str = "manual"  # auto, manual, confirm
    quiet_hours: Tuple[int, int] = (22, 7)  # (start_hour, end_hour)
    noise_sensitivity: bool = False
    night_mode: bool = False
    max_steps_per_session: int = 10
    preferred_protocols: List[str] = Field(default_factory=list)


@dataclass
class EntityProfile:
    """Normalized device entity profile."""
    canonical_device_id: str
    brand_normalized: str
    model_normalized: str
    capability_class: str
    candidate_protocols: List[str]
    confidence_score: float
    known_issues: List[str] = field(default_factory=list)
    recommended_flow: Optional[str] = None


@dataclass
class ProviderProfile:
    """Provider-specific connection information."""
    provider_name: str
    oauth_scopes: List[str]
    two_fa_patterns: List[str]
    rate_limits: Dict[str, Any]
    typical_errors: Dict[str, str]
    api_endpoints: List[str]
    documentation_urls: List[str]


@dataclass
class FlowStep:
    """Individual step in a connection flow."""
    step_id: str
    description: str
    action_type: str  # tap, scan, enter, approve, wait
    estimated_time_seconds: int
    prerequisites: List[str]
    expected_outcome: str
    failure_handlers: List[str]
    privacy_impact: Dict[str, Any]
    success_probability: float


@dataclass
class ConnectionFlow:
    """Complete connection flow for a device."""
    flow_id: str
    device_id: str
    steps: List[FlowStep]
    total_estimated_time: int
    success_probability: float
    privacy_cost: float
    effort_score: float
    readiness_score: float
    alternative_flows: List[str] = field(default_factory=list)


@dataclass
class ConsentScope:
    """Consent scope with privacy notes."""
    scope: str
    description: str
    privacy_impact: str
    least_privilege_alternative: Optional[str] = None
    required: bool = False
    recommended: bool = True


class EntityLinker:
    """Entity linking and normalization model."""
    
    def __init__(self):
        self.brand_aliases = {
            "philips": ["philips", "signify", "hue"],
            "ikea": ["ikea", "tradfri"],
            "samsung": ["samsung", "smartthings"],
            "apple": ["apple", "homekit"],
            "google": ["google", "nest"],
            "amazon": ["amazon", "alexa", "ring"],
        }
        self.model_patterns = {
            "light_bulb": r"(bulb|light|lamp|led)",
            "switch": r"(switch|outlet|plug|socket)",
            "sensor": r"(sensor|detector|monitor)",
            "camera": r"(camera|cam|security)",
            "thermostat": r"(thermostat|temp|climate)",
        }
        
    def normalize_entity(self, device_hint: DeviceHint) -> EntityProfile:
        """Normalize device hints into canonical entity profile."""
        brand = self._normalize_brand(device_hint.brand or "")
        model = self._normalize_model(device_hint.model or "")
        capability_class = self._classify_capability(brand, model)
        protocols = self._identify_protocols(device_hint, brand, model)
        
        return EntityProfile(
            canonical_device_id=f"{brand}_{model}_{capability_class}",
            brand_normalized=brand,
            model_normalized=model,
            capability_class=capability_class,
            candidate_protocols=protocols,
            confidence_score=self._calculate_confidence(device_hint),
        )
    
    def _normalize_brand(self, brand: str) -> str:
        """Normalize brand name using aliases."""
        brand_lower = brand.lower().strip()
        for canonical, aliases in self.brand_aliases.items():
            if brand_lower in aliases:
                return canonical
        return brand_lower
    
    def _normalize_model(self, model: str) -> str:
        """Normalize model string."""
        return re.sub(r'[^a-zA-Z0-9]', '_', model.lower().strip())
    
    def _classify_capability(self, brand: str, model: str) -> str:
        """Classify device capability based on brand and model."""
        text = f"{brand} {model}".lower()
        for capability, pattern in self.model_patterns.items():
            if re.search(pattern, text):
                return capability
        return "unknown"
    
    def _identify_protocols(self, device_hint: DeviceHint, brand: str, model: str) -> List[str]:
        """Identify candidate protocols based on device hints."""
        protocols = []
        
        if device_hint.matter_code:
            protocols.append("matter")
        if device_hint.ble_advertisement:
            protocols.append("bluetooth")
        if device_hint.qr_code:
            protocols.extend(["wifi", "zigbee", "thread"])
        
        # Brand-specific protocol hints
        brand_protocols = {
            "philips": ["hue", "zigbee"],
            "ikea": ["zigbee", "thread"],
            "samsung": ["wifi", "zigbee", "thread"],
            "apple": ["homekit", "bluetooth"],
            "google": ["wifi", "thread"],
            "amazon": ["wifi", "zigbee"],
        }
        
        if brand in brand_protocols:
            protocols.extend(brand_protocols[brand])
        
        return list(set(protocols))
    
    def _calculate_confidence(self, device_hint: DeviceHint) -> float:
        """Calculate confidence score based on available hints."""
        confidence = 0.0
        if device_hint.brand and device_hint.model:
            confidence += 0.4
        if device_hint.qr_code:
            confidence += 0.3
        if device_hint.mac_address:
            confidence += 0.2
        if device_hint.ble_advertisement:
            confidence += 0.1
        return min(confidence, 1.0)


class DocumentationRAG:
    """RAG system for documentation and community fixes."""
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.document_embeddings = {}
        self.documents = []
        
    async def load_knowledge_base(self, device_id: str) -> None:
        """Load relevant documentation for device."""
        # TODO: Implement actual document loading from various sources
        # For now, using mock data
        mock_docs = [
            "To connect Philips Hue bulb, press the bridge button within 30 seconds",
            "IKEA Tradfri bulbs require the gateway for remote control",
            "Samsung SmartThings devices can connect via WiFi or Zigbee",
            "Apple HomeKit devices need iOS device for setup",
        ]
        
        self.documents = mock_docs
        if self.documents:
            self.document_embeddings = self.vectorizer.fit_transform(self.documents)
    
    def extract_steps(self, query: str, max_steps: int = 5) -> List[Dict[str, Any]]:
        """Extract actionable steps from documentation."""
        if not self.documents:
            return []
        
        query_vector = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vector, self.document_embeddings)[0]
        
        # Get top relevant documents
        top_indices = np.argsort(similarities)[-max_steps:][::-1]
        
        steps = []
        for idx in top_indices:
            if similarities[idx] > 0.1:  # Threshold for relevance
                steps.append({
                    "step": self.documents[idx],
                    "relevance": float(similarities[idx]),
                    "source": "documentation"
                })
        
        return steps


class FlowPlanner:
    """Policy-aware flow planner that builds personalized step graphs."""
    
    def __init__(self):
        self.flow_templates = {}
        self._load_flow_templates()
    
    def _load_flow_templates(self):
        """Load flow templates for different device types."""
        self.flow_templates = {
            "philips_hue": [
                FlowStep("check_bridge", "Ensure Hue Bridge is powered and connected", "check", 5, [], "Bridge found", ["manual_bridge_setup"], {"data_collected": False}, 0.9),
                FlowStep("press_button", "Press the button on your Hue Bridge", "tap", 30, ["check_bridge"], "Bridge button pressed", ["retry_button"], {"data_collected": False}, 0.8),
                FlowStep("add_bulb", "Add your Hue bulb to the bridge", "tap", 60, ["press_button"], "Bulb added successfully", ["manual_bulb_add"], {"data_collected": True}, 0.7),
            ],
            "ikea_tradfri": [
                FlowStep("check_gateway", "Ensure Tradfri Gateway is connected", "check", 5, [], "Gateway found", ["manual_gateway_setup"], {"data_collected": False}, 0.9),
                FlowStep("add_remote", "Add Tradfri remote control", "tap", 45, ["check_gateway"], "Remote added", ["manual_remote_add"], {"data_collected": False}, 0.8),
                FlowStep("add_bulb", "Add bulb using the remote", "tap", 60, ["add_remote"], "Bulb added successfully", ["manual_bulb_add"], {"data_collected": True}, 0.7),
            ],
        }
    
    def plan_flow(self, entity_profile: EntityProfile, env_context: EnvironmentContext, 
                  user_prefs: UserPreferences) -> ConnectionFlow:
        """Plan personalized connection flow."""
        template_key = f"{entity_profile.brand_normalized}_{entity_profile.capability_class}"
        base_steps = self.flow_templates.get(template_key, [])
        
        # Customize steps based on environment and preferences
        customized_steps = self._customize_steps(base_steps, env_context, user_prefs)
        
        # Calculate metrics
        total_time = sum(step.estimated_time_seconds for step in customized_steps)
        success_prob = np.mean([step.success_probability for step in customized_steps])
        privacy_cost = self._calculate_privacy_cost(customized_steps, user_prefs.privacy_tier)
        effort_score = self._calculate_effort_score(customized_steps)
        readiness_score = self._calculate_readiness_score(customized_steps, env_context)
        
        return ConnectionFlow(
            flow_id=f"flow_{entity_profile.canonical_device_id}_{datetime.now().timestamp()}",
            device_id=entity_profile.canonical_device_id,
            steps=customized_steps,
            total_estimated_time=total_time,
            success_probability=success_prob,
            privacy_cost=privacy_cost,
            effort_score=effort_score,
            readiness_score=readiness_score,
        )
    
    def _customize_steps(self, steps: List[FlowStep], env_context: EnvironmentContext, 
                        user_prefs: UserPreferences) -> List[FlowStep]:
        """Customize steps based on environment and user preferences."""
        customized = []
        for step in steps:
            # Adjust time estimates based on user preferences
            if user_prefs.noise_sensitivity and "tap" in step.action_type:
                step.estimated_time_seconds += 10
            
            # Add environment-specific prerequisites
            if "wifi" in step.description.lower() and not env_context.wifi_6_available:
                step.prerequisites.append("wifi_network_available")
            
            customized.append(step)
        
        return customized
    
    def _calculate_privacy_cost(self, steps: List[FlowStep], privacy_tier: PrivacyTier) -> float:
        """Calculate privacy cost based on steps and privacy tier."""
        base_cost = sum(step.privacy_impact.get("data_collected", False) for step in steps)
        
        # Adjust based on privacy tier
        tier_multipliers = {
            PrivacyTier.MINIMAL: 0.5,
            PrivacyTier.STANDARD: 1.0,
            PrivacyTier.ENHANCED: 1.5,
        }
        
        return base_cost * tier_multipliers[privacy_tier]
    
    def _calculate_effort_score(self, steps: List[FlowStep]) -> float:
        """Calculate effort score based on steps."""
        total_time = sum(step.estimated_time_seconds for step in steps)
        num_taps = sum(1 for step in steps if "tap" in step.action_type)
        
        # Normalize: 0 = low effort, 1 = high effort
        time_score = min(total_time / 300, 1.0)  # 5 minutes = max effort
        tap_score = min(num_taps / 10, 1.0)  # 10 taps = max effort
        
        return (time_score + tap_score) / 2
    
    def _calculate_readiness_score(self, steps: List[FlowStep], env_context: EnvironmentContext) -> float:
        """Calculate readiness score based on environment."""
        readiness = 1.0
        
        # Check environment prerequisites
        if any("wifi" in step.description.lower() for step in steps) and not env_context.ssid:
            readiness *= 0.5
        
        if any("bluetooth" in step.description.lower() for step in steps) and not env_context.bluetooth_available:
            readiness *= 0.3
        
        return readiness


class TroubleshootClassifier:
    """Multi-label classifier for troubleshooting."""
    
    def __init__(self):
        self.error_patterns = {
            "network_issue": [
                "connection timeout", "network unreachable", "dns resolution failed",
                "wifi password incorrect", "ssid not found"
            ],
            "authentication_failure": [
                "invalid credentials", "unauthorized", "access denied",
                "authentication failed", "login failed"
            ],
            "device_not_found": [
                "device not found", "device offline", "device not responding",
                "no device detected", "scan failed"
            ],
            "protocol_mismatch": [
                "unsupported protocol", "protocol error", "incompatible version",
                "handshake failed", "protocol negotiation failed"
            ],
            "permission_denied": [
                "permission denied", "insufficient privileges", "access restricted",
                "user not authorized", "scope required"
            ]
        }
        
    def classify_error(self, error_message: str, context: Dict[str, Any]) -> List[Tuple[str, float]]:
        """Classify error and return likely causes with confidence scores."""
        error_lower = error_message.lower()
        classifications = []
        
        for error_type, patterns in self.error_patterns.items():
            confidence = 0.0
            for pattern in patterns:
                if pattern in error_lower:
                    confidence += 0.3
            
            # Boost confidence based on context
            if error_type == "network_issue" and context.get("network_scan_failed"):
                confidence += 0.2
            elif error_type == "authentication_failure" and context.get("auth_attempted"):
                confidence += 0.2
            
            if confidence > 0:
                classifications.append((error_type, min(confidence, 1.0)))
        
        # Sort by confidence
        classifications.sort(key=lambda x: x[1], reverse=True)
        return classifications[:3]  # Top 3 causes
    
    def get_fixes(self, error_type: str) -> List[Dict[str, Any]]:
        """Get fixes for a specific error type."""
        fixes = {
            "network_issue": [
                {"fix": "Check WiFi password and connection", "effort": "low", "success_rate": 0.8},
                {"fix": "Restart router and device", "effort": "medium", "success_rate": 0.6},
                {"fix": "Check firewall settings", "effort": "high", "success_rate": 0.4},
            ],
            "authentication_failure": [
                {"fix": "Verify username and password", "effort": "low", "success_rate": 0.7},
                {"fix": "Reset device to factory settings", "effort": "medium", "success_rate": 0.5},
                {"fix": "Contact manufacturer support", "effort": "high", "success_rate": 0.3},
            ],
            "device_not_found": [
                {"fix": "Ensure device is powered on", "effort": "low", "success_rate": 0.9},
                {"fix": "Move device closer to hub/router", "effort": "low", "success_rate": 0.7},
                {"fix": "Check device compatibility", "effort": "medium", "success_rate": 0.5},
            ],
        }
        
        return fixes.get(error_type, [])


class ConsentReasoner:
    """Rule-plus-ML system for consent scope reasoning."""
    
    def __init__(self):
        self.scope_catalog = self._load_scope_catalog()
        
    def _load_scope_catalog(self) -> Dict[str, Dict[str, Any]]:
        """Load scope catalog with privacy information."""
        return {
            "read_devices": {
                "description": "Read device information and status",
                "privacy_impact": "Low - only reads device data you own",
                "least_privilege_alternative": None,
                "required": True,
            },
            "write_devices": {
                "description": "Control and configure devices",
                "privacy_impact": "Medium - can change device settings",
                "least_privilege_alternative": "read_devices",
                "required": False,
            },
            "read_location": {
                "description": "Access device location information",
                "privacy_impact": "High - reveals device locations",
                "least_privilege_alternative": None,
                "required": False,
            },
            "read_usage": {
                "description": "Access device usage statistics",
                "privacy_impact": "Medium - reveals usage patterns",
                "least_privilege_alternative": None,
                "required": False,
            },
        }
    
    def determine_required_scopes(self, desired_capabilities: List[str], 
                                privacy_tier: PrivacyTier) -> List[ConsentScope]:
        """Determine required scopes based on desired capabilities."""
        required_scopes = []
        
        capability_scope_mapping = {
            "read_status": ["read_devices"],
            "control_device": ["read_devices", "write_devices"],
            "location_based_automation": ["read_devices", "read_location"],
            "usage_analytics": ["read_devices", "read_usage"],
        }
        
        for capability in desired_capabilities:
            if capability in capability_scope_mapping:
                scopes = capability_scope_mapping[capability]
                for scope in scopes:
                    scope_info = self.scope_catalog[scope]
                    
                    # Apply privacy tier restrictions
                    if privacy_tier == PrivacyTier.MINIMAL and scope in ["read_location", "read_usage"]:
                        continue
                    
                    consent_scope = ConsentScope(
                        scope=scope,
                        description=scope_info["description"],
                        privacy_impact=scope_info["privacy_impact"],
                        least_privilege_alternative=scope_info["least_privilege_alternative"],
                        required=scope_info["required"],
                        recommended=privacy_tier != PrivacyTier.MINIMAL,
                    )
                    required_scopes.append(consent_scope)
        
        return required_scopes


class ResourceLookupAgent:
    """Main Resource Lookup Agent implementation."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.entity_linker = EntityLinker()
        self.documentation_rag = DocumentationRAG()
        self.flow_planner = FlowPlanner()
        self.troubleshoot_classifier = TroubleshootClassifier()
        self.consent_reasoner = ConsentReasoner()
        self._session_factory = get_session_factory(self.config.get("database_url", "sqlite:///./iot_discovery.db"))
        
        # Internal state
        self.device_profiles: Dict[str, EntityProfile] = {}
        self.provider_profiles: Dict[str, ProviderProfile] = {}
        self.user_progress: Dict[str, Dict[str, Any]] = {}
        self.consent_ledger: Dict[str, List[str]] = {}
        
    async def process_device_hint(self, 
                                device_hint: DeviceHint,
                                account_hint: Optional[AccountHint] = None,
                                env_context: Optional[EnvironmentContext] = None,
                                user_prefs: Optional[UserPreferences] = None,
                                trigger: TriggerType = TriggerType.DEVICE_DECLARATION) -> Dict[str, Any]:
        """Main entry point for processing device hints."""
        
        # Step 1: Entity linking and normalization
        entity_profile = self.entity_linker.normalize_entity(device_hint)
        self.device_profiles[entity_profile.canonical_device_id] = entity_profile
        
        # Step 2: Load documentation knowledge base
        await self.documentation_rag.load_knowledge_base(entity_profile.canonical_device_id)
        
        # Step 3: Extract actionable steps from documentation
        query = f"how to connect {entity_profile.brand_normalized} {entity_profile.model_normalized}"
        documentation_steps = self.documentation_rag.extract_steps(query)
        
        # Step 4: Plan connection flow
        env_context = env_context or EnvironmentContext()
        user_prefs = user_prefs or UserPreferences()
        connection_flow = self.flow_planner.plan_flow(entity_profile, env_context, user_prefs)
        
        # Step 5: Determine consent scopes
        desired_capabilities = self._infer_capabilities(entity_profile)
        consent_scopes = self.consent_reasoner.determine_required_scopes(
            desired_capabilities, user_prefs.privacy_tier
        )
        
        # Step 6: Generate step-by-step checklist
        checklist = self._generate_checklist(connection_flow, documentation_steps, consent_scopes)
        
        # Step 7: Calculate scores
        scores = self._calculate_scores(connection_flow, consent_scopes, user_prefs)
        
        return {
            "entity_profile": entity_profile,
            "connection_flow": connection_flow,
            "documentation_steps": documentation_steps,
            "consent_scopes": consent_scopes,
            "checklist": checklist,
            "scores": scores,
            "recommendations": self._generate_recommendations(scores, user_prefs),
        }
    
    def _infer_capabilities(self, entity_profile: EntityProfile) -> List[str]:
        """Infer desired capabilities based on device type."""
        capability_mapping = {
            "light_bulb": ["read_status", "control_device"],
            "switch": ["read_status", "control_device"],
            "sensor": ["read_status"],
            "camera": ["read_status", "control_device", "location_based_automation"],
            "thermostat": ["read_status", "control_device", "usage_analytics"],
        }
        
        return capability_mapping.get(entity_profile.capability_class, ["read_status"])
    
    def _generate_checklist(self, flow: ConnectionFlow, doc_steps: List[Dict[str, Any]], 
                           consent_scopes: List[ConsentScope]) -> Dict[str, Any]:
        """Generate step-by-step checklist."""
        checklist = {
            "preflight_checks": self._generate_preflight_checks(flow),
            "connection_steps": [
                {
                    "step_id": step.step_id,
                    "description": step.description,
                    "estimated_time": step.estimated_time_seconds,
                    "action_type": step.action_type,
                    "prerequisites": step.prerequisites,
                    "expected_outcome": step.expected_outcome,
                }
                for step in flow.steps
            ],
            "consent_requirements": [
                {
                    "scope": scope.scope,
                    "description": scope.description,
                    "privacy_impact": scope.privacy_impact,
                    "required": scope.required,
                    "recommended": scope.recommended,
                }
                for scope in consent_scopes
            ],
            "documentation_references": doc_steps,
        }
        
        return checklist
    
    def _generate_preflight_checks(self, flow: ConnectionFlow) -> List[Dict[str, Any]]:
        """Generate preflight checks for the flow."""
        checks = []
        
        # Environment checks
        checks.append({
            "check": "Network connectivity",
            "description": "Ensure stable internet connection",
            "critical": True,
        })
        
        checks.append({
            "check": "Device power",
            "description": "Ensure device is powered on and ready",
            "critical": True,
        })
        
        # Protocol-specific checks
        if any("bluetooth" in step.description.lower() for step in flow.steps):
            checks.append({
                "check": "Bluetooth availability",
                "description": "Ensure Bluetooth is enabled and available",
                "critical": True,
            })
        
        return checks
    
    def _calculate_scores(self, flow: ConnectionFlow, consent_scopes: List[ConsentScope], 
                         user_prefs: UserPreferences) -> Dict[str, float]:
        """Calculate various scores for the connection attempt."""
        return {
            "effort_score": flow.effort_score,
            "readiness_score": flow.readiness_score,
            "success_probability": flow.success_probability,
            "privacy_cost": flow.privacy_cost,
            "user_comfort": self._calculate_user_comfort(flow, user_prefs),
        }
    
    def _calculate_user_comfort(self, flow: ConnectionFlow, user_prefs: UserPreferences) -> float:
        """Calculate user comfort score."""
        comfort = 1.0
        
        # Reduce comfort for noisy operations during quiet hours
        current_hour = datetime.now().hour
        if user_prefs.quiet_hours[0] <= current_hour <= user_prefs.quiet_hours[1]:
            if any("tap" in step.action_type for step in flow.steps):
                comfort *= 0.7
        
        # Reduce comfort for high effort flows
        if flow.effort_score > 0.8:
            comfort *= 0.8
        
        return comfort
    
    def _generate_recommendations(self, scores: Dict[str, float], 
                                user_prefs: UserPreferences) -> List[str]:
        """Generate recommendations based on scores."""
        recommendations = []
        
        if scores["readiness_score"] < 0.5:
            recommendations.append("Check network connectivity and device power before starting")
        
        if scores["effort_score"] > 0.8:
            recommendations.append("Consider breaking this into smaller sessions")
        
        if scores["privacy_cost"] > 0.7 and user_prefs.privacy_tier == PrivacyTier.MINIMAL:
            recommendations.append("Consider using local-only connection methods")
        
        if scores["user_comfort"] < 0.6:
            recommendations.append("Consider scheduling this for a better time")
        
        return recommendations
    
    async def troubleshoot_failure(self, error_message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Troubleshoot connection failures."""
        # Classify the error
        error_causes = self.troubleshoot_classifier.classify_error(error_message, context)
        
        # Get fixes for each cause
        all_fixes = []
        for error_type, confidence in error_causes:
            fixes = self.troubleshoot_classifier.get_fixes(error_type)
            for fix in fixes:
                fix["error_type"] = error_type
                fix["confidence"] = confidence
                all_fixes.append(fix)
        
        # Sort fixes by success rate and effort
        all_fixes.sort(key=lambda x: (x["success_rate"], -self._effort_to_score(x["effort"])), reverse=True)
        
        return {
            "error_causes": error_causes,
            "recommended_fixes": all_fixes[:5],  # Top 5 fixes
            "next_steps": self._generate_troubleshoot_steps(all_fixes),
        }
    
    def _effort_to_score(self, effort: str) -> float:
        """Convert effort string to numeric score."""
        effort_scores = {"low": 1.0, "medium": 0.5, "high": 0.0}
        return effort_scores.get(effort, 0.5)
    
    def _generate_troubleshoot_steps(self, fixes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate troubleshooting steps."""
        steps = []
        
        for i, fix in enumerate(fixes[:3]):  # Top 3 fixes
            steps.append({
                "step_number": i + 1,
                "action": fix["fix"],
                "expected_outcome": f"Resolves {fix['error_type']} issue",
                "estimated_time": 60 if fix["effort"] == "low" else 120,
                "success_probability": fix["success_rate"],
            })
        
        return steps
    
    async def record_step_completion(self, device_id: str, step_id: str, 
                                   success: bool, time_taken: int, 
                                   user_feedback: Optional[str] = None) -> None:
        """Record step completion for learning."""
        if device_id not in self.user_progress:
            self.user_progress[device_id] = {"steps": {}, "feedback": []}
        
        self.user_progress[device_id]["steps"][step_id] = {
            "success": success,
            "time_taken": time_taken,
            "timestamp": datetime.now().isoformat(),
        }
        
        if user_feedback:
            self.user_progress[device_id]["feedback"].append({
                "step_id": step_id,
                "feedback": user_feedback,
                "timestamp": datetime.now().isoformat(),
            })
        
        # TODO: Persist to database for long-term learning
        logger.info(f"Recorded step completion: {device_id}/{step_id} - success={success}")
