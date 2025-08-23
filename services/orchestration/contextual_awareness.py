"""
Contextual Awareness Agent

Maintains an always-fresh, privacy-safe picture of "what is true right now" so plans 
and resource assignments are correct, safe, and comfortable for the user.

This component handles:
- Signal ingestion from devices, apps, and services
- Normalization and entity binding
- Fusion and state estimation
- Capability graph maintenance
- Derived context and flags
- Privacy-safe querying and eventing
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict

from .models import (
    SignalDomain, ConfidenceLevel, FreshnessStatus, PrivacySensitivity,
    SignalSource, NormalizedSignal, Entity, EntityRelationship,
    CapabilityNode, CapabilityEdge, CapabilityGraph, DerivedFlag,
    ContextSnapshot, ContextQuery, ContextResponse, ContextEvent,
    ContextMetrics, IngestionConfig, FusionRule, DerivedFlagRecipe
)

logger = logging.getLogger(__name__)


@dataclass
class ContextualAwarenessConfig:
    """Configuration for the contextual awareness agent."""
    snapshot_interval_ms: int = 1000  # How often to create snapshots
    max_signal_age_ms: int = 30000  # Max age for signals to be considered fresh
    confidence_decay_rate: float = 0.1  # Rate at which confidence decays over time
    fusion_window_ms: int = 5000  # Window for signal fusion
    derived_flag_expiry_ms: int = 300000  # 5 minutes default expiry
    privacy_enforcement: bool = True
    data_minimization: bool = True
    retention_window_hours: int = 24
    health_check_interval_ms: int = 60000  # 1 minute
    max_entities_per_snapshot: int = 1000
    max_signals_per_snapshot: int = 10000


class ContextualAwareness:
    """
    Main contextual awareness agent that maintains the current state of the system.
    
    Mission: Maintain an always-fresh, privacy-safe picture of "what is true right now"
    so plans and resource assignments are correct, safe, and comfortable for the user.
    """
    
    def __init__(self, config: Optional[ContextualAwarenessConfig] = None):
        self.config = config or ContextualAwarenessConfig()
        self._running = False
        self._current_snapshot: Optional[ContextSnapshot] = None
        self._signals: Dict[str, NormalizedSignal] = {}
        self._entities: Dict[str, Entity] = {}
        self._relationships: Dict[str, EntityRelationship] = {}
        self._derived_flags: Dict[str, DerivedFlag] = {}
        self._capability_graph = CapabilityGraph()
        self._event_subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._metrics: Dict[str, ContextMetrics] = {}
        
        # Initialize subsystems
        self.ingestion = SignalIngestion(self.config)
        self.normalizer = SignalNormalizer()
        self.entity_binder = EntityBinder()
        self.fusion_engine = FusionEngine(self.config)
        self.capability_manager = CapabilityManager()
        self.flag_engine = DerivedFlagEngine(self.config)
        self.privacy_guard = PrivacyGuard()
        self.query_service = QueryService()
        self.event_service = EventService()
        self.health_monitor = HealthMonitor(self.config)
        
    async def start(self):
        """Start the contextual awareness agent."""
        self._running = True
        await self.ingestion.start()
        await self.normalizer.start()
        await self.entity_binder.start()
        await self.fusion_engine.start()
        await self.capability_manager.start()
        await self.flag_engine.start()
        await self.privacy_guard.start()
        await self.query_service.start()
        await self.event_service.start()
        await self.health_monitor.start()
        
        # Start background tasks
        asyncio.create_task(self._snapshot_loop())
        asyncio.create_task(self._cleanup_loop())
        
        logger.info("Contextual awareness agent started")
        
    async def stop(self):
        """Stop the contextual awareness agent."""
        self._running = False
        await self.ingestion.stop()
        await self.normalizer.stop()
        await self.entity_binder.stop()
        await self.fusion_engine.stop()
        await self.capability_manager.stop()
        await self.flag_engine.stop()
        await self.privacy_guard.stop()
        await self.query_service.stop()
        await self.event_service.stop()
        await self.health_monitor.stop()
        logger.info("Contextual awareness agent stopped")
        
    async def get_snapshot(self, query: ContextQuery) -> ContextResponse:
        """
        Get a context snapshot based on the query requirements.
        
        This applies privacy filtering and data minimization based on the consumer's scope.
        """
        if not self._running:
            raise RuntimeError("Contextual awareness agent is not running")
            
        try:
            logger.debug(f"Processing context query {query.query_id} from {query.consumer}")
            
            # Check if current snapshot is fresh enough
            if not self._is_snapshot_fresh(query.max_age_ms):
                await self._refresh_snapshot()
            
            # Apply privacy filtering
            filtered_snapshot = await self.privacy_guard.filter_snapshot(
                self._current_snapshot, query
            )
            
            # Calculate quality metrics
            freshness_score = self._calculate_freshness_score(filtered_snapshot)
            confidence_score = self._calculate_confidence_score(filtered_snapshot)
            privacy_compliance_score = self._calculate_privacy_compliance_score(query)
            
            # Collect warnings
            warnings = self._collect_warnings(filtered_snapshot, query)
            
            return ContextResponse(
                query_id=query.query_id,
                snapshot=filtered_snapshot,
                freshness_score=freshness_score,
                confidence_score=confidence_score,
                privacy_compliance_score=privacy_compliance_score,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Error processing context query {query.query_id}: {e}")
            return ContextResponse(
                query_id=query.query_id,
                snapshot=ContextSnapshot(snapshot_id="", timestamp=datetime.utcnow()),
                freshness_score=0.0,
                confidence_score=0.0,
                privacy_compliance_score=0.0,
                errors=[f"Query error: {str(e)}"]
            )
    
    async def subscribe_to_events(
        self, 
        event_types: List[str], 
        callback: Callable[[ContextEvent], None],
        subscriber_id: str
    ):
        """Subscribe to context change events."""
        for event_type in event_types:
            self._event_subscribers[event_type].append(callback)
        logger.info(f"Subscriber {subscriber_id} subscribed to events: {event_types}")
    
    async def unsubscribe_from_events(self, subscriber_id: str):
        """Unsubscribe from context change events."""
        # This is a simplified implementation - in practice you'd track subscribers more carefully
        logger.info(f"Subscriber {subscriber_id} unsubscribed from all events")
    
    async def add_signal(self, signal: NormalizedSignal):
        """Add a new signal to the context."""
        if not self._running:
            raise RuntimeError("Contextual awareness agent is not running")
            
        try:
            # Normalize the signal
            normalized_signal = await self.normalizer.normalize(signal)
            
            # Bind to entities
            entity_bindings = await self.entity_binder.bind_signal(normalized_signal)
            
            # Store the signal
            self._signals[normalized_signal.signal_id] = normalized_signal
            
            # Update fusion engine
            await self.fusion_engine.add_signal(normalized_signal)
            
            # Update derived flags
            await self.flag_engine.process_signal(normalized_signal)
            
            # Publish event
            event = ContextEvent(
                event_id=str(uuid.uuid4()),
                event_type="signal_added",
                timestamp=datetime.utcnow(),
                entity_id=entity_bindings.get("primary_entity"),
                new_value=normalized_signal.value,
                explanation=f"Signal {normalized_signal.field_name} from {normalized_signal.source.source_id}"
            )
            await self._publish_event(event)
            
            logger.debug(f"Added signal {normalized_signal.signal_id}")
            
        except Exception as e:
            logger.error(f"Error adding signal {signal.signal_id}: {e}")
    
    async def update_entity(self, entity: Entity):
        """Update an entity in the context."""
        if not self._running:
            raise RuntimeError("Contextual awareness agent is not running")
            
        try:
            old_entity = self._entities.get(entity.entity_id)
            self._entities[entity.entity_id] = entity
            
            # Update capability graph
            await self.capability_manager.update_entity(entity)
            
            # Publish event
            event = ContextEvent(
                event_id=str(uuid.uuid4()),
                event_type="entity_updated",
                timestamp=datetime.utcnow(),
                entity_id=entity.entity_id,
                old_value=old_entity.name if old_entity else None,
                new_value=entity.name,
                explanation=f"Entity {entity.entity_id} updated"
            )
            await self._publish_event(event)
            
            logger.debug(f"Updated entity {entity.entity_id}")
            
        except Exception as e:
            logger.error(f"Error updating entity {entity.entity_id}: {e}")
    
    async def get_metrics(self, snapshot_id: str) -> Optional[ContextMetrics]:
        """Get metrics for a specific snapshot."""
        return self._metrics.get(snapshot_id)
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get the health status of the contextual awareness system."""
        return await self.health_monitor.get_status()
    
    # Private methods
    
    async def _snapshot_loop(self):
        """Background loop for creating periodic snapshots."""
        while self._running:
            try:
                await self._refresh_snapshot()
                await asyncio.sleep(self.config.snapshot_interval_ms / 1000)
            except Exception as e:
                logger.error(f"Error in snapshot loop: {e}")
                await asyncio.sleep(1)
    
    async def _refresh_snapshot(self):
        """Refresh the current context snapshot."""
        try:
            # Get current signals
            current_signals = list(self._signals.values())
            
            # Get current derived flags
            current_flags = list(self._derived_flags.values())
            
            # Get current capability graph
            current_graph = await self.capability_manager.get_graph()
            
            # Get current entities and relationships
            current_entities = list(self._entities.values())
            current_relationships = list(self._relationships.values())
            
            # Create new snapshot
            snapshot_id = str(uuid.uuid4())
            new_snapshot = ContextSnapshot(
                snapshot_id=snapshot_id,
                timestamp=datetime.utcnow(),
                signals=current_signals,
                derived_flags=current_flags,
                capability_graph=current_graph,
                entities=current_entities,
                relationships=current_relationships
            )
            
            # Update current snapshot
            old_snapshot = self._current_snapshot
            self._current_snapshot = new_snapshot
            
            # Calculate metrics
            metrics = await self._calculate_snapshot_metrics(new_snapshot)
            self._metrics[snapshot_id] = metrics
            
            # Publish snapshot event
            event = ContextEvent(
                event_id=str(uuid.uuid4()),
                event_type="snapshot_created",
                timestamp=datetime.utcnow(),
                explanation=f"New snapshot {snapshot_id} created with {len(current_signals)} signals"
            )
            await self._publish_event(event)
            
            logger.debug(f"Created snapshot {snapshot_id}")
            
        except Exception as e:
            logger.error(f"Error refreshing snapshot: {e}")
    
    async def _cleanup_loop(self):
        """Background loop for cleaning up old data."""
        while self._running:
            try:
                await self._cleanup_old_data()
                await asyncio.sleep(3600)  # Run every hour
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_old_data(self):
        """Clean up old signals and data."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=self.config.retention_window_hours)
            
            # Remove old signals
            old_signals = [
                signal_id for signal_id, signal in self._signals.items()
                if signal.timestamp < cutoff_time
            ]
            for signal_id in old_signals:
                del self._signals[signal_id]
            
            # Remove old metrics
            old_metrics = [
                snapshot_id for snapshot_id, metrics in self._metrics.items()
                if metrics.created_at < cutoff_time
            ]
            for snapshot_id in old_metrics:
                del self._metrics[snapshot_id]
            
            if old_signals or old_metrics:
                logger.info(f"Cleaned up {len(old_signals)} old signals and {len(old_metrics)} old metrics")
                
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
    
    def _is_snapshot_fresh(self, max_age_ms: int) -> bool:
        """Check if the current snapshot is fresh enough."""
        if not self._current_snapshot:
            return False
        
        age_ms = (datetime.utcnow() - self._current_snapshot.timestamp).total_seconds() * 1000
        return age_ms <= max_age_ms
    
    def _calculate_freshness_score(self, snapshot: ContextSnapshot) -> float:
        """Calculate freshness score for a snapshot."""
        if not snapshot.signals:
            return 0.0
        
        now = datetime.utcnow()
        freshness_scores = []
        
        for signal in snapshot.signals:
            age_ms = (now - signal.timestamp).total_seconds() * 1000
            if age_ms <= 1000:  # 1 second
                freshness_scores.append(1.0)
            elif age_ms <= 5000:  # 5 seconds
                freshness_scores.append(0.8)
            elif age_ms <= 30000:  # 30 seconds
                freshness_scores.append(0.5)
            else:
                freshness_scores.append(0.1)
        
        return sum(freshness_scores) / len(freshness_scores)
    
    def _calculate_confidence_score(self, snapshot: ContextSnapshot) -> float:
        """Calculate confidence score for a snapshot."""
        if not snapshot.signals:
            return 0.0
        
        confidence_values = {
            ConfidenceLevel.UNKNOWN: 0.0,
            ConfidenceLevel.LOW: 0.25,
            ConfidenceLevel.MEDIUM: 0.5,
            ConfidenceLevel.HIGH: 0.75,
            ConfidenceLevel.VERY_HIGH: 1.0
        }
        
        scores = [confidence_values[signal.confidence] for signal in snapshot.signals]
        return sum(scores) / len(scores)
    
    def _calculate_privacy_compliance_score(self, query: ContextQuery) -> float:
        """Calculate privacy compliance score for a query."""
        # This would be based on the privacy guard's assessment
        return 1.0  # Placeholder
    
    def _collect_warnings(self, snapshot: ContextSnapshot, query: ContextQuery) -> List[str]:
        """Collect warnings about the snapshot."""
        warnings = []
        
        # Check for stale signals
        stale_signals = [
            signal for signal in snapshot.signals
            if signal.freshness == FreshnessStatus.STALE
        ]
        if stale_signals:
            warnings.append(f"{len(stale_signals)} signals are stale")
        
        # Check for low confidence signals
        low_confidence_signals = [
            signal for signal in snapshot.signals
            if signal.confidence in [ConfidenceLevel.UNKNOWN, ConfidenceLevel.LOW]
        ]
        if low_confidence_signals:
            warnings.append(f"{len(low_confidence_signals)} signals have low confidence")
        
        # Check for missing required flags
        missing_flags = [
            flag_name for flag_name in query.required_flags
            if not any(flag.name == flag_name for flag in snapshot.derived_flags)
        ]
        if missing_flags:
            warnings.append(f"Missing required flags: {missing_flags}")
        
        return warnings
    
    async def _calculate_snapshot_metrics(self, snapshot: ContextSnapshot) -> ContextMetrics:
        """Calculate metrics for a snapshot."""
        # Calculate freshness by domain
        freshness_by_domain = {}
        for domain in SignalDomain:
            domain_signals = [s for s in snapshot.signals if s.domain == domain]
            if domain_signals:
                freshness_scores = []
                for signal in domain_signals:
                    age_ms = (datetime.utcnow() - signal.timestamp).total_seconds() * 1000
                    if age_ms <= 5000:
                        freshness_scores.append(1.0)
                    elif age_ms <= 30000:
                        freshness_scores.append(0.5)
                    else:
                        freshness_scores.append(0.1)
                freshness_by_domain[domain] = sum(freshness_scores) / len(freshness_scores)
            else:
                freshness_by_domain[domain] = 0.0
        
        # Calculate confidence distribution
        confidence_distribution = defaultdict(int)
        for signal in snapshot.signals:
            confidence_distribution[signal.confidence] += 1
        
        return ContextMetrics(
            snapshot_id=snapshot.snapshot_id,
            freshness_percentile_by_domain=freshness_by_domain,
            confidence_distribution=dict(confidence_distribution),
            false_positive_rate=0.0,  # Would be calculated from historical data
            false_negative_rate=0.0,  # Would be calculated from historical data
            mean_detection_time_ms=100,  # Placeholder
            data_minimization_score=1.0  # Would be calculated by privacy guard
        )
    
    async def _publish_event(self, event: ContextEvent):
        """Publish an event to all subscribers."""
        subscribers = self._event_subscribers.get(event.event_type, [])
        for callback in subscribers:
            try:
                await callback(event)
            except Exception as e:
                logger.error(f"Error in event callback: {e}")


# Subsystems will be implemented in separate files
class SignalIngestion:
    """Pulls and subscribes to raw signals from devices, apps, and services."""
    
    def __init__(self, config: ContextualAwarenessConfig):
        self.config = config
    
    async def start(self):
        """Start the signal ingestion subsystem."""
        pass
    
    async def stop(self):
        """Stop the signal ingestion subsystem."""
        pass


class SignalNormalizer:
    """Converts everything to canonical units and schemas."""
    
    async def start(self):
        """Start the signal normalizer."""
        pass
    
    async def stop(self):
        """Stop the signal normalizer."""
        pass
    
    async def normalize(self, signal: NormalizedSignal) -> NormalizedSignal:
        """Normalize a signal."""
        # Implementation will be in signal_normalizer.py
        pass


class EntityBinder:
    """Maps each signal to a device entity, user, and zone."""
    
    async def start(self):
        """Start the entity binder."""
        pass
    
    async def stop(self):
        """Stop the entity binder."""
        pass
    
    async def bind_signal(self, signal: NormalizedSignal) -> Dict[str, str]:
        """Bind a signal to entities."""
        # Implementation will be in entity_binder.py
        pass


class FusionEngine:
    """Combines multiple signals into higher-confidence states."""
    
    def __init__(self, config: ContextualAwarenessConfig):
        self.config = config
    
    async def start(self):
        """Start the fusion engine."""
        pass
    
    async def stop(self):
        """Stop the fusion engine."""
        pass
    
    async def add_signal(self, signal: NormalizedSignal):
        """Add a signal to the fusion engine."""
        # Implementation will be in fusion_engine.py
        pass


class CapabilityManager:
    """Keeps a live graph of what each device can do."""
    
    async def start(self):
        """Start the capability manager."""
        pass
    
    async def stop(self):
        """Stop the capability manager."""
        pass
    
    async def update_entity(self, entity: Entity):
        """Update an entity in the capability graph."""
        # Implementation will be in capability_manager.py
        pass
    
    async def get_graph(self) -> CapabilityGraph:
        """Get the current capability graph."""
        # Implementation will be in capability_manager.py
        pass


class DerivedFlagEngine:
    """Computes higher-level flags and derived context."""
    
    def __init__(self, config: ContextualAwarenessConfig):
        self.config = config
    
    async def start(self):
        """Start the derived flag engine."""
        pass
    
    async def stop(self):
        """Stop the derived flag engine."""
        pass
    
    async def process_signal(self, signal: NormalizedSignal):
        """Process a signal to update derived flags."""
        # Implementation will be in derived_flag_engine.py
        pass


class PrivacyGuard:
    """Classifies every field by sensitivity and purpose."""
    
    async def start(self):
        """Start the privacy guard."""
        pass
    
    async def stop(self):
        """Stop the privacy guard."""
        pass
    
    async def filter_snapshot(self, snapshot: ContextSnapshot, query: ContextQuery) -> ContextSnapshot:
        """Filter a snapshot based on privacy requirements."""
        # Implementation will be in privacy_guard.py
        pass


class QueryService:
    """Provides point-in-time snapshots for planners and allocators."""
    
    async def start(self):
        """Start the query service."""
        pass
    
    async def stop(self):
        """Stop the query service."""
        pass


class EventService:
    """Publishes deltas when thresholds are crossed."""
    
    async def start(self):
        """Start the event service."""
        pass
    
    async def stop(self):
        """Stop the event service."""
        pass


class HealthMonitor:
    """Monitors ingestion lags, data gaps, and sensor drift."""
    
    def __init__(self, config: ContextualAwarenessConfig):
        self.config = config
    
    async def start(self):
        """Start the health monitor."""
        pass
    
    async def stop(self):
        """Stop the health monitor."""
        pass
    
    async def get_status(self) -> Dict[str, Any]:
        """Get the health status."""
        # Implementation will be in health_monitor.py
        pass
