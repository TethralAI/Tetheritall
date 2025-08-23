"""
Notification Manager

Central manager for handling push notifications across multiple platforms and providers.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import uuid

from .models import (
    Notification, NotificationTarget, DeliveryResult, DeliveryStatus,
    Platform, NotificationType, Priority
)
from .providers import (
    BaseNotificationProvider, FCMProvider, APNSProvider, 
    WebPushProvider, EmailProvider, SMSProvider
)

logger = logging.getLogger(__name__)


@dataclass
class UserSubscription:
    """User notification subscription preferences."""
    user_id: str
    platforms: Set[Platform] = field(default_factory=set)
    notification_types: Set[NotificationType] = field(default_factory=lambda: set(NotificationType))
    priority_filter: Priority = Priority.LOW
    targets: List[NotificationTarget] = field(default_factory=list)
    do_not_disturb_start: Optional[str] = None  # HH:MM format
    do_not_disturb_end: Optional[str] = None    # HH:MM format
    timezone: str = "UTC"
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class NotificationManager:
    """Manages notification delivery across multiple platforms."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.providers: Dict[Platform, BaseNotificationProvider] = {}
        self.user_subscriptions: Dict[str, UserSubscription] = {}
        self.notification_history: List[Notification] = []
        self.delivery_results: Dict[str, List[DeliveryResult]] = {}
        
        # Background tasks
        self._running = False
        self._cleanup_task: Optional[asyncio.Task] = None
        self._retry_task: Optional[asyncio.Task] = None
        self._scheduled_task: Optional[asyncio.Task] = None
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {}
        
        # Queue for pending notifications
        self._notification_queue: asyncio.Queue = asyncio.Queue()
        self._processing_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            "total_sent": 0,
            "total_delivered": 0,
            "total_failed": 0,
            "by_platform": {},
            "by_type": {}
        }
        
    async def start(self):
        """Start the notification manager."""
        self._running = True
        
        # Initialize providers
        await self._initialize_providers()
        
        # Start background tasks
        self._processing_task = asyncio.create_task(self._process_notification_queue())
        self._cleanup_task = asyncio.create_task(self._cleanup_old_notifications())
        self._retry_task = asyncio.create_task(self._retry_failed_notifications())
        self._scheduled_task = asyncio.create_task(self._process_scheduled_notifications())
        
        logger.info("Notification Manager started")
        
    async def stop(self):
        """Stop the notification manager."""
        self._running = False
        
        # Cancel background tasks
        if self._processing_task:
            self._processing_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._retry_task:
            self._retry_task.cancel()
        if self._scheduled_task:
            self._scheduled_task.cancel()
            
        logger.info("Notification Manager stopped")
        
    async def _initialize_providers(self):
        """Initialize notification providers based on configuration."""
        provider_configs = self.config.get("providers", {})
        
        # Initialize FCM provider
        if "fcm" in provider_configs:
            self.providers[Platform.FCM] = FCMProvider(provider_configs["fcm"])
            
        # Initialize APNS provider
        if "apns" in provider_configs:
            self.providers[Platform.APNS] = APNSProvider(provider_configs["apns"])
            
        # Initialize Web Push provider
        if "web_push" in provider_configs:
            self.providers[Platform.WEB_PUSH] = WebPushProvider(provider_configs["web_push"])
            
        # Initialize Email provider
        if "email" in provider_configs:
            self.providers[Platform.EMAIL] = EmailProvider(provider_configs["email"])
            
        # Initialize SMS provider
        if "sms" in provider_configs:
            self.providers[Platform.SMS] = SMSProvider(provider_configs["sms"])
            
        logger.info(f"Initialized {len(self.providers)} notification providers")
        
    async def send_notification(
        self,
        notification: Notification,
        targets: Optional[List[NotificationTarget]] = None
    ) -> Dict[str, List[DeliveryResult]]:
        """Send a notification to specified targets or user subscriptions."""
        try:
            # Use provided targets or resolve from user subscriptions
            if targets:
                notification.targets = targets
            else:
                notification.targets = await self._resolve_targets(notification)
                
            # Add to queue for processing
            await self._notification_queue.put(notification)
            
            # Store in history
            self.notification_history.append(notification)
            
            logger.info(f"Queued notification {notification.notification_id} for {len(notification.targets)} targets")
            
            # Return empty results initially (will be populated asynchronously)
            return {"results": []}
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            raise
            
    async def _process_notification_queue(self):
        """Process notifications from the queue."""
        while self._running:
            try:
                # Get notification from queue
                notification = await asyncio.wait_for(
                    self._notification_queue.get(), timeout=1.0
                )
                
                # Check if notification is scheduled
                if notification.schedule_time and notification.schedule_time > datetime.utcnow():
                    # Put back in queue for later processing
                    await self._notification_queue.put(notification)
                    continue
                    
                # Check if notification has expired
                if notification.expire_time and notification.expire_time < datetime.utcnow():
                    logger.warning(f"Notification {notification.notification_id} expired")
                    continue
                    
                # Process notification
                results = await self._deliver_notification(notification)
                
                # Store delivery results
                self.delivery_results[notification.notification_id] = results
                
                # Update statistics
                await self._update_statistics(notification, results)
                
                # Trigger event handlers
                await self._trigger_event_handlers("notification_sent", {
                    "notification": notification,
                    "results": results
                })
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing notification queue: {e}")
                
    async def _deliver_notification(self, notification: Notification) -> List[DeliveryResult]:
        """Deliver notification to all targets."""
        results = []
        
        # Group targets by platform
        targets_by_platform = {}
        for target in notification.targets:
            if target.platform not in targets_by_platform:
                targets_by_platform[target.platform] = []
            targets_by_platform[target.platform].append(target)
            
        # Send to each platform
        for platform, targets in targets_by_platform.items():
            if platform not in self.providers:
                # Create failure results for unsupported platforms
                for target in targets:
                    results.append(DeliveryResult(
                        notification_id=notification.notification_id,
                        target=target,
                        status=DeliveryStatus.FAILED,
                        message=f"Provider for {platform.value} not available"
                    ))
                continue
                
            provider = self.providers[platform]
            
            try:
                # Send bulk notification
                platform_results = await provider.send_bulk_notifications(notification, targets)
                results.extend(platform_results)
                
            except Exception as e:
                logger.error(f"Error sending to {platform.value}: {e}")
                # Create failure results
                for target in targets:
                    results.append(DeliveryResult(
                        notification_id=notification.notification_id,
                        target=target,
                        status=DeliveryStatus.FAILED,
                        message=f"Provider error: {str(e)}"
                    ))
                    
        return results
        
    async def _resolve_targets(self, notification: Notification) -> List[NotificationTarget]:
        """Resolve notification targets from user subscriptions."""
        targets = []
        
        if notification.user_id:
            # Get targets for specific user
            if notification.user_id in self.user_subscriptions:
                subscription = self.user_subscriptions[notification.user_id]
                
                # Check if user should receive this notification
                if self._should_send_to_user(notification, subscription):
                    targets.extend(subscription.targets)
        else:
            # Broadcast to all subscribed users
            for user_id, subscription in self.user_subscriptions.items():
                if self._should_send_to_user(notification, subscription):
                    targets.extend(subscription.targets)
                    
        return targets
        
    def _should_send_to_user(self, notification: Notification, subscription: UserSubscription) -> bool:
        """Check if notification should be sent to user based on subscription preferences."""
        if not subscription.enabled:
            return False
            
        # Check notification type filter
        if notification.notification_type not in subscription.notification_types:
            return False
            
        # Check priority filter
        if notification.priority.value < subscription.priority_filter.value:
            return False
            
        # Check do not disturb hours
        if subscription.do_not_disturb_start and subscription.do_not_disturb_end:
            current_time = datetime.utcnow().strftime("%H:%M")
            if subscription.do_not_disturb_start <= current_time <= subscription.do_not_disturb_end:
                # Allow critical notifications even during DND
                if notification.priority != Priority.CRITICAL:
                    return False
                    
        return True
        
    async def subscribe_user(
        self,
        user_id: str,
        targets: List[NotificationTarget],
        notification_types: Optional[Set[NotificationType]] = None,
        priority_filter: Priority = Priority.LOW,
        **kwargs
    ) -> bool:
        """Subscribe a user to notifications."""
        try:
            subscription = UserSubscription(
                user_id=user_id,
                targets=targets,
                notification_types=notification_types or set(NotificationType),
                priority_filter=priority_filter,
                **kwargs
            )
            
            self.user_subscriptions[user_id] = subscription
            
            logger.info(f"User {user_id} subscribed with {len(targets)} targets")
            return True
            
        except Exception as e:
            logger.error(f"Error subscribing user {user_id}: {e}")
            return False
            
    async def unsubscribe_user(self, user_id: str) -> bool:
        """Unsubscribe a user from notifications."""
        try:
            if user_id in self.user_subscriptions:
                del self.user_subscriptions[user_id]
                logger.info(f"User {user_id} unsubscribed")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error unsubscribing user {user_id}: {e}")
            return False
            
    async def update_user_subscription(
        self,
        user_id: str,
        **updates
    ) -> bool:
        """Update user subscription preferences."""
        try:
            if user_id not in self.user_subscriptions:
                return False
                
            subscription = self.user_subscriptions[user_id]
            
            # Update subscription attributes
            for key, value in updates.items():
                if hasattr(subscription, key):
                    setattr(subscription, key, value)
                    
            logger.info(f"Updated subscription for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating subscription for user {user_id}: {e}")
            return False
            
    async def get_delivery_status(self, notification_id: str) -> Optional[Dict[str, Any]]:
        """Get delivery status for a notification."""
        if notification_id not in self.delivery_results:
            return None
            
        results = self.delivery_results[notification_id]
        
        status_summary = {
            "notification_id": notification_id,
            "total_targets": len(results),
            "delivered": sum(1 for r in results if r.status == DeliveryStatus.DELIVERED),
            "failed": sum(1 for r in results if r.status == DeliveryStatus.FAILED),
            "pending": sum(1 for r in results if r.status == DeliveryStatus.PENDING),
            "results": [r.to_dict() for r in results]
        }
        
        return status_summary
        
    async def _update_statistics(self, notification: Notification, results: List[DeliveryResult]):
        """Update notification statistics."""
        self.stats["total_sent"] += 1
        
        for result in results:
            if result.status == DeliveryStatus.DELIVERED:
                self.stats["total_delivered"] += 1
            elif result.status == DeliveryStatus.FAILED:
                self.stats["total_failed"] += 1
                
            # Update platform stats
            platform = result.target.platform.value
            if platform not in self.stats["by_platform"]:
                self.stats["by_platform"][platform] = {"sent": 0, "delivered": 0, "failed": 0}
                
            self.stats["by_platform"][platform]["sent"] += 1
            if result.status == DeliveryStatus.DELIVERED:
                self.stats["by_platform"][platform]["delivered"] += 1
            elif result.status == DeliveryStatus.FAILED:
                self.stats["by_platform"][platform]["failed"] += 1
                
        # Update notification type stats
        notification_type = notification.notification_type.value
        if notification_type not in self.stats["by_type"]:
            self.stats["by_type"][notification_type] = 0
        self.stats["by_type"][notification_type] += 1
        
    async def _cleanup_old_notifications(self):
        """Clean up old notifications and delivery results."""
        while self._running:
            try:
                cutoff_time = datetime.utcnow() - timedelta(days=7)  # Keep 7 days
                
                # Clean up notification history
                self.notification_history = [
                    n for n in self.notification_history
                    if n.created_at > cutoff_time
                ]
                
                # Clean up delivery results
                old_ids = [
                    notification_id for notification_id, results in self.delivery_results.items()
                    if results and results[0].delivered_at and results[0].delivered_at < cutoff_time
                ]
                
                for notification_id in old_ids:
                    del self.delivery_results[notification_id]
                    
                await asyncio.sleep(3600)  # Run every hour
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                
    async def _retry_failed_notifications(self):
        """Retry failed notification deliveries."""
        while self._running:
            try:
                # Implementation for retrying failed notifications
                # This would involve checking delivery results and retrying based on retry policies
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in retry task: {e}")
                
    async def _process_scheduled_notifications(self):
        """Process scheduled notifications."""
        while self._running:
            try:
                # Implementation for processing scheduled notifications
                # This would check for notifications scheduled for the current time
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in scheduled notifications task: {e}")
                
    def add_event_handler(self, event_type: str, handler: Callable):
        """Add an event handler."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        
    async def _trigger_event_handlers(self, event_type: str, data: Dict[str, Any]):
        """Trigger event handlers."""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    await handler(data)
                except Exception as e:
                    logger.error(f"Error in event handler: {e}")
                    
    def get_statistics(self) -> Dict[str, Any]:
        """Get notification statistics."""
        return {
            **self.stats,
            "active_subscriptions": len(self.user_subscriptions),
            "queue_size": self._notification_queue.qsize(),
            "providers_enabled": {
                platform.value: provider.enabled
                for platform, provider in self.providers.items()
            },
            "running": self._running
        }
