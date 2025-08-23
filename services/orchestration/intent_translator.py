"""
Intent Translator
Converts natural language intents into structured goals and constraints.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .models import Goal, Constraint, PrivacyClass, TrustTier

logger = logging.getLogger(__name__)


@dataclass
class IntentTranslation:
    """Result of intent translation."""
    goals: List[Goal]
    constraints: List[Constraint]
    confidence: float
    entities: Dict[str, Any]


class IntentTranslator:
    """Translates natural language intents into structured specifications."""
    
    def __init__(self):
        # Intent patterns for common IoT operations
        self._patterns = {
            "energy_optimization": [
                r"optimize\s+energy",
                r"save\s+power",
                r"reduce\s+electricity",
                r"lower\s+energy\s+usage",
                r"minimize\s+power\s+consumption"
            ],
            "comfort_control": [
                r"set\s+comfort",
                r"adjust\s+temperature",
                r"control\s+climate",
                r"maintain\s+comfort",
                r"optimize\s+comfort"
            ],
            "security_monitoring": [
                r"monitor\s+security",
                r"check\s+safety",
                r"surveillance",
                r"security\s+alert",
                r"intrusion\s+detection"
            ],
            "automation": [
                r"automate",
                r"schedule",
                r"routine",
                r"automatic",
                r"smart\s+home"
            ],
            "data_collection": [
                r"collect\s+data",
                r"gather\s+information",
                r"monitor\s+metrics",
                r"track\s+usage",
                r"analyze\s+patterns"
            ],
            "privacy_focused": [
                r"private",
                r"local\s+only",
                r"no\s+cloud",
                r"offline",
                r"secure"
            ],
            "cost_conscious": [
                r"cheap",
                r"low\s+cost",
                r"budget",
                r"affordable",
                r"minimize\s+cost"
            ],
            "high_performance": [
                r"fast",
                r"quick",
                r"real\s+time",
                r"immediate",
                r"urgent"
            ]
        }
        
        # Device type patterns
        self._device_patterns = {
            "thermostat": [r"thermostat", r"temperature", r"climate", r"hvac"],
            "lighting": [r"light", r"bulb", r"lamp", r"switch"],
            "security": [r"camera", r"sensor", r"alarm", r"lock"],
            "appliance": [r"appliance", r"device", r"equipment"],
            "sensor": [r"sensor", r"detector", r"monitor"]
        }
        
        # Constraint patterns
        self._constraint_patterns = {
            "latency": [
                (r"within\s+(\d+)\s*(ms|milliseconds?)", "latency"),
                (r"(\d+)\s*(ms|milliseconds?)\s+or\s+less", "latency"),
                (r"real\s+time", "latency"),
                (r"immediate", "latency")
            ],
            "cost": [
                (r"under\s+\$(\d+)", "cost"),
                (r"less\s+than\s+\$(\d+)", "cost"),
                (r"budget\s+of\s+\$(\d+)", "cost"),
                (r"max\s+cost\s+\$(\d+)", "cost")
            ],
            "energy": [
                (r"(\d+)\s*(w|watts?)\s+or\s+less", "energy"),
                (r"under\s+(\d+)\s*(w|watts?)", "energy"),
                (r"low\s+power", "energy")
            ],
            "privacy": [
                (r"local\s+only", "privacy"),
                (r"no\s+cloud", "privacy"),
                (r"offline", "privacy"),
                (r"private", "privacy")
            ]
        }
    
    async def translate(self, intent: str) -> IntentTranslation:
        """
        Translate a natural language intent into structured goals and constraints.
        
        Args:
            intent: Natural language description of the desired action
            
        Returns:
            IntentTranslation with goals, constraints, confidence, and entities
        """
        logger.debug(f"Translating intent: {intent}")
        
        # Extract entities
        entities = self._extract_entities(intent)
        
        # Generate goals based on intent patterns
        goals = self._generate_goals(intent, entities)
        
        # Generate constraints based on intent patterns
        constraints = self._generate_constraints(intent, entities)
        
        # Calculate confidence based on pattern matches
        confidence = self._calculate_confidence(intent, entities)
        
        return IntentTranslation(
            goals=goals,
            constraints=constraints,
            confidence=confidence,
            entities=entities
        )
    
    def _extract_entities(self, intent: str) -> Dict[str, Any]:
        """Extract entities from the intent."""
        entities = {
            "device_types": [],
            "actions": [],
            "locations": [],
            "time_constraints": [],
            "numeric_values": {}
        }
        
        intent_lower = intent.lower()
        
        # Extract device types
        for device_type, patterns in self._device_patterns.items():
            for pattern in patterns:
                if re.search(pattern, intent_lower):
                    entities["device_types"].append(device_type)
                    break
        
        # Extract actions
        action_patterns = [
            (r"turn\s+(on|off)", "toggle"),
            (r"set\s+(\w+)", "set"),
            (r"adjust\s+(\w+)", "adjust"),
            (r"monitor\s+(\w+)", "monitor"),
            (r"collect\s+(\w+)", "collect"),
            (r"optimize\s+(\w+)", "optimize"),
            (r"minimize\s+(\w+)", "minimize"),
            (r"maximize\s+(\w+)", "maximize")
        ]
        
        for pattern, action in action_patterns:
            if re.search(pattern, intent_lower):
                entities["actions"].append(action)
        
        # Extract locations
        location_patterns = [
            r"in\s+the\s+(\w+)",
            r"at\s+(\w+)",
            r"(\w+)\s+room",
            r"(\w+)\s+area"
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, intent_lower)
            entities["locations"].extend(matches)
        
        # Extract numeric values
        numeric_patterns = [
            (r"(\d+)\s*degrees?", "temperature"),
            (r"(\d+)\s*%", "percentage"),
            (r"(\d+)\s*(w|watts?)", "power"),
            (r"\$(\d+)", "cost"),
            (r"(\d+)\s*(ms|milliseconds?)", "latency")
        ]
        
        for pattern, value_type in numeric_patterns:
            matches = re.findall(pattern, intent_lower)
            if matches:
                entities["numeric_values"][value_type] = [int(m[0]) if isinstance(m, tuple) else int(m) for m in matches]
        
        return entities
    
    def _generate_goals(self, intent: str, entities: Dict[str, Any]) -> List[Goal]:
        """Generate goals based on intent patterns."""
        goals = []
        intent_lower = intent.lower()
        
        # Energy optimization goals
        if any(re.search(pattern, intent_lower) for pattern in self._patterns["energy_optimization"]):
            goals.append(Goal(
                type="minimize",
                target="energy",
                value="consumption",
                weight=0.9
            ))
        
        # Comfort control goals
        if any(re.search(pattern, intent_lower) for pattern in self._patterns["comfort_control"]):
            goals.append(Goal(
                type="optimize",
                target="comfort",
                value="user_satisfaction",
                weight=0.8
            ))
        
        # Security monitoring goals
        if any(re.search(pattern, intent_lower) for pattern in self._patterns["security_monitoring"]):
            goals.append(Goal(
                type="maximize",
                target="security",
                value="safety_level",
                weight=0.9
            ))
        
        # Automation goals
        if any(re.search(pattern, intent_lower) for pattern in self._patterns["automation"]):
            goals.append(Goal(
                type="optimize",
                target="efficiency",
                value="automation_level",
                weight=0.7
            ))
        
        # Data collection goals
        if any(re.search(pattern, intent_lower) for pattern in self._patterns["data_collection"]):
            goals.append(Goal(
                type="maximize",
                target="data_quality",
                value="completeness",
                weight=0.6
            ))
        
        # Privacy-focused goals
        if any(re.search(pattern, intent_lower) for pattern in self._patterns["privacy_focused"]):
            goals.append(Goal(
                type="maximize",
                target="privacy",
                value="local_processing",
                weight=1.0
            ))
        
        # Cost-conscious goals
        if any(re.search(pattern, intent_lower) for pattern in self._patterns["cost_conscious"]):
            goals.append(Goal(
                type="minimize",
                target="cost",
                value="total_expense",
                weight=0.8
            ))
        
        # High-performance goals
        if any(re.search(pattern, intent_lower) for pattern in self._patterns["high_performance"]):
            goals.append(Goal(
                type="minimize",
                target="latency",
                value="response_time",
                weight=0.9
            ))
        
        # Default goal if none found
        if not goals:
            goals.append(Goal(
                type="optimize",
                target="efficiency",
                value="overall_performance",
                weight=0.5
            ))
        
        return goals
    
    def _generate_constraints(self, intent: str, entities: Dict[str, Any]) -> List[Constraint]:
        """Generate constraints based on intent patterns."""
        constraints = []
        intent_lower = intent.lower()
        
        # Latency constraints
        for pattern, constraint_type in self._constraint_patterns["latency"]:
            match = re.search(pattern, intent_lower)
            if match:
                if "real time" in intent_lower or "immediate" in intent_lower:
                    value = 100  # 100ms for real-time
                else:
                    value = int(match.group(1))
                
                constraints.append(Constraint(
                    type="latency",
                    value=value,
                    operator="lte",
                    priority=8
                ))
        
        # Cost constraints
        for pattern, constraint_type in self._constraint_patterns["cost"]:
            match = re.search(pattern, intent_lower)
            if match:
                value = float(match.group(1))
                constraints.append(Constraint(
                    type="cost",
                    value=value,
                    operator="lte",
                    priority=6
                ))
        
        # Energy constraints
        for pattern, constraint_type in self._constraint_patterns["energy"]:
            match = re.search(pattern, intent_lower)
            if match:
                value = int(match.group(1))
                constraints.append(Constraint(
                    type="energy",
                    value=value,
                    operator="lte",
                    priority=7
                ))
        
        # Privacy constraints
        for pattern, constraint_type in self._constraint_patterns["privacy"]:
            if re.search(pattern, intent_lower):
                constraints.append(Constraint(
                    type="privacy",
                    value="local_only",
                    operator="eq",
                    priority=9
                ))
        
        # Device-specific constraints
        if entities.get("device_types"):
            constraints.append(Constraint(
                type="device_availability",
                value=entities["device_types"],
                operator="in",
                priority=5
            ))
        
        # Location constraints
        if entities.get("locations"):
            constraints.append(Constraint(
                type="location",
                value=entities["locations"],
                operator="in",
                priority=4
            ))
        
        # Default constraints
        if not constraints:
            constraints.extend([
                Constraint(
                    type="latency",
                    value=5000,  # 5 seconds default
                    operator="lte",
                    priority=3
                ),
                Constraint(
                    type="cost",
                    value=1.0,  # $1 default
                    operator="lte",
                    priority=2
                )
            ])
        
        return constraints
    
    def _calculate_confidence(self, intent: str, entities: Dict[str, Any]) -> float:
        """Calculate confidence score for the translation."""
        confidence = 0.5  # Base confidence
        
        # Boost confidence based on pattern matches
        intent_lower = intent.lower()
        
        # Pattern matches
        pattern_matches = 0
        total_patterns = 0
        
        for category, patterns in self._patterns.items():
            total_patterns += len(patterns)
            for pattern in patterns:
                if re.search(pattern, intent_lower):
                    pattern_matches += 1
        
        if total_patterns > 0:
            confidence += (pattern_matches / total_patterns) * 0.3
        
        # Entity extraction
        if entities.get("device_types"):
            confidence += 0.1
        
        if entities.get("actions"):
            confidence += 0.1
        
        if entities.get("numeric_values"):
            confidence += 0.1
        
        # Cap at 1.0
        return min(confidence, 1.0)
    
    async def validate_intent(self, intent: str) -> Dict[str, Any]:
        """Validate an intent and provide feedback."""
        translation = await self.translate(intent)
        
        validation = {
            "valid": translation.confidence > 0.6,
            "confidence": translation.confidence,
            "suggestions": [],
            "warnings": []
        }
        
        # Generate suggestions for low confidence
        if translation.confidence < 0.6:
            validation["suggestions"].append(
                "Consider being more specific about the desired action or target devices"
            )
        
        # Check for missing critical information
        if not translation.goals:
            validation["warnings"].append("No clear goals identified")
        
        if not translation.constraints:
            validation["warnings"].append("No constraints specified")
        
        # Check for conflicting goals
        goal_targets = [goal.target for goal in translation.goals]
        if "energy" in goal_targets and "performance" in goal_targets:
            validation["warnings"].append("Conflicting goals: energy optimization vs performance")
        
        return validation
