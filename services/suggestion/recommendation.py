"""
Recommendation Packager
Creates user-friendly recommendation cards and what-if analysis.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json

from .models import (
    RecommendationCard, CombinationCandidate, ContextSnapshot, CapabilityType,
    PrivacyLevel, SafetyLevel, EffortLevel, WhatIfItem
)

logger = logging.getLogger(__name__)


class RecommendationPackager:
    """
    Packages evaluated combinations into user-friendly recommendations.
    
    Implements B4 from the spec:
    - Select top unique outcomes after clustering similar ones
    - Build home-specific plans for each selected outcome
    - Produce user-friendly suggestion cards
    - Generate what-if reports for missing capabilities
    """
    
    def __init__(self):
        self._card_templates = self._initialize_card_templates()
        self._what_if_templates = self._initialize_what_if_templates()
        
    async def create_recommendations(
        self,
        evaluation_result,
        user_id: str,
        session_id: str
    ) -> List[RecommendationCard]:
        """
        Create recommendation cards from evaluated combinations.
        
        Args:
            evaluation_result: Result from combination evaluator
            user_id: User identifier
            session_id: Session identifier
            
        Returns:
            List of recommendation cards
        """
        recommendations = []
        
        # Get top combinations
        top_combinations = evaluation_result.combinations[:10]  # Limit to top 10
        
        # Cluster similar combinations
        clustered_combinations = await self._cluster_similar_combinations(top_combinations)
        
        # Create recommendation cards for each cluster
        for cluster in clustered_combinations:
            card = await self._create_recommendation_card(
                cluster, user_id, session_id
            )
            if card:
                recommendations.append(card)
        
        # Sort by confidence
        recommendations.sort(key=lambda c: c.confidence, reverse=True)
        
        logger.info(f"Created {len(recommendations)} recommendation cards")
        return recommendations
    
    async def create_what_if_items(
        self,
        capability_graph: Dict[str, Any],
        missing_capabilities: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Create what-if analysis items for missing capabilities.
        
        Args:
            capability_graph: Current capability graph
            missing_capabilities: List of missing capability types
            
        Returns:
            List of what-if items
        """
        what_if_items = []
        
        # Get unique missing capability types
        unique_missing = list(set(missing_capabilities))
        
        for capability_type in unique_missing:
            what_if_item = await self._create_what_if_item(
                capability_type, capability_graph
            )
            if what_if_item:
                what_if_items.append(what_if_item)
        
        logger.info(f"Created {len(what_if_items)} what-if items")
        return what_if_items
    
    async def _cluster_similar_combinations(
        self,
        combinations: List[CombinationCandidate]
    ) -> List[List[CombinationCandidate]]:
        """Cluster similar combinations together."""
        clusters = []
        processed_signatures = set()
        
        for combination in combinations:
            # Check if we already have a similar combination
            if combination.capability_signature in processed_signatures:
                # Add to existing cluster
                for cluster in clusters:
                    if cluster[0].capability_signature == combination.capability_signature:
                        cluster.append(combination)
                        break
            else:
                # Create new cluster
                clusters.append([combination])
                processed_signatures.add(combination.capability_signature)
        
        return clusters
    
    async def _create_recommendation_card(
        self,
        cluster: List[CombinationCandidate],
        user_id: str,
        session_id: str
    ) -> Optional[RecommendationCard]:
        """Create a recommendation card from a cluster of combinations."""
        if not cluster:
            return None
        
        # Use the best combination from the cluster
        best_combination = cluster[0]
        
        # Generate card content
        title = await self._generate_card_title(best_combination)
        description = await self._generate_card_description(best_combination)
        rationale = await self._generate_card_rationale(best_combination)
        category = await self._determine_card_category(best_combination)
        confidence = await self._calculate_card_confidence(best_combination, len(cluster))
        
        # Create tunable controls
        tunable_controls = await self._create_tunable_controls(best_combination)
        
        # Create storyboard preview
        storyboard_preview = await self._create_storyboard_preview(best_combination)
        
        card = RecommendationCard(
            title=title,
            description=description,
            rationale=rationale,
            category=category,
            confidence=confidence,
            privacy_badge=best_combination.privacy_level,
            safety_badge=best_combination.safety_level,
            effort_rating=best_combination.effort_required,
            tunable_controls=tunable_controls,
            storyboard_preview=storyboard_preview,
            combination=best_combination
        )
        
        return card
    
    async def _generate_card_title(self, combination: CombinationCandidate) -> str:
        """Generate a title for the recommendation card."""
        # Determine primary capability
        primary_capability = self._get_primary_capability(combination)
        
        # Map capability to title template
        title_templates = {
            CapabilityType.LIGHTING: "Smart Lighting Setup",
            CapabilityType.SENSING: "Motion-Aware Automation",
            CapabilityType.ACTUATION: "Smart Device Control",
            CapabilityType.AUDIO: "Audio Enhancement",
            CapabilityType.VIDEO: "Security Monitoring",
            CapabilityType.SECURITY: "Security Enhancement",
            CapabilityType.CLIMATE: "Climate Control",
            CapabilityType.ENERGY: "Energy Optimization",
            CapabilityType.ACCESS_CONTROL: "Access Management",
            CapabilityType.WEATHER: "Weather-Responsive Setup",
            CapabilityType.CALENDAR: "Schedule-Based Automation",
            CapabilityType.PRESENCE: "Presence-Aware Setup"
        }
        
        base_title = title_templates.get(primary_capability, "Smart Home Enhancement")
        
        # Add room context if available
        rooms = set()
        for device in combination.devices:
            if device.room:
                rooms.add(device.room)
        
        if rooms:
            room_list = ", ".join(sorted(rooms))
            return f"{base_title} for {room_list}"
        
        return base_title
    
    async def _generate_card_description(self, combination: CombinationCandidate) -> str:
        """Generate a description for the recommendation card."""
        # Count devices and services
        device_count = len(combination.devices)
        service_count = len(combination.services)
        
        # Get primary capabilities
        capabilities = set()
        for device in combination.devices:
            capabilities.add(device.capability_type.value)
        for service in combination.services:
            capabilities.add(service.capability_type.value)
        
        # Create description based on capabilities
        if CapabilityType.LIGHTING in capabilities and CapabilityType.SENSING in capabilities:
            return "Automatically control lighting based on motion detection for enhanced convenience and energy savings."
        elif CapabilityType.SECURITY in capabilities and CapabilityType.VIDEO in capabilities:
            return "Monitor your home with video and motion sensors for enhanced security and peace of mind."
        elif CapabilityType.CLIMATE in capabilities and CapabilityType.SENSING in capabilities:
            return "Optimize your home's climate based on environmental conditions and occupancy."
        elif CapabilityType.ENERGY in capabilities and CapabilityType.ACTUATION in capabilities:
            return "Automatically manage power consumption by turning devices on and off based on usage patterns."
        elif CapabilityType.WEATHER in capabilities and CapabilityType.LIGHTING in capabilities:
            return "Adjust lighting based on weather conditions to maintain optimal comfort and visibility."
        else:
            return f"Connect {device_count} devices and {service_count} services for a smarter home experience."
    
    async def _generate_card_rationale(self, combination: CombinationCandidate) -> List[str]:
        """Generate rationale points for the recommendation card."""
        rationale = []
        
        # Context fit rationale
        if combination.context_fit > 0.7:
            rationale.append("Perfect fit for your current situation")
        elif combination.context_fit > 0.5:
            rationale.append("Good fit for your current context")
        
        # Utility rationale
        if combination.estimated_value > 0.8:
            rationale.append("High value for your home")
        elif combination.estimated_value > 0.6:
            rationale.append("Good value for your setup")
        
        # Safety rationale
        if combination.safety_level == SafetyLevel.SAFE:
            rationale.append("Safe and secure implementation")
        
        # Energy rationale
        if any(d.capability_type == CapabilityType.ENERGY for d in combination.devices):
            rationale.append("Helps save energy and reduce costs")
        
        # Convenience rationale
        if combination.effort_required in [EffortLevel.NONE, EffortLevel.LOW]:
            rationale.append("Easy to set up and use")
        
        # Privacy rationale
        if combination.privacy_level == PrivacyLevel.PUBLIC:
            rationale.append("Privacy-friendly implementation")
        
        return rationale[:3]  # Limit to top 3 rationale points
    
    async def _determine_card_category(self, combination: CombinationCandidate) -> str:
        """Determine the category for the recommendation card."""
        capabilities = set()
        for device in combination.devices:
            capabilities.add(device.capability_type)
        for service in combination.services:
            capabilities.add(service.capability_type)
        
        # Determine primary category
        if CapabilityType.SECURITY in capabilities or CapabilityType.ACCESS_CONTROL in capabilities:
            return "security"
        elif CapabilityType.ENERGY in capabilities:
            return "energy"
        elif CapabilityType.LIGHTING in capabilities or CapabilityType.CLIMATE in capabilities:
            return "comfort"
        elif CapabilityType.SENSING in capabilities:
            return "automation"
        else:
            return "enhancement"
    
    async def _calculate_card_confidence(
        self,
        combination: CombinationCandidate,
        cluster_size: int
    ) -> float:
        """Calculate confidence score for the recommendation card."""
        confidence = combination.estimated_value
        
        # Boost confidence for combinations that appear multiple times
        if cluster_size > 1:
            confidence += 0.1
        
        # Boost confidence for high feasibility
        if combination.feasibility_score > 0.9:
            confidence += 0.1
        
        # Reduce confidence for high effort
        if combination.effort_required == EffortLevel.HIGH:
            confidence -= 0.1
        
        return min(1.0, max(0.0, confidence))
    
    async def _create_tunable_controls(self, combination: CombinationCandidate) -> Dict[str, Any]:
        """Create tunable controls for the recommendation card."""
        controls = {}
        
        # Lighting controls
        if any(d.capability_type == CapabilityType.LIGHTING for d in combination.devices):
            controls["brightness"] = {
                "type": "slider",
                "min": 0,
                "max": 100,
                "default": 80,
                "label": "Brightness Level"
            }
            controls["duration"] = {
                "type": "slider",
                "min": 30,
                "max": 300,
                "default": 120,
                "label": "Duration (seconds)"
            }
        
        # Sensing controls
        if any(d.capability_type == CapabilityType.SENSING for d in combination.devices):
            controls["sensitivity"] = {
                "type": "slider",
                "min": 1,
                "max": 10,
                "default": 5,
                "label": "Motion Sensitivity"
            }
        
        # Audio controls
        if any(d.capability_type == CapabilityType.AUDIO for d in combination.devices):
            controls["volume"] = {
                "type": "slider",
                "min": 0,
                "max": 100,
                "default": 50,
                "label": "Volume Level"
            }
        
        return controls
    
    async def _create_storyboard_preview(self, combination: CombinationCandidate) -> List[Dict[str, Any]]:
        """Create storyboard preview for the recommendation card."""
        storyboard = []
        
        # Step 1: Trigger
        trigger_step = await self._create_trigger_step(combination)
        if trigger_step:
            storyboard.append(trigger_step)
        
        # Step 2: Action
        action_step = await self._create_action_step(combination)
        if action_step:
            storyboard.append(action_step)
        
        # Step 3: Result
        result_step = await self._create_result_step(combination)
        if result_step:
            storyboard.append(result_step)
        
        return storyboard
    
    async def _create_trigger_step(self, combination: CombinationCandidate) -> Dict[str, Any]:
        """Create trigger step for storyboard."""
        triggers = []
        
        for device in combination.devices:
            if device.capability_type == CapabilityType.SENSING:
                triggers.append("Motion detected")
            elif device.capability_type == CapabilityType.TIME:
                triggers.append("Time-based trigger")
        
        for service in combination.services:
            if service.capability_type == CapabilityType.WEATHER:
                triggers.append("Weather condition change")
            elif service.capability_type == CapabilityType.CALENDAR:
                triggers.append("Calendar event")
        
        if triggers:
            return {
                "step": 1,
                "title": "Trigger",
                "description": " or ".join(triggers),
                "icon": "trigger"
            }
        
        return None
    
    async def _create_action_step(self, combination: CombinationCandidate) -> Dict[str, Any]:
        """Create action step for storyboard."""
        actions = []
        
        for device in combination.devices:
            if device.capability_type == CapabilityType.LIGHTING:
                actions.append("Adjust lighting")
            elif device.capability_type == CapabilityType.ACTUATION:
                actions.append("Control device")
            elif device.capability_type == CapabilityType.CLIMATE:
                actions.append("Adjust climate")
        
        if actions:
            return {
                "step": 2,
                "title": "Action",
                "description": " and ".join(actions),
                "icon": "action"
            }
        
        return None
    
    async def _create_result_step(self, combination: CombinationCandidate) -> Dict[str, Any]:
        """Create result step for storyboard."""
        results = []
        
        if any(d.capability_type == CapabilityType.LIGHTING for d in combination.devices):
            results.append("Enhanced comfort")
        if any(d.capability_type == CapabilityType.ENERGY for d in combination.devices):
            results.append("Energy savings")
        if any(d.capability_type == CapabilityType.SECURITY for d in combination.devices):
            results.append("Improved security")
        
        if results:
            return {
                "step": 3,
                "title": "Result",
                "description": " and ".join(results),
                "icon": "result"
            }
        
        return {
            "step": 3,
            "title": "Result",
            "description": "Automated home experience",
            "icon": "result"
        }
    
    async def _create_what_if_item(
        self,
        capability_type: str,
        capability_graph: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create a what-if item for a missing capability."""
        # Get template for this capability type
        template = self._what_if_templates.get(capability_type)
        if not template:
            return None
        
        # Calculate estimated benefit
        estimated_benefit = await self._calculate_what_if_benefit(capability_type, capability_graph)
        
        # Determine setup effort
        setup_effort = self._determine_what_if_effort(capability_type)
        
        # Determine privacy and safety impact
        privacy_impact = self._determine_what_if_privacy(capability_type)
        safety_impact = self._determine_what_if_safety(capability_type)
        
        return {
            "capability_type": capability_type,
            "capability_name": template["name"],
            "description": template["description"],
            "example_outcomes": template["examples"],
            "estimated_benefit": estimated_benefit,
            "setup_effort": setup_effort.value,
            "privacy_impact": privacy_impact.value,
            "safety_impact": safety_impact.value
        }
    
    def _get_primary_capability(self, combination: CombinationCandidate) -> CapabilityType:
        """Get the primary capability from a combination."""
        # Prioritize capabilities by importance
        priority_order = [
            CapabilityType.SECURITY,
            CapabilityType.ACCESS_CONTROL,
            CapabilityType.VIDEO,
            CapabilityType.SENSING,
            CapabilityType.LIGHTING,
            CapabilityType.CLIMATE,
            CapabilityType.ENERGY,
            CapabilityType.ACTUATION,
            CapabilityType.AUDIO,
            CapabilityType.WEATHER,
            CapabilityType.CALENDAR,
            CapabilityType.PRESENCE
        ]
        
        for priority_cap in priority_order:
            for device in combination.devices:
                if device.capability_type == priority_cap:
                    return priority_cap
            for service in combination.services:
                if service.capability_type == priority_cap:
                    return priority_cap
        
        # Fallback to first capability
        if combination.devices:
            return combination.devices[0].capability_type
        elif combination.services:
            return combination.services[0].capability_type
        
        return CapabilityType.LIGHTING  # Default fallback
    
    async def _calculate_what_if_benefit(
        self,
        capability_type: str,
        capability_graph: Dict[str, Any]
    ) -> str:
        """Calculate estimated benefit for what-if item."""
        benefit_templates = {
            "lighting": "Add smart lighting for comfort and energy savings",
            "sensing": "Add motion sensors for automated responses",
            "actuation": "Add smart switches for remote control",
            "audio": "Add audio devices for notifications and entertainment",
            "video": "Add cameras for security monitoring",
            "security": "Add security devices for enhanced protection",
            "climate": "Add climate control for optimal comfort and efficiency",
            "energy": "Add energy monitoring for cost savings",
            "access_control": "Add smart locks for secure and convenient access control",
            "weather": "Add weather integration for responsive automation",
            "calendar": "Add calendar integration for schedule-based automation",
            "presence": "Add presence detection for personalized experiences"
        }
        
        return benefit_templates.get(capability_type, "Add this capability for enhanced automation")
    
    def _determine_what_if_effort(self, capability_type: str) -> EffortLevel:
        """Determine setup effort for what-if item."""
        effort_mapping = {
            "lighting": EffortLevel.LOW,
            "sensing": EffortLevel.LOW,
            "actuation": EffortLevel.LOW,
            "audio": EffortLevel.MEDIUM,
            "video": EffortLevel.MEDIUM,
            "security": EffortLevel.MEDIUM,
            "climate": EffortLevel.MEDIUM,
            "energy": EffortLevel.LOW,
            "access_control": EffortLevel.HIGH,
            "weather": EffortLevel.NONE,
            "calendar": EffortLevel.LOW,
            "presence": EffortLevel.LOW
        }
        
        return effort_mapping.get(capability_type, EffortLevel.MEDIUM)
    
    def _determine_what_if_privacy(self, capability_type: str) -> PrivacyLevel:
        """Determine privacy impact for what-if item."""
        privacy_mapping = {
            "lighting": PrivacyLevel.PUBLIC,
            "sensing": PrivacyLevel.PERSONAL,
            "actuation": PrivacyLevel.PUBLIC,
            "audio": PrivacyLevel.PERSONAL,
            "video": PrivacyLevel.SENSITIVE,
            "security": PrivacyLevel.PRIVATE,
            "climate": PrivacyLevel.PUBLIC,
            "energy": PrivacyLevel.PUBLIC,
            "access_control": PrivacyLevel.PRIVATE,
            "weather": PrivacyLevel.PUBLIC,
            "calendar": PrivacyLevel.PERSONAL,
            "presence": PrivacyLevel.PERSONAL
        }
        
        return privacy_mapping.get(capability_type, PrivacyLevel.PERSONAL)
    
    def _determine_what_if_safety(self, capability_type: str) -> SafetyLevel:
        """Determine safety impact for what-if item."""
        safety_mapping = {
            "lighting": SafetyLevel.SAFE,
            "sensing": SafetyLevel.SAFE,
            "actuation": SafetyLevel.SAFE,
            "audio": SafetyLevel.SAFE,
            "video": SafetyLevel.SAFE,
            "security": SafetyLevel.CAUTION,
            "climate": SafetyLevel.SAFE,
            "energy": SafetyLevel.SAFE,
            "access_control": SafetyLevel.CAUTION,
            "weather": SafetyLevel.SAFE,
            "calendar": SafetyLevel.SAFE,
            "presence": SafetyLevel.SAFE
        }
        
        return safety_mapping.get(capability_type, SafetyLevel.SAFE)
    
    def _initialize_card_templates(self) -> Dict[str, Any]:
        """Initialize card templates."""
        return {
            "lighting": {
                "title_template": "Smart Lighting for {room}",
                "description_template": "Automated lighting control for {room}"
            },
            "security": {
                "title_template": "Security Enhancement",
                "description_template": "Enhanced security monitoring and control"
            },
            "energy": {
                "title_template": "Energy Optimization",
                "description_template": "Smart energy management and cost savings"
            }
        }
    
    def _initialize_what_if_templates(self) -> Dict[str, Any]:
        """Initialize what-if templates."""
        return {
            "lighting": {
                "name": "Smart Lighting",
                "description": "Add smart bulbs and switches for automated lighting control",
                "examples": ["Motion-activated lights", "Schedule-based lighting", "Weather-responsive lighting"]
            },
            "sensing": {
                "name": "Motion Sensors",
                "description": "Add motion sensors for automated responses to movement",
                "examples": ["Motion-triggered lights", "Occupancy-based climate control", "Security alerts"]
            },
            "actuation": {
                "name": "Smart Switches",
                "description": "Add smart switches and outlets for remote device control",
                "examples": ["Remote power control", "Energy monitoring", "Automated device management"]
            },
            "video": {
                "name": "Security Cameras",
                "description": "Add cameras for security monitoring and peace of mind",
                "examples": ["Motion-triggered recording", "Remote monitoring", "Security alerts"]
            },
            "climate": {
                "name": "Smart Thermostat",
                "description": "Add smart climate control for optimal comfort and efficiency",
                "examples": ["Schedule-based heating", "Occupancy-based control", "Weather-responsive settings"]
            },
            "access_control": {
                "name": "Smart Locks",
                "description": "Add smart locks for secure and convenient access control",
                "examples": ["Remote lock/unlock", "Access logs", "Temporary access codes"]
            }
        }
