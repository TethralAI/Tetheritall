"""
LLM Bridge
Provides clarifying suggestions when the suggestion engine needs help.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json

from .models import (
    SuggestionRequest, RecommendationCard, ContextSnapshot, CapabilityType
)

logger = logging.getLogger(__name__)


class LLMBridge:
    """
    Bridge to LLM for clarifying suggestions when needed.
    
    Implements F1-F3 from the spec:
    - When to call LLM (missing signals, few suggestions, unclear intent)
    - What to send (compact description, top candidates, targeted questions)
    - Expected return (explanation or answers for re-ranking)
    """
    
    def __init__(self):
        self._llm_client = None  # Would connect to LLM service
        self._call_history: List[Dict[str, Any]] = []
        
    async def generate_clarifying_suggestions(
        self,
        request: SuggestionRequest,
        ingestion_result
    ) -> Optional[Dict[str, Any]]:
        """
        Generate clarifying suggestions using LLM.
        
        Args:
            request: Original suggestion request
            ingestion_result: Result from device ingestion
            
        Returns:
            LLM-generated suggestions or None
        """
        try:
            # Step 1: Determine if LLM call is needed
            if not await self._should_call_llm(request, ingestion_result):
                return None
            
            # Step 2: Prepare compact brief
            brief = await self._prepare_compact_brief(request, ingestion_result)
            
            # Step 3: Generate targeted questions
            questions = await self._generate_targeted_questions(request, ingestion_result)
            
            # Step 4: Call LLM
            llm_response = await self._call_llm(brief, questions)
            
            # Step 5: Process response
            suggestions = await self._process_llm_response(llm_response, request)
            
            # Step 6: Record call
            self._record_llm_call(request, brief, questions, llm_response, suggestions)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error generating LLM suggestions: {e}")
            return None
    
    async def _should_call_llm(
        self,
        request: SuggestionRequest,
        ingestion_result
    ) -> bool:
        """Determine if LLM call is needed."""
        # Check if required signals are missing
        if not ingestion_result.context_snapshot:
            return True
        
        # Check if we have too few capabilities
        capability_count = len(ingestion_result.capability_graph.get("capabilities", {}))
        if capability_count < 2:
            return True
        
        # Check if user has repeatedly rejected similar suggestions
        # This would require access to feedback history
        if request.context_hints.get("repeated_rejections", False):
            return True
        
        return False
    
    async def _prepare_compact_brief(
        self,
        request: SuggestionRequest,
        ingestion_result
    ) -> Dict[str, Any]:
        """Prepare compact brief for LLM."""
        # Extract device classes and key capabilities
        device_classes = []
        key_capabilities = []
        
        for device_id, device_info in ingestion_result.capability_graph.get("devices", {}).items():
            device_class = f"{device_info['brand']} {device_info['model']}"
            device_classes.append(device_class)
            
            for capability in device_info.get("capabilities", []):
                key_capabilities.append(capability["type"])
        
        # Extract service capabilities
        for service_id, service_info in ingestion_result.capability_graph.get("services", {}).items():
            key_capabilities.append(service_info["type"])
        
        # Create compact brief
        brief = {
            "user_context": {
                "time_of_day": ingestion_result.context_snapshot.time_of_day.strftime("%H:%M") if ingestion_result.context_snapshot else "unknown",
                "is_weekend": ingestion_result.context_snapshot.is_weekend if ingestion_result.context_snapshot else False,
                "is_quiet_hours": ingestion_result.context_snapshot.is_quiet_hours if ingestion_result.context_snapshot else False,
                "user_present": ingestion_result.context_snapshot.user_present if ingestion_result.context_snapshot else True
            },
            "device_classes": list(set(device_classes)),
            "key_capabilities": list(set(key_capabilities)),
            "total_devices": len(ingestion_result.capability_graph.get("devices", {})),
            "total_services": len(ingestion_result.capability_graph.get("services", {})),
            "user_preferences": request.preferences
        }
        
        return brief
    
    async def _generate_targeted_questions(
        self,
        request: SuggestionRequest,
        ingestion_result
    ) -> List[str]:
        """Generate targeted questions for LLM."""
        questions = []
        
        # Check for missing capabilities
        available_capabilities = set()
        for device_id, device_info in ingestion_result.capability_graph.get("devices", {}).items():
            for capability in device_info.get("capabilities", []):
                available_capabilities.add(capability["type"])
        
        for service_id, service_info in ingestion_result.capability_graph.get("services", {}).items():
            available_capabilities.add(service_info["type"])
        
        # Question 1: Lighting preferences
        if "lighting" not in available_capabilities:
            questions.append("What type of lighting control would be most useful for your home? (e.g., motion-activated, schedule-based, weather-responsive)")
        
        # Question 2: Security preferences
        if "security" not in available_capabilities and "video" not in available_capabilities:
            questions.append("Are you interested in security monitoring features like motion detection or video surveillance?")
        
        # Question 3: Energy preferences
        if "energy" not in available_capabilities:
            questions.append("How important is energy efficiency and cost savings in your smart home setup?")
        
        # Limit to 3 questions
        return questions[:3]
    
    async def _call_llm(self, brief: Dict[str, Any], questions: List[str]) -> Dict[str, Any]:
        """Call LLM with brief and questions."""
        # This would make an actual call to an LLM service
        # For now, simulate the response
        
        prompt = self._build_llm_prompt(brief, questions)
        
        # Simulate LLM response
        response = {
            "explanation": "Based on your current setup, I can suggest several smart home enhancements that would work well with your devices.",
            "suggestions": [
                {
                    "title": "Smart Lighting Setup",
                    "description": "Add motion-activated lighting for convenience and energy savings",
                    "reasoning": "You have entry areas that would benefit from automatic lighting",
                    "effort": "low",
                    "value": "high"
                },
                {
                    "title": "Energy Monitoring",
                    "description": "Track and optimize your home's energy consumption",
                    "reasoning": "This would help you save money and reduce environmental impact",
                    "effort": "medium",
                    "value": "medium"
                }
            ],
            "answers": {
                "lighting_preference": "motion-activated",
                "security_interest": "moderate",
                "energy_priority": "high"
            }
        }
        
        return response
    
    def _build_llm_prompt(self, brief: Dict[str, Any], questions: List[str]) -> str:
        """Build prompt for LLM."""
        prompt = f"""
You are a smart home suggestion assistant. Based on the following information, provide helpful suggestions:

User Context:
- Time: {brief['user_context']['time_of_day']}
- Weekend: {brief['user_context']['is_weekend']}
- Quiet hours: {brief['user_context']['is_quiet_hours']}
- User present: {brief['user_context']['user_present']}

Available Devices: {', '.join(brief['device_classes'])}
Key Capabilities: {', '.join(brief['key_capabilities'])}
Total Devices: {brief['total_devices']}
Total Services: {brief['total_services']}

User Preferences: {brief['user_preferences']}

Questions to help provide better suggestions:
{chr(10).join(f"{i+1}. {q}" for i, q in enumerate(questions))}

Please provide:
1. A brief explanation of what would work well
2. 2-3 specific suggestions with reasoning
3. Answers to the questions above

Keep responses concise and practical.
"""
        return prompt
    
    async def _process_llm_response(
        self,
        llm_response: Dict[str, Any],
        request: SuggestionRequest
    ) -> Dict[str, Any]:
        """Process LLM response into suggestion format."""
        suggestions = []
        
        for suggestion in llm_response.get("suggestions", []):
            # Convert LLM suggestion to recommendation card format
            card = {
                "recommendation_id": f"llm_{len(suggestions)}",
                "title": suggestion["title"],
                "description": suggestion["description"],
                "rationale": [suggestion["reasoning"]],
                "category": "llm_generated",
                "confidence": 0.7,  # Moderate confidence for LLM suggestions
                "privacy_badge": "personal",
                "safety_badge": "safe",
                "effort_rating": suggestion["effort"],
                "llm_generated": True
            }
            suggestions.append(card)
        
        return {
            "recommendations": suggestions,
            "explanation": llm_response.get("explanation", ""),
            "answers": llm_response.get("answers", {}),
            "llm_generated": True
        }
    
    def _record_llm_call(
        self,
        request: SuggestionRequest,
        brief: Dict[str, Any],
        questions: List[str],
        llm_response: Dict[str, Any],
        suggestions: Dict[str, Any]
    ):
        """Record LLM call for analysis."""
        call_record = {
            "timestamp": datetime.utcnow(),
            "user_id": request.user_id,
            "brief": brief,
            "questions": questions,
            "llm_response": llm_response,
            "suggestions_generated": len(suggestions.get("recommendations", [])),
            "success": bool(suggestions)
        }
        
        self._call_history.append(call_record)
        
        # Keep only recent calls
        if len(self._call_history) > 100:
            self._call_history = self._call_history[-100:]
    
    async def get_llm_call_stats(self) -> Dict[str, Any]:
        """Get statistics about LLM calls."""
        if not self._call_history:
            return {
                "total_calls": 0,
                "success_rate": 0.0,
                "average_suggestions": 0.0
            }
        
        total_calls = len(self._call_history)
        successful_calls = sum(1 for call in self._call_history if call["success"])
        success_rate = successful_calls / total_calls if total_calls > 0 else 0.0
        
        total_suggestions = sum(call["suggestions_generated"] for call in self._call_history)
        average_suggestions = total_suggestions / total_calls if total_calls > 0 else 0.0
        
        return {
            "total_calls": total_calls,
            "success_rate": success_rate,
            "average_suggestions": average_suggestions,
            "recent_calls": len([c for c in self._call_history if (datetime.utcnow() - c["timestamp"]).days < 7])
        }
