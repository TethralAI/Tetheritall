"""
Suggestion Engine API
FastAPI endpoints for the Tethral Suggestion Engine.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from .engine import SuggestionEngine
from .models import SuggestionConfig
from .models import SuggestionRequest, SuggestionResponse

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/suggestions", tags=["suggestions"])

# Global suggestion engine instance
suggestion_engine: Optional[SuggestionEngine] = None


class SuggestionRequestModel(BaseModel):
    """Pydantic model for suggestion requests."""
    user_id: str
    session_id: Optional[str] = None
    context_hints: Dict[str, Any] = {}
    preferences: Dict[str, Any] = {}
    discovery_width: Optional[float] = None
    max_recommendations: int = 10
    include_what_if: bool = True
    enable_llm_fallback: bool = True


class FeedbackRequestModel(BaseModel):
    """Pydantic model for feedback requests."""
    recommendation_id: str
    feedback_type: str  # accept, reject, snooze, edit, execute
    feedback_data: Optional[Dict[str, Any]] = None


class ExecuteRequestModel(BaseModel):
    """Pydantic model for execution requests."""
    request_id: str
    recommendation_id: str


async def get_suggestion_engine() -> SuggestionEngine:
    """Dependency to get the suggestion engine instance."""
    if suggestion_engine is None:
        raise HTTPException(status_code=503, detail="Suggestion engine not initialized")
    return suggestion_engine


async def get_user_id(request: Request) -> str:
    """Extract user ID from request headers or query params."""
    # This would integrate with your authentication system
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        user_id = request.query_params.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    return user_id


@router.post("/generate", response_model=Dict[str, Any])
async def generate_suggestions(
    request_data: SuggestionRequestModel,
    engine: SuggestionEngine = Depends(get_suggestion_engine),
    user_id: str = Depends(get_user_id)
):
    """
    Generate suggestions for the user's current devices and services.
    
    This endpoint implements the complete suggestion pipeline:
    1. Ingest current devices and services
    2. Generate powerset of combinations
    3. Evaluate combinations for feasibility and value
    4. Provide recommendations
    5. Handle LLM fallback if needed
    """
    try:
        # Create suggestion request
        request = SuggestionRequest(
            user_id=user_id,
            session_id=request_data.session_id,
            context_hints=request_data.context_hints,
            preferences=request_data.preferences,
            discovery_width=request_data.discovery_width,
            max_recommendations=request_data.max_recommendations,
            include_what_if=request_data.include_what_if,
            enable_llm_fallback=request_data.enable_llm_fallback
        )
        
        # Generate suggestions
        response = await engine.generate_suggestions(request)
        
        # Convert to API response format
        api_response = {
            "request_id": response.request_id,
            "status": response.status,
            "recommendations": [
                {
                    "recommendation_id": rec.recommendation_id,
                    "title": rec.title,
                    "description": rec.description,
                    "rationale": rec.rationale,
                    "category": rec.category,
                    "confidence": rec.confidence,
                    "privacy_badge": rec.privacy_badge.value,
                    "safety_badge": rec.safety_badge.value,
                    "effort_rating": rec.effort_rating.value,
                    "tunable_controls": rec.tunable_controls,
                    "storyboard_preview": rec.storyboard_preview
                }
                for rec in response.recommendations
            ],
            "what_if_items": response.what_if_items,
            "processing_time_ms": response.processing_time_ms,
            "errors": response.errors,
            "warnings": response.warnings,
            "llm_generated": response.llm_generated
        }
        
        return api_response
        
    except Exception as e:
        logger.error(f"Error generating suggestions: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating suggestions: {str(e)}")


@router.post("/feedback")
async def record_feedback(
    feedback_data: FeedbackRequestModel,
    engine: SuggestionEngine = Depends(get_suggestion_engine),
    user_id: str = Depends(get_user_id)
):
    """
    Record user feedback for a recommendation.
    
    This endpoint records feedback for learning and continuous improvement.
    """
    try:
        await engine.record_feedback(
            user_id=user_id,
            recommendation_id=feedback_data.recommendation_id,
            feedback_type=feedback_data.feedback_type,
            feedback_data=feedback_data.feedback_data
        )
        
        return {
            "success": True,
            "message": f"Feedback recorded: {feedback_data.feedback_type}"
        }
        
    except Exception as e:
        logger.error(f"Error recording feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Error recording feedback: {str(e)}")


@router.post("/execute")
async def execute_suggestion(
    execute_data: ExecuteRequestModel,
    engine: SuggestionEngine = Depends(get_suggestion_engine),
    user_id: str = Depends(get_user_id)
):
    """
    Execute a selected suggestion.
    
    This endpoint converts a recommendation into an execution plan and runs it.
    """
    try:
        result = await engine.execute_suggestion(
            request_id=execute_data.request_id,
            recommendation_id=execute_data.recommendation_id,
            user_id=user_id
        )
        
        return {
            "success": result["success"],
            "plan_id": result.get("plan_id"),
            "execution_id": result.get("execution_id"),
            "status": result.get("status"),
            "details": result.get("details", {}),
            "error": result.get("error")
        }
        
    except Exception as e:
        logger.error(f"Error executing suggestion: {e}")
        raise HTTPException(status_code=500, detail=f"Error executing suggestion: {str(e)}")


@router.get("/status")
async def get_engine_status(
    engine: SuggestionEngine = Depends(get_suggestion_engine)
):
    """
    Get the status of the suggestion engine.
    """
    try:
        return {
            "status": "running" if engine._running else "stopped",
            "version": "1.0.0",
            "components": {
                "ingestion_service": "running",
                "powerset_generator": "ready",
                "evaluator": "ready",
                "packager": "ready",
                "orchestration_adapter": "ready",
                "feedback_service": "running",
                "llm_bridge": "ready"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting engine status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting engine status: {str(e)}")


@router.get("/stats")
async def get_engine_stats(
    engine: SuggestionEngine = Depends(get_suggestion_engine)
):
    """
    Get statistics about the suggestion engine.
    """
    try:
        # Get performance metrics
        performance_metrics = engine._performance_metrics
        
        # Get LLM bridge stats
        llm_stats = await engine.llm_bridge.get_llm_call_stats()
        
        return {
            "performance": {
                "total_requests": len(performance_metrics),
                "average_processing_time_ms": sum(performance_metrics.values()) / len(performance_metrics) if performance_metrics else 0
            },
            "llm_bridge": llm_stats,
            "user_overlays": len(engine._user_overlays),
            "active_requests": len(engine._active_requests)
        }
        
    except Exception as e:
        logger.error(f"Error getting engine stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting engine stats: {str(e)}")


async def initialize_suggestion_engine():
    """Initialize the global suggestion engine instance."""
    global suggestion_engine
    
    try:
        config = SuggestionConfig(
            max_combinations=1000,
            max_candidates_per_request=10,
            time_budget_ms=5000,
            enable_llm_fallback=True,
            local_learning_default=True,
            cloud_sync_optional=True
        )
        
        suggestion_engine = SuggestionEngine(config)
        await suggestion_engine.start()
        
        logger.info("Suggestion engine initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing suggestion engine: {e}")
        raise


async def shutdown_suggestion_engine():
    """Shutdown the global suggestion engine instance."""
    global suggestion_engine
    
    if suggestion_engine:
        try:
            await suggestion_engine.stop()
            logger.info("Suggestion engine shutdown successfully")
        except Exception as e:
            logger.error(f"Error shutting down suggestion engine: {e}")


# Add startup and shutdown events to the router
@router.on_event("startup")
async def startup_event():
    """Startup event for the suggestion engine."""
    await initialize_suggestion_engine()


@router.on_event("shutdown")
async def shutdown_event():
    """Shutdown event for the suggestion engine."""
    await shutdown_suggestion_engine()
