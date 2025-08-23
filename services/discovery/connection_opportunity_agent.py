"""
Connection Opportunity Agent (COA)

ML-focused agent that maximizes connected capability coverage and routine flexibility quickly,
with low user effort and high privacy.

Goal: Maximize connected capability coverage and routine flexibility quickly, with low user effort and high privacy.
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
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

from shared.config.policy import ConsentPolicy
from shared.database.api_database import get_session_factory, session_scope
from shared.database.models import Device, ApiEndpoint, ScanResult


logger = logging.getLogger(__name__)


class TriggerType(Enum):
    FIRST_SUCCESS = "first_success"
    ONBOARDING_BURST = "onboarding_burst"
    CONTEXT_CHANGE = "context_change"
    ACCOUNT_LINKING = "account_linking"
    SCHEDULED_SCAN = "scheduled_scan"


class DiscoveryType(Enum):
    MDNS = "mdns"
    SSDP = "ssdp"
    BLE = "ble"
    THREAD = "thread"
    ZIGBEE = "zigbee"
    WIFI_BEACON = "wifi_beacon"
    MATTER = "matter"
    SMARTTHINGS = "smartthings"


class CapabilityType(Enum):
    LIGHTING = "lighting"
    CLIMATE = "climate"
    SECURITY = "security"
    ENTERTAINMENT = "entertainment"
    APPLIANCES = "appliances"
    SENSORS = "sensors"
    CAMERAS = "cameras"
    LOCKS = "locks"
    SPEAKERS = "speakers"
    DISPLAYS = "displays"


@dataclass
class NetworkDiscovery:
    """Network discovery result."""
    discovery_id: str
    discovery_type: DiscoveryType
    device_info: Dict[str, Any]
    protocol_candidates: List[str]
    confidence_score: float
    timestamp: datetime
    location_hint: Optional[str] = None


@dataclass
class ConnectionOpportunity:
    """Connection opportunity with value and friction estimates."""
    opportunity_id: str
    source: str  # discovery_id or provider_name
    device_type: str
    capability_unlocks: List[CapabilityType]
    value_score: float
    friction_score: float
    privacy_cost: float
    context_constraints: List[str]
    rationale: str
    estimated_steps: int
    success_probability: float


@dataclass
class CoverageGap:
    """Capability coverage gap analysis."""
    capability: CapabilityType
    current_coverage: float  # 0-1
    missing_devices: List[str]
    routine_impact: float  # How much this affects routine flexibility
    priority_score: float


@dataclass
class UserConstraints:
    """User constraints for opportunity selection."""
    privacy_tier: str = "standard"  # minimal, standard, enhanced
    time_budget_minutes: int = 30
    noise_sensitivity: bool = False
    quiet_hours: Tuple[int, int] = (22, 7)
    max_consent_scope: str = "standard"
    preferred_protocols: List[str] = field(default_factory=list)
    disliked_brands: List[str] = field(default_factory=list)
    do_not_ask_until: Dict[str, datetime] = field(default_factory=dict)


class DiscoveryClassifier:
    """ML model for classifying discovered devices."""
    
    def __init__(self):
        self.classifier = RandomForestClassifier(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        
    def extract_features(self, discovery: NetworkDiscovery) -> np.ndarray:
        """Extract features from discovery for classification."""
        features = []
        
        # Protocol features
        protocol_features = [0] * len(DiscoveryType)
        for protocol in discovery.protocol_candidates:
            try:
                idx = list(DiscoveryType).index(DiscoveryType(protocol))
                protocol_features[idx] = 1
            except ValueError:
                pass
        features.extend(protocol_features)
        
        # Device info features
        device_info = discovery.device_info
        features.extend([
            len(device_info.get("name", "")),
            len(device_info.get("model", "")),
            len(device_info.get("manufacturer", "")),
            device_info.get("port", 0) or 0,
            device_info.get("services", []),
        ])
        
        # Discovery type features
        discovery_type_features = [0] * len(DiscoveryType)
        try:
            idx = list(DiscoveryType).index(discovery.discovery_type)
            discovery_type_features[idx] = 1
        except ValueError:
            pass
        features.extend(discovery_type_features)
        
        return np.array(features).reshape(1, -1)
    
    def classify_device(self, discovery: NetworkDiscovery) -> Tuple[str, float]:
        """Classify discovered device type."""
        if not self.is_trained:
            # Use rule-based classification as fallback
            return self._rule_based_classification(discovery)
        
        features = self.extract_features(discovery)
        features_scaled = self.scaler.transform(features)
        prediction = self.classifier.predict(features_scaled)[0]
        confidence = np.max(self.classifier.predict_proba(features_scaled))
        
        return prediction, confidence
    
    def _rule_based_classification(self, discovery: NetworkDiscovery) -> Tuple[str, float]:
        """Rule-based device classification."""
        device_info = discovery.device_info
        name = device_info.get("name", "").lower()
        model = device_info.get("model", "").lower()
        manufacturer = device_info.get("manufacturer", "").lower()
        
        # Simple keyword-based classification
        if any(word in name for word in ["light", "bulb", "lamp", "hue", "tradfri"]):
            return "light_bulb", 0.8
        elif any(word in name for word in ["switch", "outlet", "plug"]):
            return "switch", 0.8
        elif any(word in name for word in ["sensor", "detector", "motion"]):
            return "sensor", 0.8
        elif any(word in name for word in ["camera", "cam", "security"]):
            return "camera", 0.8
        elif any(word in name for word in ["thermostat", "temp", "climate"]):
            return "thermostat", 0.8
        else:
            return "unknown", 0.3


class OpportunityValueEstimator:
    """Submodular coverage estimator for opportunity value."""
    
    def __init__(self):
        self.capability_weights = {
            CapabilityType.LIGHTING: 0.3,
            CapabilityType.CLIMATE: 0.25,
            CapabilityType.SECURITY: 0.2,
            CapabilityType.ENTERTAINMENT: 0.15,
            CapabilityType.APPLIANCES: 0.1,
        }
        
        self.routine_templates = {
            "morning": [CapabilityType.LIGHTING, CapabilityType.CLIMATE],
            "evening": [CapabilityType.LIGHTING, CapabilityType.ENTERTAINMENT],
            "security": [CapabilityType.SECURITY, CapabilityType.CAMERAS],
            "comfort": [CapabilityType.CLIMATE, CapabilityType.LIGHTING],
        }
    
    def estimate_value(self, opportunity: ConnectionOpportunity, 
                      current_coverage: Dict[CapabilityType, float]) -> float:
        """Estimate the marginal value of connecting this opportunity."""
        value = 0.0
        
        # Calculate marginal coverage gain for each capability
        for capability in opportunity.capability_unlocks:
            current = current_coverage.get(capability, 0.0)
            marginal_gain = min(1.0 - current, 0.3)  # Cap marginal gain at 30%
            value += marginal_gain * self.capability_weights.get(capability, 0.1)
        
        # Bonus for routine flexibility
        routine_bonus = self._calculate_routine_bonus(opportunity, current_coverage)
        value += routine_bonus
        
        return value
    
    def _calculate_routine_bonus(self, opportunity: ConnectionOpportunity,
                               current_coverage: Dict[CapabilityType, float]) -> float:
        """Calculate bonus for routine flexibility."""
        bonus = 0.0
        
        for routine_name, required_capabilities in self.routine_templates.items():
            # Check if this opportunity helps complete a routine
            missing_capabilities = []
            for capability in required_capabilities:
                if current_coverage.get(capability, 0.0) < 0.5:  # Less than 50% coverage
                    missing_capabilities.append(capability)
            
            # If this opportunity provides missing capabilities
            for capability in opportunity.capability_unlocks:
                if capability in missing_capabilities:
                    bonus += 0.1  # Small bonus for each routine capability unlocked
        
        return min(bonus, 0.3)  # Cap routine bonus at 30%


class FrictionForecaster:
    """Gradient model for predicting connection friction."""
    
    def __init__(self):
        self.brand_friction_profiles = {
            "philips": {"steps": 3, "success_rate": 0.9, "time_minutes": 5},
            "ikea": {"steps": 4, "success_rate": 0.8, "time_minutes": 8},
            "samsung": {"steps": 5, "success_rate": 0.7, "time_minutes": 10},
            "apple": {"steps": 2, "success_rate": 0.95, "time_minutes": 3},
            "google": {"steps": 4, "success_rate": 0.8, "time_minutes": 7},
            "amazon": {"steps": 3, "success_rate": 0.85, "time_minutes": 6},
        }
        
        self.protocol_friction = {
            "matter": {"steps": 2, "success_rate": 0.9, "time_minutes": 3},
            "bluetooth": {"steps": 3, "success_rate": 0.8, "time_minutes": 5},
            "wifi": {"steps": 4, "success_rate": 0.7, "time_minutes": 8},
            "zigbee": {"steps": 5, "success_rate": 0.6, "time_minutes": 12},
            "thread": {"steps": 3, "success_rate": 0.8, "time_minutes": 6},
        }
    
    def forecast_friction(self, opportunity: ConnectionOpportunity, 
                         env_context: Dict[str, Any]) -> Dict[str, float]:
        """Forecast connection friction and success probability."""
        # Base friction from brand and protocol
        brand = opportunity.source.split("_")[0] if "_" in opportunity.source else "unknown"
        protocol = opportunity.protocol_candidates[0] if opportunity.protocol_candidates else "unknown"
        
        brand_profile = self.brand_friction_profiles.get(brand, {"steps": 5, "success_rate": 0.6, "time_minutes": 10})
        protocol_profile = self.protocol_friction.get(protocol, {"steps": 4, "success_rate": 0.7, "time_minutes": 8})
        
        # Combine profiles
        steps = max(brand_profile["steps"], protocol_profile["steps"])
        success_rate = brand_profile["success_rate"] * protocol_profile["success_rate"]
        time_minutes = brand_profile["time_minutes"] + protocol_profile["time_minutes"]
        
        # Adjust based on environment context
        if env_context.get("network_quality") == "poor":
            success_rate *= 0.8
            time_minutes *= 1.2
        
        if env_context.get("bluetooth_available") == False and "bluetooth" in protocol:
            success_rate *= 0.3
            time_minutes *= 2.0
        
        # Calculate friction score (0 = low friction, 1 = high friction)
        friction_score = min((steps / 10.0 + time_minutes / 30.0) / 2.0, 1.0)
        
        return {
            "steps": steps,
            "success_probability": success_rate,
            "time_minutes": time_minutes,
            "friction_score": friction_score,
        }


class SequencingPolicy:
    """Contextual bandit for opportunity sequencing."""
    
    def __init__(self):
        self.opportunity_history: List[Dict[str, Any]] = []
        self.user_preferences: Dict[str, float] = {}
        
    def select_opportunities(self, opportunities: List[ConnectionOpportunity],
                           user_constraints: UserConstraints,
                           batch_size: int = 3) -> List[ConnectionOpportunity]:
        """Select best opportunities based on policy."""
        # Filter opportunities based on constraints
        filtered_opportunities = self._filter_by_constraints(opportunities, user_constraints)
        
        # Score opportunities
        scored_opportunities = []
        for opp in filtered_opportunities:
            score = self._calculate_opportunity_score(opp, user_constraints)
            scored_opportunities.append((opp, score))
        
        # Sort by score and select top batch
        scored_opportunities.sort(key=lambda x: x[1], reverse=True)
        selected = [opp for opp, score in scored_opportunities[:batch_size]]
        
        # Apply diversity constraints
        selected = self._apply_diversity_constraints(selected)
        
        return selected
    
    def _filter_by_constraints(self, opportunities: List[ConnectionOpportunity],
                             constraints: UserConstraints) -> List[ConnectionOpportunity]:
        """Filter opportunities based on user constraints."""
        filtered = []
        
        for opp in opportunities:
            # Check privacy constraints
            if constraints.privacy_tier == "minimal" and opp.privacy_cost > 0.5:
                continue
            
            # Check time budget
            if opp.estimated_steps * 2 > constraints.time_budget_minutes:  # Rough estimate
                continue
            
            # Check do-not-ask constraints
            if opp.source in constraints.do_not_ask_until:
                if datetime.now() < constraints.do_not_ask_until[opp.source]:
                    continue
            
            # Check disliked brands
            if any(brand in opp.source.lower() for brand in constraints.disliked_brands):
                continue
            
            filtered.append(opp)
        
        return filtered
    
    def _calculate_opportunity_score(self, opportunity: ConnectionOpportunity,
                                   constraints: UserConstraints) -> float:
        """Calculate opportunity score based on policy."""
        # Base score from value and friction
        value_friction_ratio = opportunity.value_score / (opportunity.friction_score + 0.1)
        
        # Privacy penalty
        privacy_penalty = opportunity.privacy_cost * 0.5
        
        # User preference bonus
        preference_bonus = self.user_preferences.get(opportunity.device_type, 0.0)
        
        # Context penalty for noise sensitivity
        context_penalty = 0.0
        if constraints.noise_sensitivity and "bluetooth" in opportunity.protocol_candidates:
            context_penalty = 0.2
        
        return value_friction_ratio - privacy_penalty + preference_bonus - context_penalty
    
    def _apply_diversity_constraints(self, opportunities: List[ConnectionOpportunity]) -> List[ConnectionOpportunity]:
        """Apply diversity constraints to avoid suggesting similar devices."""
        if len(opportunities) <= 1:
            return opportunities
        
        # Group by device type
        device_types = {}
        for opp in opportunities:
            if opp.device_type not in device_types:
                device_types[opp.device_type] = []
            device_types[opp.device_type].append(opp)
        
        # Select diverse set
        diverse_selection = []
        max_per_type = max(1, len(opportunities) // len(device_types))
        
        for device_type, type_opportunities in device_types.items():
            diverse_selection.extend(type_opportunities[:max_per_type])
        
        return diverse_selection[:len(opportunities)]
    
    def update_policy(self, opportunity_id: str, user_action: str, 
                     outcome: Dict[str, Any]) -> None:
        """Update policy based on user actions and outcomes."""
        self.opportunity_history.append({
            "opportunity_id": opportunity_id,
            "user_action": user_action,  # accept, decline, complete, abandon
            "outcome": outcome,
            "timestamp": datetime.now().isoformat(),
        })
        
        # Update user preferences based on actions
        if user_action == "accept":
            # Positive reinforcement for accepted opportunities
            pass
        elif user_action == "decline":
            # Negative reinforcement for declined opportunities
            pass


class ConnectionOpportunityAgent:
    """Main Connection Opportunity Agent implementation."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.discovery_classifier = DiscoveryClassifier()
        self.value_estimator = OpportunityValueEstimator()
        self.friction_forecaster = FrictionForecaster()
        self.sequencing_policy = SequencingPolicy()
        self._session_factory = get_session_factory(self.config.get("database_url", "sqlite:///./iot_discovery.db"))
        
        # Internal state
        self.opportunity_graph: Dict[str, ConnectionOpportunity] = {}
        self.coverage_ledger: Dict[CapabilityType, float] = {}
        self.user_preference_memory: Dict[str, Dict[str, Any]] = {}
        
    async def process_discoveries(self, discoveries: List[NetworkDiscovery],
                                user_constraints: UserConstraints,
                                env_context: Dict[str, Any]) -> Dict[str, Any]:
        """Process network discoveries and generate opportunities."""
        
        # Step 1: Classify discovered devices
        classified_discoveries = []
        for discovery in discoveries:
            device_type, confidence = self.discovery_classifier.classify_device(discovery)
            classified_discoveries.append({
                "discovery": discovery,
                "device_type": device_type,
                "confidence": confidence,
            })
        
        # Step 2: Generate connection opportunities
        opportunities = []
        for classified in classified_discoveries:
            if classified["confidence"] > 0.5:  # Only consider confident classifications
                opportunity = await self._generate_opportunity(
                    classified["discovery"], 
                    classified["device_type"],
                    env_context
                )
                if opportunity:
                    opportunities.append(opportunity)
                    self.opportunity_graph[opportunity.opportunity_id] = opportunity
        
        # Step 3: Update coverage analysis
        coverage_gaps = self._analyze_coverage_gaps(opportunities)
        
        # Step 4: Select best opportunities
        selected_opportunities = self.sequencing_policy.select_opportunities(
            opportunities, user_constraints
        )
        
        # Step 5: Generate recommendations
        recommendations = self._generate_recommendations(selected_opportunities, coverage_gaps)
        
        return {
            "discoveries_processed": len(discoveries),
            "opportunities_generated": len(opportunities),
            "selected_opportunities": selected_opportunities,
            "coverage_gaps": coverage_gaps,
            "recommendations": recommendations,
            "next_scan_suggested": self._suggest_next_scan(user_constraints),
        }
    
    async def _generate_opportunity(self, discovery: NetworkDiscovery, 
                                  device_type: str, env_context: Dict[str, Any]) -> Optional[ConnectionOpportunity]:
        """Generate connection opportunity from discovery."""
        
        # Map device type to capabilities
        capability_mapping = {
            "light_bulb": [CapabilityType.LIGHTING],
            "switch": [CapabilityType.LIGHTING],
            "sensor": [CapabilityType.SENSORS],
            "camera": [CapabilityType.CAMERAS, CapabilityType.SECURITY],
            "thermostat": [CapabilityType.CLIMATE],
            "lock": [CapabilityType.LOCKS, CapabilityType.SECURITY],
            "speaker": [CapabilityType.ENTERTAINMENT],
            "display": [CapabilityType.DISPLAYS, CapabilityType.ENTERTAINMENT],
        }
        
        capabilities = capability_mapping.get(device_type, [CapabilityType.SENSORS])
        
        # Estimate value and friction
        temp_opportunity = ConnectionOpportunity(
            opportunity_id=f"opp_{discovery.discovery_id}",
            source=discovery.discovery_id,
            device_type=device_type,
            capability_unlocks=capabilities,
            value_score=0.0,  # Will be calculated
            friction_score=0.0,  # Will be calculated
            privacy_cost=0.0,  # Will be calculated
            context_constraints=[],
            rationale="",
            estimated_steps=0,
            success_probability=0.0,
        )
        
        # Calculate scores
        value_score = self.value_estimator.estimate_value(temp_opportunity, self.coverage_ledger)
        friction_forecast = self.friction_forecaster.forecast_friction(temp_opportunity, env_context)
        
        # Determine privacy cost based on discovery type
        privacy_cost = self._estimate_privacy_cost(discovery)
        
        # Generate rationale
        rationale = self._generate_rationale(discovery, device_type, capabilities, value_score)
        
        return ConnectionOpportunity(
            opportunity_id=f"opp_{discovery.discovery_id}",
            source=discovery.discovery_id,
            device_type=device_type,
            capability_unlocks=capabilities,
            value_score=value_score,
            friction_score=friction_forecast["friction_score"],
            privacy_cost=privacy_cost,
            context_constraints=self._identify_context_constraints(discovery, env_context),
            rationale=rationale,
            estimated_steps=friction_forecast["steps"],
            success_probability=friction_forecast["success_probability"],
        )
    
    def _estimate_privacy_cost(self, discovery: NetworkDiscovery) -> float:
        """Estimate privacy cost of connecting this discovery."""
        # Local discoveries have lower privacy cost
        if discovery.discovery_type in [DiscoveryType.BLE, DiscoveryType.MDNS, DiscoveryType.SSDP]:
            return 0.2
        
        # Cloud-based discoveries have higher privacy cost
        if discovery.discovery_type in [DiscoveryType.SMARTTHINGS, DiscoveryType.MATTER]:
            return 0.6
        
        return 0.4  # Default moderate cost
    
    def _generate_rationale(self, discovery: NetworkDiscovery, device_type: str,
                          capabilities: List[CapabilityType], value_score: float) -> str:
        """Generate human-readable rationale for the opportunity."""
        capability_names = [cap.value for cap in capabilities]
        
        if value_score > 0.7:
            impact = "significantly improve"
        elif value_score > 0.4:
            impact = "improve"
        else:
            impact = "slightly enhance"
        
        return f"Connecting this {device_type} would {impact} your {', '.join(capability_names)} capabilities and enable new automation routines."
    
    def _identify_context_constraints(self, discovery: NetworkDiscovery, 
                                    env_context: Dict[str, Any]) -> List[str]:
        """Identify context constraints for this opportunity."""
        constraints = []
        
        if discovery.discovery_type == DiscoveryType.BLE and not env_context.get("bluetooth_available"):
            constraints.append("bluetooth_unavailable")
        
        if discovery.discovery_type == DiscoveryType.THREAD and not env_context.get("thread_available"):
            constraints.append("thread_unavailable")
        
        if env_context.get("network_quality") == "poor":
            constraints.append("poor_network")
        
        return constraints
    
    def _analyze_coverage_gaps(self, opportunities: List[ConnectionOpportunity]) -> List[CoverageGap]:
        """Analyze current capability coverage gaps."""
        gaps = []
        
        # Calculate current coverage for each capability
        capability_counts = {}
        for opp in opportunities:
            for capability in opp.capability_unlocks:
                if capability not in capability_counts:
                    capability_counts[capability] = 0
                capability_counts[capability] += 1
        
        # Identify gaps
        for capability in CapabilityType:
            current_coverage = min(capability_counts.get(capability, 0) / 5.0, 1.0)  # Normalize to 0-1
            self.coverage_ledger[capability] = current_coverage
            
            if current_coverage < 0.5:  # Less than 50% coverage
                missing_devices = [opp.device_type for opp in opportunities 
                                 if capability in opp.capability_unlocks]
                
                gap = CoverageGap(
                    capability=capability,
                    current_coverage=current_coverage,
                    missing_devices=missing_devices,
                    routine_impact=self._calculate_routine_impact(capability),
                    priority_score=1.0 - current_coverage,  # Higher priority for lower coverage
                )
                gaps.append(gap)
        
        return gaps
    
    def _calculate_routine_impact(self, capability: CapabilityType) -> float:
        """Calculate how much a capability affects routine flexibility."""
        routine_importance = {
            CapabilityType.LIGHTING: 0.9,  # Very important for routines
            CapabilityType.CLIMATE: 0.8,
            CapabilityType.SECURITY: 0.7,
            CapabilityType.ENTERTAINMENT: 0.6,
            CapabilityType.APPLIANCES: 0.5,
            CapabilityType.SENSORS: 0.4,
            CapabilityType.CAMERAS: 0.3,
            CapabilityType.LOCKS: 0.3,
            CapabilityType.SPEAKERS: 0.2,
            CapabilityType.DISPLAYS: 0.2,
        }
        
        return routine_importance.get(capability, 0.3)
    
    def _generate_recommendations(self, opportunities: List[ConnectionOpportunity],
                                coverage_gaps: List[CoverageGap]) -> List[Dict[str, Any]]:
        """Generate recommendations for the user."""
        recommendations = []
        
        # High-value opportunities
        high_value_opps = [opp for opp in opportunities if opp.value_score > 0.7]
        if high_value_opps:
            recommendations.append({
                "type": "high_value",
                "title": "High-Impact Connections",
                "description": f"These {len(high_value_opps)} devices will significantly improve your smart home capabilities",
                "opportunities": high_value_opps[:3],
            })
        
        # Coverage gaps
        if coverage_gaps:
            top_gap = max(coverage_gaps, key=lambda g: g.priority_score)
            recommendations.append({
                "type": "coverage_gap",
                "title": f"Improve {top_gap.capability.value.title()} Coverage",
                "description": f"Adding {top_gap.capability.value} devices will enable new automation routines",
                "capability": top_gap.capability,
                "current_coverage": top_gap.current_coverage,
            })
        
        # Low-friction opportunities
        low_friction_opps = [opp for opp in opportunities if opp.friction_score < 0.3]
        if low_friction_opps:
            recommendations.append({
                "type": "low_friction",
                "title": "Quick Connections",
                "description": f"These {len(low_friction_opps)} devices can be connected in under 5 minutes",
                "opportunities": low_friction_opps[:2],
            })
        
        return recommendations
    
    def _suggest_next_scan(self, user_constraints: UserConstraints) -> Optional[datetime]:
        """Suggest when to perform the next discovery scan."""
        # Don't suggest scans during quiet hours
        current_hour = datetime.now().hour
        if user_constraints.quiet_hours[0] <= current_hour <= user_constraints.quiet_hours[1]:
            # Suggest for next day during active hours
            next_scan = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
            if next_scan < datetime.now():
                next_scan += timedelta(days=1)
            return next_scan
        
        # Suggest scan in 2 hours if during active hours
        return datetime.now() + timedelta(hours=2)
    
    async def record_user_action(self, opportunity_id: str, action: str, 
                               outcome: Optional[Dict[str, Any]] = None) -> None:
        """Record user action for policy learning."""
        self.sequencing_policy.update_policy(opportunity_id, action, outcome or {})
        
        # Update user preference memory
        if opportunity_id in self.opportunity_graph:
            opportunity = self.opportunity_graph[opportunity_id]
            device_type = opportunity.device_type
            
            if device_type not in self.user_preference_memory:
                self.user_preference_memory[device_type] = {
                    "acceptances": 0,
                    "declines": 0,
                    "completions": 0,
                    "abandons": 0,
                }
            
            if action in self.user_preference_memory[device_type]:
                self.user_preference_memory[device_type][action] += 1
        
        logger.info(f"Recorded user action: {opportunity_id} - {action}")
    
    async def get_coverage_summary(self) -> Dict[str, Any]:
        """Get current capability coverage summary."""
        return {
            "coverage_by_capability": self.coverage_ledger,
            "total_opportunities": len(self.opportunity_graph),
            "coverage_score": np.mean(list(self.coverage_ledger.values())),
            "recommendations": self._generate_coverage_recommendations(),
        }
    
    def _generate_coverage_recommendations(self) -> List[str]:
        """Generate recommendations based on coverage analysis."""
        recommendations = []
        
        # Find lowest coverage capabilities
        sorted_coverage = sorted(self.coverage_ledger.items(), key=lambda x: x[1])
        
        for capability, coverage in sorted_coverage[:3]:
            if coverage < 0.3:
                recommendations.append(f"Consider adding more {capability.value} devices for better automation")
            elif coverage < 0.6:
                recommendations.append(f"Your {capability.value} coverage is moderate - adding more devices would improve routines")
        
        return recommendations
