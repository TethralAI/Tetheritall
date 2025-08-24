"""
Tethral Suggestion Engine
Main engine that orchestrates the end-to-end suggestion pipeline.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import time
import uuid
from dataclasses import dataclass
from enum import Enum

from shared.config.settings import settings
from shared.database.api_database import get_session_factory, session_scope

from .ingestion import DeviceIngestionService
from .powerset import PowersetGenerator
from .evaluation import CombinationEvaluator
from .recommendation import RecommendationPackager
from .orchestration import OrchestrationAdapter
from .feedback import FeedbackService
from .llm_bridge import LLMBridge
from .models import (
    SuggestionRequest, SuggestionResponse, DeviceCapability, ServiceCapability,
    ContextSnapshot, CombinationCandidate, OutcomeTemplate, RecommendationCard,
    ExecutionPlan, UserOverlay, SituationPolicy, SuggestionConfig
)

logger = logging.getLogger(__name__)


class SuggestionStatus(Enum):
    """Suggestion processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"





class SuggestionEngine:
    """
    Main suggestion engine that orchestrates the end-to-end pipeline.
    
    Pipeline:
    1. Ingest current devices and services
    2. Generate powerset of combinations
    3. Evaluate combinations for feasibility and value
    4. Provide recommendations
    5. Execute selected combinations
    6. Learn from feedback
    """
    
    def __init__(self, config: Optional[SuggestionConfig] = None):
        self.config = config or SuggestionConfig()
        self._running = False
        self._session_factory = get_session_factory(settings.database_url)
        
        # Core pipeline components
        self.ingestion_service = DeviceIngestionService()
        self.powerset_generator = PowersetGenerator(self.config)
        self.evaluator = CombinationEvaluator()
        self.recommendation_packager = RecommendationPackager()
        self.orchestration_adapter = OrchestrationAdapter()
        self.feedback_service = FeedbackService()
        self.llm_bridge = LLMBridge()
        
        # State management
        self._active_requests: Dict[str, SuggestionRequest] = {}
        self._user_overlays: Dict[str, UserOverlay] = {}
        self._situation_policies: Dict[str, SituationPolicy] = {}
        
        # Monitoring
        self._request_history: List[Dict[str, Any]] = []
        self._performance_metrics: Dict[str, float] = {}
        
    async def start(self):
        """Start the suggestion engine."""
        self._running = True
        
        # Initialize components
        await self.ingestion_service.start()
        await self.feedback_service.start()
        
        # Load user overlays from storage
        await self._load_user_overlays()
        
        logger.info("Suggestion engine started")
        
    async def stop(self):
        """Stop the suggestion engine."""
        self._running = False
        
        # Stop components
        await self.ingestion_service.stop()
        await self.feedback_service.stop()
        
        # Save user overlays
        await self._save_user_overlays()
        
        logger.info("Suggestion engine stopped")
        
    async def generate_suggestions(
        self, 
        request: SuggestionRequest
    ) -> SuggestionResponse:
        """
        Main entry point for generating suggestions.
        
        This implements the complete pipeline:
        1. Ingest devices and services
        2. Generate combinations
        3. Evaluate and rank
        4. Package recommendations
        5. Handle LLM fallback if needed
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            logger.info(f"Generating suggestions for request {request_id}")
            
            # Store active request
            self._active_requests[request_id] = request
            
            # Step 1: Ingest current devices and services
            ingestion_result = await self._ingest_devices_and_services(request)
            if not ingestion_result.success:
                return SuggestionResponse(
                    request_id=request_id,
                    status=SuggestionStatus.FAILED,
                    errors=[f"Ingestion failed: {ingestion_result.error}"]
                )
            
            # Step 2: Generate powerset of combinations
            combinations = await self._generate_combinations(
                ingestion_result.capability_graph,
                ingestion_result.context_snapshot
            )
            
            if not combinations:
                # Try LLM fallback for broader discovery
                if self.config.enable_llm_fallback:
                    llm_result = await self._llm_fallback(request, ingestion_result)
                    if llm_result:
                        return llm_result
                
                return SuggestionResponse(
                    request_id=request_id,
                    status=SuggestionStatus.PARTIAL,
                    recommendations=[],
                    warnings=["No combinations found. Consider adding more devices or services."]
                )
            
            # Step 3: Evaluate combinations
            evaluation_result = await self._evaluate_combinations(
                combinations,
                ingestion_result.context_snapshot,
                request.user_id
            )
            
            # Step 4: Package recommendations
            recommendations = await self._package_recommendations(
                evaluation_result,
                request.user_id,
                request.session_id
            )
            
            # Step 5: Generate what-if analysis
            what_if_items = await self._generate_what_if_analysis(
                ingestion_result.capability_graph,
                evaluation_result.missing_capabilities
            )
            
            # Calculate performance metrics
            processing_time = time.time() - start_time
            self._performance_metrics[request_id] = processing_time
            
            return SuggestionResponse(
                request_id=request_id,
                status=SuggestionStatus.COMPLETED,
                recommendations=recommendations,
                what_if_items=what_if_items,
                context_snapshot=ingestion_result.context_snapshot,
                processing_time_ms=int(processing_time * 1000)
            )
            
        except Exception as e:
            logger.error(f"Error generating suggestions for request {request_id}: {e}")
            return SuggestionResponse(
                request_id=request_id,
                status=SuggestionStatus.FAILED,
                errors=[f"Internal error: {str(e)}"]
            )
        finally:
            # Clean up active request
            self._active_requests.pop(request_id, None)
    
    async def execute_suggestion(
        self, 
        request_id: str, 
        recommendation_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Execute a selected suggestion through the orchestration system."""
        try:
            # Get the original request
            request = self._active_requests.get(request_id)
            if not request:
                return {"success": False, "error": "Request not found"}
            
            # Convert recommendation to execution plan
            plan = await self._create_execution_plan(recommendation_id, user_id)
            
            # Execute through orchestration adapter
            execution_result = await self.orchestration_adapter.execute_plan(plan)
            
            # Record feedback for learning
            await self.feedback_service.record_execution(
                user_id=user_id,
                recommendation_id=recommendation_id,
                success=execution_result["success"],
                user_feedback="executed"
            )
            
            return execution_result
            
        except Exception as e:
            logger.error(f"Error executing suggestion: {e}")
            return {"success": False, "error": str(e)}
    
    async def record_feedback(
        self, 
        user_id: str, 
        recommendation_id: str, 
        feedback_type: str,
        feedback_data: Optional[Dict[str, Any]] = None
    ):
        """Record user feedback for learning."""
        await self.feedback_service.record_feedback(
            user_id=user_id,
            recommendation_id=recommendation_id,
            feedback_type=feedback_type,
            feedback_data=feedback_data or {}
        )
    
    async def _ingest_devices_and_services(self, request: SuggestionRequest):
        """Step 1: Ingest and normalize devices and services."""
        return await self.ingestion_service.ingest(
            user_id=request.user_id,
            session_id=request.session_id,
            context_hints=request.context_hints
        )
    
    async def _generate_combinations(
        self, 
        capability_graph: Dict[str, Any],
        context_snapshot: ContextSnapshot
    ) -> List[CombinationCandidate]:
        """Step 2: Generate powerset of combinations."""
        return await self.powerset_generator.generate_combinations(
            capability_graph=capability_graph,
            context_snapshot=context_snapshot,
            time_budget_ms=self.config.time_budget_ms
        )
    
    async def _evaluate_combinations(
        self,
        combinations: List[CombinationCandidate],
        context_snapshot: ContextSnapshot,
        user_id: str
    ):
        """Step 3: Evaluate combinations for feasibility and value."""
        return await self.evaluator.evaluate_combinations(
            combinations=combinations,
            context_snapshot=context_snapshot,
            user_id=user_id,
            user_overlay=self._user_overlays.get(user_id)
        )
    
    async def _package_recommendations(
        self,
        evaluation_result,
        user_id: str,
        session_id: str
    ) -> List[RecommendationCard]:
        """Step 4: Package recommendations into user-friendly cards."""
        return await self.recommendation_packager.create_recommendations(
            evaluation_result=evaluation_result,
            user_id=user_id,
            session_id=session_id
        )
    
    async def _generate_what_if_analysis(
        self,
        capability_graph: Dict[str, Any],
        missing_capabilities: List[str]
    ) -> List[Dict[str, Any]]:
        """Generate what-if analysis for missing capabilities."""
        return await self.recommendation_packager.create_what_if_items(
            capability_graph=capability_graph,
            missing_capabilities=missing_capabilities
        )
    
    async def _llm_fallback(
        self, 
        request: SuggestionRequest,
        ingestion_result
    ) -> Optional[SuggestionResponse]:
        """Use LLM bridge when insufficient combinations are found."""
        try:
            llm_result = await self.llm_bridge.generate_clarifying_suggestions(
                request=request,
                ingestion_result=ingestion_result
            )
            
            if llm_result:
                return SuggestionResponse(
                    request_id=str(uuid.uuid4()),
                    status=SuggestionStatus.PARTIAL,
                    recommendations=llm_result.recommendations,
                    warnings=["Used LLM fallback for broader discovery"],
                    llm_generated=True
                )
        except Exception as e:
            logger.error(f"LLM fallback failed: {e}")
        
        return None
    
    async def _create_execution_plan(
        self, 
        recommendation_id: str, 
        user_id: str
    ) -> ExecutionPlan:
        """Create execution plan from recommendation."""
        # This would convert a recommendation into an orchestration plan
        # Implementation depends on the recommendation structure
        pass
    
    async def _load_user_overlays(self):
        """Load user overlays from persistent storage."""
        # Implementation for loading user preferences and learning data
        pass
    
    async def _save_user_overlays(self):
        """Save user overlays to persistent storage."""
        # Implementation for saving user preferences and learning data
        pass
