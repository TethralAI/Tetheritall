"""
Event Manager
Handles event publishing, subscription, and notification.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
import json
import uuid

from .models import Event, EventType, EventPriority, EventFilter, EventSubscription
from shared.config.settings import settings

logger = logging.getLogger(__name__)


class EventManager:
    """Manages event publishing, subscription, and notification."""
    
    def __init__(self):
        self._subscriptions: Dict[str, EventSubscription] = {}
        self._event_queue: List[Event] = []
        self._event_history: List[Event] = []
        self._callbacks: Dict[str, List[Callable]] = {
            'event_published': [],
            'event_delivered': [],
            'event_failed': [],
            'subscription_added': [],
            'subscription_removed': []
        }
        self._event_processor_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._max_history_size = 10000  # Maximum number of events to keep in history
        
    async def start(self):
        """Start the event manager."""
        logger.info("Starting event manager")
        
        # Load existing events and subscriptions from database
        await self._load_events_from_database()
        await self._load_subscriptions_from_database()
        
        # Start background tasks
        self._event_processor_task = asyncio.create_task(self._process_event_queue())
        self._cleanup_task = asyncio.create_task(self._cleanup_old_events())
        
        logger.info("Event manager started")
        
    async def stop(self):
        """Stop the event manager."""
        logger.info("Stopping event manager")
        
        # Cancel background tasks
        if self._event_processor_task:
            self._event_processor_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
            
        # Save events and subscriptions to database
        await self._save_events_to_database()
        await self._save_subscriptions_to_database()
            
        logger.info("Event manager stopped")
        
    async def publish_event(self, event_type: EventType, source: str, data: Dict[str, Any] = None, 
                          priority: EventPriority = EventPriority.NORMAL, ttl: Optional[int] = None,
                          metadata: Dict[str, Any] = None) -> Event:
        """Publish an event."""
        try:
            # Create event
            event = Event(
                event_id=str(uuid.uuid4()),
                event_type=event_type,
                source=source,
                timestamp=datetime.utcnow(),
                data=data or {},
                metadata=metadata or {},
                priority=priority,
                ttl=ttl
            )
            
            # Add to queue
            self._event_queue.append(event)
            
            # Add to history
            self._event_history.append(event)
            
            # Keep history size manageable
            if len(self._event_history) > self._max_history_size:
                self._event_history = self._event_history[-self._max_history_size:]
                
            # Save to database
            await self._save_event_to_database(event)
                
            # Notify callbacks
            await self._notify_callbacks('event_published', event)
            
            logger.debug(f"Published event: {event.event_id} ({event_type.value}) from {source}")
            return event
            
        except Exception as e:
            logger.error(f"Error publishing event {event_type.value}: {e}")
            raise
            
    async def subscribe(self, subscriber_id: str, event_filter: EventFilter, 
                       callback: Optional[Callable] = None) -> str:
        """Subscribe to events with a filter."""
        try:
            # Create subscription
            subscription = EventSubscription(
                subscription_id=str(uuid.uuid4()),
                subscriber_id=subscriber_id,
                filter=event_filter,
                callback=callback
            )
            
            # Add subscription
            self._subscriptions[subscription.subscription_id] = subscription
            
            # Save to database
            await self._save_subscription_to_database(subscription)
            
            # Notify callbacks
            await self._notify_callbacks('subscription_added', subscription)
            
            logger.info(f"Added subscription {subscription.subscription_id} for subscriber {subscriber_id}")
            return subscription.subscription_id
            
        except Exception as e:
            logger.error(f"Error adding subscription for {subscriber_id}: {e}")
            raise
            
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events."""
        try:
            if subscription_id not in self._subscriptions:
                logger.warning(f"Subscription {subscription_id} not found")
                return False
                
            subscription = self._subscriptions[subscription_id]
            
            # Remove subscription
            del self._subscriptions[subscription_id]
            
            # Notify callbacks
            await self._notify_callbacks('subscription_removed', subscription)
            
            logger.info(f"Removed subscription {subscription_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing subscription {subscription_id}: {e}")
            return False
            
    async def get_subscriptions(self, subscriber_id: Optional[str] = None) -> List[EventSubscription]:
        """Get subscriptions with optional filtering by subscriber."""
        subscriptions = list(self._subscriptions.values())
        
        if subscriber_id:
            subscriptions = [sub for sub in subscriptions if sub.subscriber_id == subscriber_id]
            
        return subscriptions
        
    async def get_event_history(self, event_type: Optional[EventType] = None, 
                               source: Optional[str] = None, limit: int = 100) -> List[Event]:
        """Get event history with optional filtering."""
        events = list(self._event_history)
        
        # Apply filters
        if event_type:
            events = [event for event in events if event.event_type == event_type]
        if source:
            events = [event for event in events if event.source == source]
            
        # Sort by timestamp (newest first) and limit
        events.sort(key=lambda x: x.timestamp, reverse=True)
        return events[:limit]
        
    async def get_event_statistics(self) -> Dict[str, Any]:
        """Get event manager statistics."""
        total_events = len(self._event_history)
        queued_events = len(self._event_queue)
        active_subscriptions = len([sub for sub in self._subscriptions.values() if sub.active])
        
        # Event type distribution
        event_type_counts = {}
        for event in self._event_history:
            event_type = event.event_type.value
            event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1
            
        # Priority distribution
        priority_counts = {}
        for event in self._event_history:
            priority = event.priority.value
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
            
        # Source distribution
        source_counts = {}
        for event in self._event_history:
            source = event.source
            source_counts[source] = source_counts.get(source, 0) + 1
            
        return {
            'total_events': total_events,
            'queued_events': queued_events,
            'active_subscriptions': active_subscriptions,
            'event_type_distribution': event_type_counts,
            'priority_distribution': priority_counts,
            'source_distribution': source_counts
        }
        
    def add_callback(self, event: str, callback: Callable):
        """Add a callback for event manager events."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
            logger.debug(f"Added callback for event: {event}")
        else:
            logger.warning(f"Unknown event type: {event}")
            
    def remove_callback(self, event: str, callback: Callable):
        """Remove a callback for event manager events."""
        if event in self._callbacks and callback in self._callbacks[event]:
            self._callbacks[event].remove(callback)
            logger.debug(f"Removed callback for event: {event}")
            
    async def _process_event_queue(self):
        """Process events in the queue."""
        while True:
            try:
                if self._event_queue:
                    event = self._event_queue.pop(0)
                    await self._deliver_event(event)
                    
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing event queue: {e}")
                await asyncio.sleep(1)
                
    async def _deliver_event(self, event: Event):
        """Deliver event to matching subscribers."""
        try:
            # Check if event has expired
            if event.is_expired():
                logger.warning(f"Event expired: {event.event_id}")
                await self._notify_callbacks('event_failed', event, error="Event expired")
                return
                
            # Find matching subscriptions
            matching_subscriptions = []
            for subscription in self._subscriptions.values():
                if subscription.active and subscription.filter.matches(event):
                    matching_subscriptions.append(subscription)
                    
            # Deliver to subscribers
            delivered_count = 0
            for subscription in matching_subscriptions:
                try:
                    if subscription.callback:
                        # Call the callback
                        if asyncio.iscoroutinefunction(subscription.callback):
                            await subscription.callback(event)
                        else:
                            subscription.callback(event)
                            
                    delivered_count += 1
                    
                except Exception as e:
                    logger.error(f"Error delivering event to subscription {subscription.subscription_id}: {e}")
                    
            # Mark event as delivered if at least one subscriber received it
            if delivered_count > 0:
                event.mark_delivered()
                await self._notify_callbacks('event_delivered', event, delivered_count=delivered_count)
                logger.debug(f"Delivered event {event.event_id} to {delivered_count} subscribers")
            else:
                logger.debug(f"No subscribers for event {event.event_id}")
                
        except Exception as e:
            logger.error(f"Error delivering event {event.event_id}: {e}")
            await self._notify_callbacks('event_failed', event, error=str(e))
            
    async def _cleanup_old_events(self):
        """Clean up old events from history."""
        while True:
            try:
                current_time = datetime.utcnow()
                cleanup_threshold = timedelta(hours=24)  # 24 hours
                
                # Remove old events from history
                old_events = []
                for event in self._event_history:
                    if current_time - event.timestamp > cleanup_threshold:
                        old_events.append(event)
                        
                for event in old_events:
                    self._event_history.remove(event)
                    
                if old_events:
                    logger.info(f"Cleaned up {len(old_events)} old events from history")
                    
                await asyncio.sleep(3600)  # Check every hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(3600)
                
    async def _notify_callbacks(self, event: str, data: Any, **kwargs):
        """Notify all callbacks for an event."""
        if event in self._callbacks:
            for callback in self._callbacks[event]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data, **kwargs)
                    else:
                        callback(data, **kwargs)
                except Exception as e:
                    logger.error(f"Error in callback for event {event}: {e}")
                    
    # Convenience methods for common event types
    async def publish_device_event(self, device_id: str, event_type: EventType, 
                                 data: Dict[str, Any] = None, priority: EventPriority = EventPriority.NORMAL) -> Event:
        """Publish a device-related event."""
        event_data = data or {}
        event_data['device_id'] = device_id
        
        return await self.publish_event(
            event_type=event_type,
            source=f"device_{device_id}",
            data=event_data,
            priority=priority
        )
        
    async def publish_system_event(self, event_type: EventType, data: Dict[str, Any] = None,
                                 priority: EventPriority = EventPriority.NORMAL) -> Event:
        """Publish a system-related event."""
        return await self.publish_event(
            event_type=event_type,
            source="system",
            data=data or {},
            priority=priority
        )
        
    async def publish_security_event(self, event_type: EventType, data: Dict[str, Any] = None,
                                   priority: EventPriority = EventPriority.HIGH) -> Event:
        """Publish a security-related event."""
        return await self.publish_event(
            event_type=event_type,
            source="security",
            data=data or {},
            priority=priority
        )
        
    async def subscribe_to_device_events(self, subscriber_id: str, device_id: Optional[str] = None,
                                       callback: Optional[Callable] = None) -> str:
        """Subscribe to device events."""
        event_types = [
            EventType.DEVICE_DISCOVERED,
            EventType.DEVICE_CONNECTED,
            EventType.DEVICE_DISCONNECTED,
            EventType.DEVICE_AUTHENTICATED,
            EventType.DEVICE_TRUSTED,
            EventType.DEVICE_ERROR,
            EventType.DEVICE_ONLINE,
            EventType.DEVICE_OFFLINE
        ]
        
        filter_data = {}
        if device_id:
            filter_data['device_id'] = device_id
            
        event_filter = EventFilter(
            event_types=event_types,
            data_filters=filter_data if filter_data else None
        )
        
        return await self.subscribe(subscriber_id, event_filter, callback)
        
    async def subscribe_to_security_events(self, subscriber_id: str, callback: Optional[Callable] = None) -> str:
        """Subscribe to security events."""
        event_types = [
            EventType.AUTHENTICATION_SUCCESS,
            EventType.AUTHENTICATION_FAILED,
            EventType.TRUST_ESTABLISHED,
            EventType.TRUST_REVOKED,
            EventType.SECURITY_ALERT
        ]
        
        event_filter = EventFilter(
            event_types=event_types,
            min_priority=EventPriority.NORMAL
        )
        
        return await self.subscribe(subscriber_id, event_filter, callback)
        
    async def subscribe_to_critical_events(self, subscriber_id: str, callback: Optional[Callable] = None) -> str:
        """Subscribe to critical priority events."""
        event_filter = EventFilter(
            min_priority=EventPriority.CRITICAL
        )
        
        return await self.subscribe(subscriber_id, event_filter, callback)

    async def _load_events_from_database(self):
        """Load events from database."""
        try:
            from shared.database.models import Event as DBEvent
            from shared.database.api_database import get_session_factory, session_scope
            from shared.config.settings import settings
            
            session_factory = get_session_factory(settings.database_url)
            
            with session_scope(session_factory) as session:
                # Load recent events (last 24 hours)
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                db_events = session.query(DBEvent).filter(
                    DBEvent.timestamp >= cutoff_time
                ).order_by(DBEvent.timestamp.desc()).limit(1000).all()
                
                for db_event in db_events:
                    event = Event(
                        event_id=db_event.event_id,
                        event_type=EventType(db_event.event_type),
                        source=db_event.source,
                        timestamp=db_event.timestamp,
                        data=db_event.data or {},
                        metadata=db_event.event_metadata or {},
                        priority=EventPriority(db_event.priority),
                        ttl=db_event.ttl
                    )
                    self._event_history.append(event)
                    
            logger.info(f"Loaded {len(db_events)} events from database")
            
        except Exception as e:
            logger.error(f"Error loading events from database: {e}")
            
    async def _save_event_to_database(self, event: Event):
        """Save event to database."""
        try:
            from shared.database.models import Event as DBEvent
            from shared.database.api_database import get_session_factory, session_scope
            from shared.config.settings import settings
            
            session_factory = get_session_factory(settings.database_url)
            
            with session_scope(session_factory) as session:
                db_event = DBEvent(
                    event_id=event.event_id,
                    event_type=event.event_type.value,
                    source=event.source,
                    timestamp=event.timestamp,
                    data=event.data,
                    event_metadata=event.metadata,
                    priority=event.priority.value,
                    ttl=event.ttl,
                    delivered=event.delivered
                )
                session.add(db_event)
                session.commit()
                
                logger.debug(f"Saved event to database: {event.event_id}")
                
        except Exception as e:
            logger.error(f"Error saving event to database: {e}")
            
    async def _load_subscriptions_from_database(self):
        """Load subscriptions from database."""
        try:
            from shared.database.models import EventSubscription as DBEventSubscription
            from shared.database.api_database import get_session_factory, session_scope
            from shared.config.settings import settings
            
            session_factory = get_session_factory(settings.database_url)
            
            with session_scope(session_factory) as session:
                db_subscriptions = session.query(DBEventSubscription).filter_by(active=True).all()
                
                for db_subscription in db_subscriptions:
                    subscription = EventSubscription(
                        subscription_id=db_subscription.subscription_id,
                        subscriber_id=db_subscription.subscriber_id,
                        event_filter=EventFilter(
                            event_types=[EventType(et) for et in (db_subscription.event_types or [])],
                            sources=db_subscription.sources or [],
                            priority_filter=EventPriority(db_subscription.priority_filter) if db_subscription.priority_filter else None
                        ),
                        callback=None,  # Callbacks need to be re-registered
                        created_at=db_subscription.created_at
                    )
                    self._subscriptions[db_subscription.subscription_id] = subscription
                    
            logger.info(f"Loaded {len(db_subscriptions)} subscriptions from database")
            
        except Exception as e:
            logger.error(f"Error loading subscriptions from database: {e}")
            
    async def _save_subscription_to_database(self, subscription: EventSubscription):
        """Save subscription to database."""
        try:
            from shared.database.models import EventSubscription as DBEventSubscription
            from shared.database.api_database import get_session_factory, session_scope
            from shared.config.settings import settings
            
            session_factory = get_session_factory(settings.database_url)
            
            with session_scope(session_factory) as session:
                # Check if subscription exists
                existing = session.query(DBEventSubscription).filter_by(
                    subscription_id=subscription.subscription_id
                ).first()
                
                if existing:
                    # Update existing subscription
                    existing.subscriber_id = subscription.subscriber_id
                    existing.event_types = [et.value for et in (subscription.event_filter.event_types or [])]
                    existing.sources = subscription.event_filter.sources or []
                    existing.priority_filter = subscription.event_filter.priority_filter.value if subscription.event_filter.priority_filter else None
                    existing.active = True
                else:
                    # Create new subscription
                    db_subscription = DBEventSubscription(
                        subscription_id=subscription.subscription_id,
                        subscriber_id=subscription.subscriber_id,
                        event_types=[et.value for et in (subscription.event_filter.event_types or [])],
                        sources=subscription.event_filter.sources or [],
                        priority_filter=subscription.event_filter.priority_filter.value if subscription.event_filter.priority_filter else None,
                        active=True
                    )
                    session.add(db_subscription)
                    
                session.commit()
                logger.debug(f"Saved subscription to database: {subscription.subscription_id}")
                
        except Exception as e:
            logger.error(f"Error saving subscription to database: {e}")
            
    async def _save_events_to_database(self):
        """Save all events to database."""
        try:
            for event in self._event_history:
                await self._save_event_to_database(event)
            logger.info("Saved all events to database")
            
        except Exception as e:
            logger.error(f"Error saving events to database: {e}")
            
    async def _save_subscriptions_to_database(self):
        """Save all subscriptions to database."""
        try:
            for subscription in self._subscriptions.values():
                await self._save_subscription_to_database(subscription)
            logger.info("Saved all subscriptions to database")
            
        except Exception as e:
            logger.error(f"Error saving subscriptions to database: {e}")
