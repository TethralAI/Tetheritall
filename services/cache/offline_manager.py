"""
Offline Manager

Manages offline actions and synchronization when connectivity is restored.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
import json

from .models import OfflineAction, SyncStatus, CacheEntry, CacheType
from .cache_manager import CacheManager

logger = logging.getLogger(__name__)


class OfflineManager:
    """Manages offline actions and device control when connectivity is lost."""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        self.offline_actions: Dict[str, OfflineAction] = {}
        self.is_online = True
        self.last_online_check = datetime.utcnow()
        
        # Background tasks
        self._running = False
        self._connectivity_task: Optional[asyncio.Task] = None
        self._sync_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Event handlers
        self.connection_handlers: List[Callable] = []
        self.disconnection_handlers: List[Callable] = []
        self.sync_handlers: List[Callable] = []
        
        # Configuration
        self.connectivity_check_interval = 30  # seconds
        self.sync_retry_interval = 60  # seconds
        self.max_offline_actions = 10000
        self.action_expiry_days = 7
        
        # Statistics
        self.stats = {
            "offline_actions_queued": 0,
            "offline_actions_synced": 0,
            "offline_actions_failed": 0,
            "connectivity_checks": 0,
            "last_sync_attempt": None,
            "last_successful_sync": None
        }
        
    async def start(self):
        """Start the offline manager."""
        self._running = True
        
        # Load offline actions from cache
        await self._load_offline_actions()
        
        # Start background tasks
        self._connectivity_task = asyncio.create_task(self._monitor_connectivity())
        self._sync_task = asyncio.create_task(self._sync_offline_actions())
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_actions())
        
        logger.info("Offline Manager started")
        
    async def stop(self):
        """Stop the offline manager."""
        self._running = False
        
        # Save offline actions to cache
        await self._save_offline_actions()
        
        # Cancel background tasks
        if self._connectivity_task:
            self._connectivity_task.cancel()
        if self._sync_task:
            self._sync_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
            
        logger.info("Offline Manager stopped")
        
    async def queue_offline_action(
        self,
        action_type: str,
        target_id: str,
        command: Dict[str, Any],
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Queue an action for execution when online."""
        try:
            # Check action limits
            if len(self.offline_actions) >= self.max_offline_actions:
                await self._cleanup_old_actions()
                
            # Create offline action
            action = OfflineAction(
                action_type=action_type,
                target_id=target_id,
                command=command,
                priority=priority,
                metadata=metadata or {}
            )
            
            # Store action
            self.offline_actions[action.action_id] = action
            
            # Persist to cache
            await self._save_action_to_cache(action)
            
            self.stats["offline_actions_queued"] += 1
            
            logger.info(f"Queued offline action {action.action_id}: {action_type} for {target_id}")
            
            # Try immediate execution if online
            if self.is_online:
                await self._execute_action(action)
                
            return action.action_id
            
        except Exception as e:
            logger.error(f"Error queuing offline action: {e}")
            raise
            
    async def execute_device_command(
        self,
        device_id: str,
        command: Dict[str, Any],
        priority: int = 0
    ) -> Dict[str, Any]:
        """Execute device command with offline queuing support."""
        try:
            if self.is_online:
                # Try to execute immediately
                # This would integrate with your IoT hub manager
                result = await self._execute_device_command_online(device_id, command)
                if result.get("success"):
                    return result
                    
            # Queue for offline execution
            action_id = await self.queue_offline_action(
                action_type="device_control",
                target_id=device_id,
                command=command,
                priority=priority,
                metadata={"device_id": device_id}
            )
            
            return {
                "success": True,
                "offline": True,
                "action_id": action_id,
                "message": "Command queued for execution when online"
            }
            
        except Exception as e:
            logger.error(f"Error executing device command: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def get_cached_device_state(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get cached device state for offline access."""
        try:
            cached_state = await self.cache_manager.get(
                f"device_state:{device_id}",
                CacheType.DEVICE_STATE
            )
            return cached_state
            
        except Exception as e:
            logger.error(f"Error getting cached device state: {e}")
            return None
            
    async def cache_device_state(
        self,
        device_id: str,
        state: Dict[str, Any],
        ttl_seconds: int = 3600
    ) -> bool:
        """Cache device state for offline access."""
        try:
            return await self.cache_manager.set(
                f"device_state:{device_id}",
                state,
                CacheType.DEVICE_STATE,
                ttl_seconds=ttl_seconds,
                tags=["device", device_id]
            )
            
        except Exception as e:
            logger.error(f"Error caching device state: {e}")
            return False
            
    async def get_offline_action_status(self, action_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an offline action."""
        if action_id not in self.offline_actions:
            return None
            
        action = self.offline_actions[action_id]
        return {
            "action_id": action.action_id,
            "action_type": action.action_type,
            "target_id": action.target_id,
            "sync_status": action.sync_status.value,
            "retry_count": action.retry_count,
            "timestamp": action.timestamp.isoformat(),
            "error_message": action.error_message
        }
        
    async def cancel_offline_action(self, action_id: str) -> bool:
        """Cancel a pending offline action."""
        try:
            if action_id in self.offline_actions:
                action = self.offline_actions[action_id]
                if action.sync_status == SyncStatus.PENDING:
                    action.sync_status = SyncStatus.FAILED
                    action.error_message = "Cancelled by user"
                    await self._save_action_to_cache(action)
                    return True
            return False
            
        except Exception as e:
            logger.error(f"Error cancelling offline action: {e}")
            return False
            
    async def _monitor_connectivity(self):
        """Monitor network connectivity."""
        while self._running:
            try:
                # Simple connectivity check
                previous_state = self.is_online
                self.is_online = await self._check_connectivity()
                self.last_online_check = datetime.utcnow()
                self.stats["connectivity_checks"] += 1
                
                # Handle connectivity changes
                if previous_state != self.is_online:
                    if self.is_online:
                        logger.info("Connectivity restored - triggering sync")
                        await self._trigger_connection_handlers()
                        asyncio.create_task(self._sync_pending_actions())
                    else:
                        logger.warning("Connectivity lost - entering offline mode")
                        await self._trigger_disconnection_handlers()
                        
                await asyncio.sleep(self.connectivity_check_interval)
                
            except Exception as e:
                logger.error(f"Error in connectivity monitor: {e}")
                
    async def _check_connectivity(self) -> bool:
        """Check network connectivity."""
        try:
            # This is a simplified check - in production you'd ping your actual servers
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://httpbin.org/status/200",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
                    
        except Exception:
            return False
            
    async def _sync_offline_actions(self):
        """Synchronize offline actions when connectivity is available."""
        while self._running:
            try:
                if self.is_online:
                    await self._sync_pending_actions()
                    
                await asyncio.sleep(self.sync_retry_interval)
                
            except Exception as e:
                logger.error(f"Error in sync task: {e}")
                
    async def _sync_pending_actions(self):
        """Sync all pending offline actions."""
        try:
            self.stats["last_sync_attempt"] = datetime.utcnow().isoformat()
            
            pending_actions = [
                action for action in self.offline_actions.values()
                if action.sync_status == SyncStatus.PENDING
            ]
            
            if not pending_actions:
                return
                
            # Sort by priority and timestamp
            pending_actions.sort(key=lambda x: (x.priority, x.timestamp), reverse=True)
            
            synced_count = 0
            failed_count = 0
            
            for action in pending_actions:
                try:
                    result = await self._execute_action(action)
                    if result:
                        action.sync_status = SyncStatus.SYNCED
                        synced_count += 1
                    else:
                        action.retry_count += 1
                        if action.retry_count >= action.max_retries:
                            action.sync_status = SyncStatus.FAILED
                            failed_count += 1
                            
                    await self._save_action_to_cache(action)
                    
                except Exception as e:
                    logger.error(f"Error syncing action {action.action_id}: {e}")
                    action.retry_count += 1
                    action.error_message = str(e)
                    if action.retry_count >= action.max_retries:
                        action.sync_status = SyncStatus.FAILED
                        failed_count += 1
                        
            self.stats["offline_actions_synced"] += synced_count
            self.stats["offline_actions_failed"] += failed_count
            
            if synced_count > 0 or failed_count > 0:
                self.stats["last_successful_sync"] = datetime.utcnow().isoformat()
                logger.info(f"Sync completed: {synced_count} synced, {failed_count} failed")
                
                # Trigger sync handlers
                await self._trigger_sync_handlers({
                    "synced": synced_count,
                    "failed": failed_count
                })
                
        except Exception as e:
            logger.error(f"Error in sync process: {e}")
            
    async def _execute_action(self, action: OfflineAction) -> bool:
        """Execute a single offline action."""
        try:
            action.sync_status = SyncStatus.SYNCING
            
            if action.action_type == "device_control":
                result = await self._execute_device_command_online(
                    action.target_id, action.command
                )
                return result.get("success", False)
            # Add other action types as needed
            
            return False
            
        except Exception as e:
            logger.error(f"Error executing action {action.action_id}: {e}")
            action.error_message = str(e)
            return False
            
    async def _execute_device_command_online(
        self,
        device_id: str,
        command: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute device command when online."""
        # This would integrate with your actual IoT hub manager
        # For now, return a mock response
        try:
            # Simulate API call delay
            await asyncio.sleep(0.1)
            
            # Mock successful response
            return {
                "success": True,
                "device_id": device_id,
                "command": command,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
            
    async def _save_offline_actions(self):
        """Save offline actions to cache."""
        try:
            actions_data = {
                action_id: action.to_dict()
                for action_id, action in self.offline_actions.items()
            }
            
            await self.cache_manager.set(
                "offline_actions",
                actions_data,
                CacheType.OFFLINE_ACTION,
                ttl_seconds=86400 * 7  # 7 days
            )
            
        except Exception as e:
            logger.error(f"Error saving offline actions: {e}")
            
    async def _load_offline_actions(self):
        """Load offline actions from cache."""
        try:
            actions_data = await self.cache_manager.get("offline_actions")
            if actions_data:
                for action_id, action_dict in actions_data.items():
                    action = OfflineAction.from_dict(action_dict)
                    self.offline_actions[action_id] = action
                    
                logger.info(f"Loaded {len(self.offline_actions)} offline actions from cache")
                
        except Exception as e:
            logger.error(f"Error loading offline actions: {e}")
            
    async def _save_action_to_cache(self, action: OfflineAction):
        """Save single action to cache."""
        try:
            await self.cache_manager.set(
                f"offline_action:{action.action_id}",
                action.to_dict(),
                CacheType.OFFLINE_ACTION,
                ttl_seconds=86400 * self.action_expiry_days
            )
            
        except Exception as e:
            logger.error(f"Error saving action to cache: {e}")
            
    async def _cleanup_expired_actions(self):
        """Clean up expired offline actions."""
        while self._running:
            try:
                cutoff_time = datetime.utcnow() - timedelta(days=self.action_expiry_days)
                
                expired_ids = [
                    action_id for action_id, action in self.offline_actions.items()
                    if action.timestamp < cutoff_time
                ]
                
                for action_id in expired_ids:
                    del self.offline_actions[action_id]
                    await self.cache_manager.delete(f"offline_action:{action_id}")
                    
                if expired_ids:
                    logger.info(f"Cleaned up {len(expired_ids)} expired offline actions")
                    
                await asyncio.sleep(3600)  # Run every hour
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                
    async def _cleanup_old_actions(self):
        """Clean up old actions when approaching limits."""
        try:
            # Sort by timestamp and remove oldest 20%
            sorted_actions = sorted(
                self.offline_actions.items(),
                key=lambda x: x[1].timestamp
            )
            
            actions_to_remove = len(sorted_actions) // 5
            for i in range(actions_to_remove):
                action_id, _ = sorted_actions[i]
                del self.offline_actions[action_id]
                await self.cache_manager.delete(f"offline_action:{action_id}")
                
            logger.info(f"Cleaned up {actions_to_remove} old offline actions")
            
        except Exception as e:
            logger.error(f"Error cleaning up old actions: {e}")
            
    async def _trigger_connection_handlers(self):
        """Trigger connection event handlers."""
        for handler in self.connection_handlers:
            try:
                await handler()
            except Exception as e:
                logger.error(f"Error in connection handler: {e}")
                
    async def _trigger_disconnection_handlers(self):
        """Trigger disconnection event handlers."""
        for handler in self.disconnection_handlers:
            try:
                await handler()
            except Exception as e:
                logger.error(f"Error in disconnection handler: {e}")
                
    async def _trigger_sync_handlers(self, data: Dict[str, Any]):
        """Trigger sync event handlers."""
        for handler in self.sync_handlers:
            try:
                await handler(data)
            except Exception as e:
                logger.error(f"Error in sync handler: {e}")
                
    def add_connection_handler(self, handler: Callable):
        """Add connection event handler."""
        self.connection_handlers.append(handler)
        
    def add_disconnection_handler(self, handler: Callable):
        """Add disconnection event handler."""
        self.disconnection_handlers.append(handler)
        
    def add_sync_handler(self, handler: Callable):
        """Add sync event handler."""
        self.sync_handlers.append(handler)
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get offline manager statistics."""
        return {
            **self.stats,
            "is_online": self.is_online,
            "pending_actions": len([
                a for a in self.offline_actions.values()
                if a.sync_status == SyncStatus.PENDING
            ]),
            "total_offline_actions": len(self.offline_actions),
            "last_online_check": self.last_online_check.isoformat(),
            "running": self._running
        }
