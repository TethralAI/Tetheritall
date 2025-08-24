"""
Feedback Service
Records user feedback and updates learning overlays for continuous improvement.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json

from .models import (
    FeedbackRecord, UserOverlay, ContextSnapshot, RecommendationCard
)

logger = logging.getLogger(__name__)


class FeedbackService:
    """
    Service for recording and processing user feedback.
    
    Implements B6 from the spec:
    - Record user feedback signals
    - Update user overlay with preference drifts
    - Boost accepted patterns and penalize rejected ones
    - Narrow or widen suggestion sets based on user behavior
    """
    
    def __init__(self):
        self._feedback_history: Dict[str, List[FeedbackRecord]] = {}
        self._user_overlays: Dict[str, UserOverlay] = {}
        self._running = False
        
    async def start(self):
        """Start the feedback service."""
        self._running = True
        logger.info("Feedback service started")
        
    async def stop(self):
        """Stop the feedback service."""
        self._running = False
        logger.info("Feedback service stopped")
        
    async def record_feedback(
        self,
        user_id: str,
        recommendation_id: str,
        feedback_type: str,
        feedback_data: Optional[Dict[str, Any]] = None
    ):
        """
        Record user feedback for a recommendation.
        
        Args:
            user_id: User identifier
            recommendation_id: Recommendation identifier
            feedback_type: Type of feedback (accept, reject, snooze, edit, execute)
            feedback_data: Additional feedback data
        """
        try:
            feedback_record = FeedbackRecord(
                user_id=user_id,
                recommendation_id=recommendation_id,
                feedback_type=feedback_type,
                feedback_data=feedback_data or {},
                timestamp=datetime.utcnow()
            )
            
            # Store feedback
            if user_id not in self._feedback_history:
                self._feedback_history[user_id] = []
            self._feedback_history[user_id].append(feedback_record)
            
            # Update user overlay
            await self._update_user_overlay(user_id, feedback_record)
            
            logger.info(f"Recorded {feedback_type} feedback for user {user_id}, recommendation {recommendation_id}")
            
        except Exception as e:
            logger.error(f"Error recording feedback: {e}")
    
    async def record_execution(
        self,
        user_id: str,
        recommendation_id: str,
        success: bool,
        user_feedback: str
    ):
        """
        Record execution feedback for a recommendation.
        
        Args:
            user_id: User identifier
            recommendation_id: Recommendation identifier
            success: Whether execution was successful
            user_feedback: User's feedback about execution
        """
        feedback_data = {
            "execution_success": success,
            "user_feedback": user_feedback
        }
        
        await self.record_feedback(
            user_id=user_id,
            recommendation_id=recommendation_id,
            feedback_type="execute",
            feedback_data=feedback_data
        )
    
    async def get_user_overlay(self, user_id: str) -> Optional[UserOverlay]:
        """Get user overlay for a user."""
        return self._user_overlays.get(user_id)
    
    async def update_user_overlay(self, user_id: str, overlay: UserOverlay):
        """Update user overlay for a user."""
        self._user_overlays[user_id] = overlay
        overlay.updated_at = datetime.utcnow()
    
    async def _update_user_overlay(self, user_id: str, feedback_record: FeedbackRecord):
        """Update user overlay based on feedback."""
        # Get or create user overlay
        if user_id not in self._user_overlays:
            self._user_overlays[user_id] = UserOverlay(user_id=user_id)
        
        overlay = self._user_overlays[user_id]
        
        # Update based on feedback type
        if feedback_record.feedback_type == "accept":
            await self._handle_accept_feedback(overlay, feedback_record)
        elif feedback_record.feedback_type == "reject":
            await self._handle_reject_feedback(overlay, feedback_record)
        elif feedback_record.feedback_type == "snooze":
            await self._handle_snooze_feedback(overlay, feedback_record)
        elif feedback_record.feedback_type == "edit":
            await self._handle_edit_feedback(overlay, feedback_record)
        elif feedback_record.feedback_type == "execute":
            await self._handle_execute_feedback(overlay, feedback_record)
        
        # Update timestamp
        overlay.updated_at = datetime.utcnow()
    
    async def _handle_accept_feedback(self, overlay: UserOverlay, feedback_record: FeedbackRecord):
        """Handle accept feedback."""
        # Boost the pattern
        pattern_key = self._extract_pattern_key(feedback_record)
        if pattern_key:
            # Add to accepted patterns
            accepted_pattern = {
                "pattern_key": pattern_key,
                "timestamp": feedback_record.timestamp,
                "context": feedback_record.feedback_data.get("context", {}),
                "strength": 1.0
            }
            overlay.accepted_patterns.append(accepted_pattern)
            
            # Update device affinities if available
            if "device_ids" in feedback_record.feedback_data:
                for device_id in feedback_record.feedback_data["device_ids"]:
                    current_affinity = overlay.device_affinities.get(device_id, 0.5)
                    overlay.device_affinities[device_id] = min(1.0, current_affinity + 0.1)
            
            # Update room affinities if available
            if "rooms" in feedback_record.feedback_data:
                for room in feedback_record.feedback_data["rooms"]:
                    current_affinity = overlay.room_affinities.get(room, 0.5)
                    overlay.room_affinities[room] = min(1.0, current_affinity + 0.05)
    
    async def _handle_reject_feedback(self, overlay: UserOverlay, feedback_record: FeedbackRecord):
        """Handle reject feedback."""
        # Penalize the pattern
        pattern_key = self._extract_pattern_key(feedback_record)
        if pattern_key:
            # Add to rejected patterns
            rejected_pattern = {
                "pattern_key": pattern_key,
                "timestamp": feedback_record.timestamp,
                "context": feedback_record.feedback_data.get("context", {}),
                "strength": 1.0,
                "reason": feedback_record.feedback_data.get("reason", "unknown")
            }
            overlay.rejected_patterns.append(rejected_pattern)
            
            # Update device affinities if available
            if "device_ids" in feedback_record.feedback_data:
                for device_id in feedback_record.feedback_data["device_ids"]:
                    current_affinity = overlay.device_affinities.get(device_id, 0.5)
                    overlay.device_affinities[device_id] = max(0.0, current_affinity - 0.1)
            
            # Update room affinities if available
            if "rooms" in feedback_record.feedback_data:
                for room in feedback_record.feedback_data["rooms"]:
                    current_affinity = overlay.room_affinities.get(room, 0.5)
                    overlay.room_affinities[room] = max(0.0, current_affinity - 0.05)
    
    async def _handle_snooze_feedback(self, overlay: UserOverlay, feedback_record: FeedbackRecord):
        """Handle snooze feedback."""
        # Snooze is a mild negative signal
        pattern_key = self._extract_pattern_key(feedback_record)
        if pattern_key:
            rejected_pattern = {
                "pattern_key": pattern_key,
                "timestamp": feedback_record.timestamp,
                "context": feedback_record.feedback_data.get("context", {}),
                "strength": 0.5,  # Lower strength for snooze
                "reason": "snoozed"
            }
            overlay.rejected_patterns.append(rejected_pattern)
    
    async def _handle_edit_feedback(self, overlay: UserOverlay, feedback_record: FeedbackRecord):
        """Handle edit feedback."""
        # Edit shows interest but with modifications
        pattern_key = self._extract_pattern_key(feedback_record)
        if pattern_key:
            # Record the edit
            accepted_pattern = {
                "pattern_key": pattern_key,
                "timestamp": feedback_record.timestamp,
                "context": feedback_record.feedback_data.get("context", {}),
                "strength": 0.7,  # Moderate strength for edits
                "edits": feedback_record.feedback_data.get("edits", {})
            }
            overlay.accepted_patterns.append(accepted_pattern)
            
            # Update preferences based on edits
            if "preference_changes" in feedback_record.feedback_data:
                changes = feedback_record.feedback_data["preference_changes"]
                if "energy_vs_comfort_bias" in changes:
                    overlay.energy_vs_comfort_bias = changes["energy_vs_comfort_bias"]
                if "safety_vs_convenience_bias" in changes:
                    overlay.safety_vs_convenience_bias = changes["safety_vs_convenience_bias"]
                if "privacy_vs_functionality_bias" in changes:
                    overlay.privacy_vs_functionality_bias = changes["privacy_vs_functionality_bias"]
    
    async def _handle_execute_feedback(self, overlay: UserOverlay, feedback_record: FeedbackRecord):
        """Handle execute feedback."""
        # Execution is a strong positive signal
        pattern_key = self._extract_pattern_key(feedback_record)
        if pattern_key:
            success = feedback_record.feedback_data.get("execution_success", True)
            
            if success:
                # Strong positive signal for successful execution
                accepted_pattern = {
                    "pattern_key": pattern_key,
                    "timestamp": feedback_record.timestamp,
                    "context": feedback_record.feedback_data.get("context", {}),
                    "strength": 1.5,  # Higher strength for successful execution
                    "execution_success": True
                }
                overlay.accepted_patterns.append(accepted_pattern)
            else:
                # Mild negative signal for failed execution
                rejected_pattern = {
                    "pattern_key": pattern_key,
                    "timestamp": feedback_record.timestamp,
                    "context": feedback_record.feedback_data.get("context", {}),
                    "strength": 0.3,  # Lower strength for execution failure
                    "reason": "execution_failed"
                }
                overlay.rejected_patterns.append(rejected_pattern)
    
    def _extract_pattern_key(self, feedback_record: FeedbackRecord) -> Optional[str]:
        """Extract pattern key from feedback record."""
        # This would extract a pattern key based on the recommendation
        # For now, use a simple hash of the recommendation ID
        return f"pattern_{feedback_record.recommendation_id[:8]}"
    
    async def get_feedback_summary(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get feedback summary for a user."""
        if user_id not in self._feedback_history:
            return {
                "total_feedback": 0,
                "feedback_by_type": {},
                "recent_activity": []
            }
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        recent_feedback = [
            f for f in self._feedback_history[user_id]
            if f.timestamp >= cutoff_date
        ]
        
        # Count by type
        feedback_by_type = {}
        for feedback in recent_feedback:
            feedback_type = feedback.feedback_type
            feedback_by_type[feedback_type] = feedback_by_type.get(feedback_type, 0) + 1
        
        return {
            "total_feedback": len(recent_feedback),
            "feedback_by_type": feedback_by_type,
            "recent_activity": [
                {
                    "timestamp": f.timestamp.isoformat(),
                    "type": f.feedback_type,
                    "recommendation_id": f.recommendation_id
                }
                for f in recent_feedback[-10:]  # Last 10 feedback items
            ]
        }
    
    async def cleanup_old_feedback(self, days: int = 90):
        """Clean up old feedback records."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        for user_id in list(self._feedback_history.keys()):
            self._feedback_history[user_id] = [
                f for f in self._feedback_history[user_id]
                if f.timestamp >= cutoff_date
            ]
            
            # Remove user if no feedback remains
            if not self._feedback_history[user_id]:
                del self._feedback_history[user_id]
        
        logger.info(f"Cleaned up feedback older than {days} days")
    
    async def decay_pattern_strengths(self):
        """Decay pattern strengths over time."""
        current_time = datetime.utcnow()
        decay_factor = 0.95  # 5% decay per day
        
        for user_id, overlay in self._user_overlays.items():
            # Decay accepted patterns
            for pattern in overlay.accepted_patterns:
                days_old = (current_time - pattern["timestamp"]).days
                if days_old > 0:
                    pattern["strength"] *= (decay_factor ** days_old)
            
            # Decay rejected patterns
            for pattern in overlay.rejected_patterns:
                days_old = (current_time - pattern["timestamp"]).days
                if days_old > 0:
                    pattern["strength"] *= (decay_factor ** days_old)
            
            # Remove very weak patterns
            overlay.accepted_patterns = [
                p for p in overlay.accepted_patterns
                if p["strength"] > 0.1
            ]
            overlay.rejected_patterns = [
                p for p in overlay.rejected_patterns
                if p["strength"] > 0.1
            ]
        
        logger.info("Applied pattern strength decay")
