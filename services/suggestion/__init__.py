"""
Tethral Suggestion Engine Package

A comprehensive suggestion engine that discovers meaningful device and service combinations,
evaluates them for feasibility and value, and provides intelligent recommendations.

Main Components:
- SuggestionEngine: Main orchestrator for the suggestion pipeline
- DeviceIngestionService: Normalizes devices and services into capabilities
- PowersetGenerator: Generates combinations with intelligent pruning
- CombinationEvaluator: Evaluates combinations for feasibility and value
- RecommendationPackager: Creates user-friendly recommendation cards
- OrchestrationAdapter: Converts recommendations into executable plans
- FeedbackService: Records user feedback and updates learning overlays
- LLMBridge: Provides clarifying suggestions when needed

Usage:
    from services.suggestion import SuggestionEngine, SuggestionRequest
    
    engine = SuggestionEngine()
    await engine.start()
    
    request = SuggestionRequest(
        user_id="user123",
        session_id="session456",
        context_hints={"location": "home"}
    )
    
    response = await engine.generate_suggestions(request)
    print(f"Generated {len(response.recommendations)} recommendations")
"""

from .engine import SuggestionEngine, SuggestionStatus
from .models import SuggestionConfig
from .models import (
    SuggestionRequest, SuggestionResponse, DeviceCapability, ServiceCapability,
    ContextSnapshot, CombinationCandidate, OutcomeTemplate, RecommendationCard,
    ExecutionPlan, UserOverlay, SituationPolicy, CapabilityType, PrivacyLevel,
    SafetyLevel, EffortLevel, WhatIfItem, FeedbackRecord
)
from .ingestion import DeviceIngestionService, IngestionResult
from .powerset import PowersetGenerator, PowersetConfig
from .evaluation import CombinationEvaluator, EvaluationResult
from .recommendation import RecommendationPackager
from .orchestration import OrchestrationAdapter
from .feedback import FeedbackService
from .llm_bridge import LLMBridge

__all__ = [
    # Main engine
    "SuggestionEngine",
    "SuggestionConfig", 
    "SuggestionStatus",
    
    # Models
    "SuggestionRequest",
    "SuggestionResponse",
    "DeviceCapability",
    "ServiceCapability",
    "ContextSnapshot",
    "CombinationCandidate",
    "OutcomeTemplate",
    "RecommendationCard",
    "ExecutionPlan",
    "UserOverlay",
    "SituationPolicy",
    "CapabilityType",
    "PrivacyLevel",
    "SafetyLevel",
    "EffortLevel",
    "WhatIfItem",
    "FeedbackRecord",
    
    # Services
    "DeviceIngestionService",
    "IngestionResult",
    "PowersetGenerator",
    "PowersetConfig",
    "CombinationEvaluator",
    "EvaluationResult",
    "RecommendationPackager",
    "OrchestrationAdapter",
    "FeedbackService",
    "LLMBridge"
]

__version__ = "1.0.0"
__author__ = "Tethral Team"
__description__ = "Tethral Suggestion Engine - Intelligent device and service combination discovery"
