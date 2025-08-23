"""
Device State Manager
Manages device states, tracks state changes, and provides monitoring capabilities.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
import json
import uuid

from .models import DeviceState, StateChange, StateType
from shared.config.settings import settings
from shared.database.api_database import get_session_factory, session_scope

logger = logging.getLogger(__name__)


class StateManager:
    """Manages device states and state transitions."""
    
    def __init__(self):
        self._device_states: Dict[str, DeviceState] = {}
        self._session_factory = get_session_factory(settings.database_url)
        self._callbacks: Dict[str, List[Callable]] = {
            'state_changed': [],
            'device_online': [],
            'device_offline': [],
            'device_error': [],
            'state_transition': []
        }
        self._monitoring_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start the state manager."""
        logger.info("Starting state manager")
        
        # Load existing device states from database
        await self._load_states_from_database()
        
        # Start background tasks
        self._monitoring_task = asyncio.create_task(self._monitor_device_states())
        self._cleanup_task = asyncio.create_task(self._cleanup_old_states())
        
        logger.info(f"State manager started with {len(self._device_states)} device states")
        
    async def stop(self):
        """Stop the state manager."""
        logger.info("Stopping state manager")
        
        # Cancel background tasks
        if self._monitoring_task:
            self._monitoring_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
            
        # Save states to database
        await self._save_states_to_database()
        
        logger.info("State manager stopped")
        
    async def register_device(self, device_id: str, initial_state: StateType = StateType.OFFLINE) -> DeviceState:
        """Register a new device for state management."""
        try:
            if device_id in self._device_states:
                logger.warning(f"Device {device_id} already registered for state management")
                return self._device_states[device_id]
                
            # Create device state
            device_state = DeviceState(
                device_id=device_id,
                current_state=initial_state
            )
            
            # Add to manager
            self._device_states[device_id] = device_state
            
            # Save to database
            await self._save_device_state_to_database(device_state)
            
            logger.info(f"Registered device for state management: {device_id}")
            return device_state
            
        except Exception as e:
            logger.error(f"Error registering device {device_id} for state management: {e}")
            raise
            
    async def unregister_device(self, device_id: str) -> bool:
        """Unregister a device from state management."""
        try:
            if device_id not in self._device_states:
                logger.warning(f"Device {device_id} not found in state manager")
                return False
                
            # Remove from manager
            del self._device_states[device_id]
            
            # Remove from database
            await self._remove_device_state_from_database(device_id)
            
            logger.info(f"Unregistered device from state management: {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error unregistering device {device_id} from state management: {e}")
            return False
            
    async def update_device_state(self, device_id: str, new_state: StateType, reason: Optional[str] = None, metadata: Dict[str, Any] = None) -> Optional[StateChange]:
        """Update device state and create state change record."""
        try:
            device_state = self._device_states.get(device_id)
            if not device_state:
                logger.warning(f"Device {device_id} not found in state manager")
                return None
                
            # Update state
            state_change = device_state.update_state(new_state, reason, metadata)
            
            # Save to database
            await self._save_device_state_to_database(device_state)
            await self._save_state_change_to_database(state_change)
            
            # Notify callbacks
            await self._notify_callbacks('state_changed', device_state, state_change=state_change)
            
            # Notify specific state change callbacks
            if new_state == StateType.ONLINE:
                await self._notify_callbacks('device_online', device_state)
            elif new_state == StateType.OFFLINE:
                await self._notify_callbacks('device_offline', device_state)
            elif new_state == StateType.ERROR:
                await self._notify_callbacks('device_error', device_state)
                
            # Notify state transition callbacks
            await self._notify_callbacks('state_transition', device_state, old_state=state_change.old_state, new_state=new_state)
            
            logger.info(f"Updated device {device_id} state: {state_change.old_state.value} -> {new_state.value}")
            return state_change
            
        except Exception as e:
            logger.error(f"Error updating device state {device_id}: {e}")
            return None
            
    async def get_device_state(self, device_id: str) -> Optional[DeviceState]:
        """Get device state."""
        return self._device_states.get(device_id)
        
    async def get_device_states(self, state_filter: Optional[StateType] = None) -> List[DeviceState]:
        """Get device states with optional filtering."""
        states = list(self._device_states.values())
        
        if state_filter:
            states = [state for state in states if state.current_state == state_filter]
            
        return states
        
    async def get_online_devices(self) -> List[DeviceState]:
        """Get all online devices."""
        return [state for state in self._device_states.values() if state.is_online()]
        
    async def get_offline_devices(self) -> List[DeviceState]:
        """Get all offline devices."""
        return [state for state in self._device_states.values() if not state.is_online()]
        
    async def get_error_devices(self) -> List[DeviceState]:
        """Get all devices in error state."""
        return [state for state in self._device_states.values() if state.is_error()]
        
    async def get_device_state_history(self, device_id: str, limit: int = 50) -> List[StateChange]:
        """Get device state history."""
        device_state = self._device_states.get(device_id)
        if not device_state:
            return []
            
        return device_state.get_recent_changes(limit)
        
    async def get_state_statistics(self) -> Dict[str, Any]:
        """Get state management statistics."""
        total_devices = len(self._device_states)
        online_devices = len(await self.get_online_devices())
        offline_devices = len(await self.get_offline_devices())
        error_devices = len(await self.get_error_devices())
        
        # State distribution
        state_counts = {}
        for state in StateType:
            state_counts[state.value] = len(await self.get_device_states(state))
            
        # Average state duration
        total_duration = sum(state.get_state_duration() for state in self._device_states.values())
        avg_duration = total_duration / total_devices if total_devices > 0 else 0.0
        
        return {
            'total_devices': total_devices,
            'online_devices': online_devices,
            'offline_devices': offline_devices,
            'error_devices': error_devices,
            'state_distribution': state_counts,
            'average_state_duration': avg_duration
        }
        
    async def update_device_configuration(self, device_id: str, config: Dict[str, Any]) -> bool:
        """Update device configuration."""
        try:
            device_state = self._device_states.get(device_id)
            if not device_state:
                logger.warning(f"Device {device_id} not found in state manager")
                return False
                
            device_state.update_configuration(config)
            
            # Save to database
            await self._save_device_state_to_database(device_state)
            
            logger.info(f"Updated configuration for device {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating configuration for device {device_id}: {e}")
            return False
            
    async def get_device_configuration(self, device_id: str) -> Dict[str, Any]:
        """Get device configuration."""
        device_state = self._device_states.get(device_id)
        if not device_state:
            return {}
            
        return device_state.configuration
        
    async def update_device_metadata(self, device_id: str, metadata: Dict[str, Any]) -> bool:
        """Update device metadata."""
        try:
            device_state = self._device_states.get(device_id)
            if not device_state:
                logger.warning(f"Device {device_id} not found in state manager")
                return False
                
            device_state.update_metadata(metadata)
            
            # Save to database
            await self._save_device_state_to_database(device_state)
            
            logger.info(f"Updated metadata for device {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating metadata for device {device_id}: {e}")
            return False
            
    async def get_device_metadata(self, device_id: str) -> Dict[str, Any]:
        """Get device metadata."""
        device_state = self._device_states.get(device_id)
        if not device_state:
            return {}
            
        return device_state.metadata
        
    def add_callback(self, event: str, callback: Callable):
        """Add a callback for state events."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
            logger.debug(f"Added callback for event: {event}")
        else:
            logger.warning(f"Unknown event type: {event}")
            
    def remove_callback(self, event: str, callback: Callable):
        """Remove a callback for state events."""
        if event in self._callbacks and callback in self._callbacks[event]:
            self._callbacks[event].remove(callback)
            logger.debug(f"Removed callback for event: {event}")
            
    async def _notify_callbacks(self, event: str, device_state: DeviceState, **kwargs):
        """Notify all callbacks for an event."""
        if event in self._callbacks:
            for callback in self._callbacks[event]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(device_state, **kwargs)
                    else:
                        callback(device_state, **kwargs)
                except Exception as e:
                    logger.error(f"Error in callback for event {event}: {e}")
                    
    async def _load_states_from_database(self):
        """Load device states from database."""
        try:
            from shared.database.models import DeviceState as DBDeviceState, StateChange as DBStateChange
            
            with session_scope(self._session_factory) as session:
                db_states = session.query(DBDeviceState).all()
                
                for db_state in db_states:
                    # Create device state object
                    device_state = DeviceState(
                        device_id=db_state.device_id,
                        current_state=StateType(db_state.current_state),
                        last_updated=db_state.last_updated,
                        configuration=db_state.configuration or {},
                        metadata=db_state.device_metadata or {}
                    )
                    
                    # Load state history
                    state_changes = session.query(DBStateChange).filter_by(
                        device_id=db_state.device_id
                    ).order_by(DBStateChange.timestamp).all()
                    
                    for db_change in state_changes:
                        state_change = StateChange(
                            from_state=StateType(db_change.from_state) if db_change.from_state else None,
                            to_state=StateType(db_change.to_state),
                            timestamp=db_change.timestamp,
                            reason=db_change.reason,
                            metadata=db_change.change_metadata or {}
                        )
                        device_state.state_history.append(state_change)
                    
                    self._device_states[db_state.device_id] = device_state
                    
            logger.info(f"Loaded {len(db_states)} device states from database")
            
        except Exception as e:
            logger.error(f"Error loading device states from database: {e}")
            
    async def _save_device_state_to_database(self, device_state: DeviceState):
        """Save device state to database."""
        try:
            from shared.database.models import DeviceState as DBDeviceState, StateChange as DBStateChange
            
            with session_scope(self._session_factory) as session:
                # Check if device state exists
                db_state = session.query(DBDeviceState).filter_by(
                    device_id=device_state.device_id
                ).first()
                
                if db_state:
                    # Update existing state
                    db_state.current_state = device_state.current_state.value
                    db_state.last_updated = device_state.last_updated
                    db_state.configuration = device_state.configuration
                    db_state.device_metadata = device_state.metadata
                else:
                    # Create new state
                    db_state = DBDeviceState(
                        device_id=device_state.device_id,
                        current_state=device_state.current_state.value,
                        last_updated=device_state.last_updated,
                        configuration=device_state.configuration,
                        device_metadata=device_state.metadata
                    )
                    session.add(db_state)
                
                session.commit()
                logger.debug(f"Saved device state to database: {device_state.device_id}")
                
        except Exception as e:
            logger.error(f"Error saving device state to database: {e}")
            
    async def _remove_device_state_from_database(self, device_id: str):
        """Remove device state from database."""
        try:
            from shared.database.models import DeviceState as DBDeviceState, StateChange as DBStateChange
            
            with session_scope(self._session_factory) as session:
                # Remove state changes first (due to foreign key constraints)
                session.query(DBStateChange).filter_by(device_id=device_id).delete()
                
                # Remove device state
                session.query(DBDeviceState).filter_by(device_id=device_id).delete()
                
                session.commit()
                logger.info(f"Removed device state from database: {device_id}")
                
        except Exception as e:
            logger.error(f"Error removing device state from database: {e}")
            
    async def _save_state_change_to_database(self, state_change: StateChange):
        """Save state change to database."""
        try:
            from shared.database.models import StateChange as DBStateChange
            
            with session_scope(self._session_factory) as session:
                db_state_change = DBStateChange(
                    device_id=state_change.device_id,
                    from_state=state_change.from_state.value if state_change.from_state else None,
                    to_state=state_change.to_state.value,
                    timestamp=state_change.timestamp,
                    reason=state_change.reason,
                    change_metadata=state_change.metadata
                )
                session.add(db_state_change)
                session.commit()
                
                logger.debug(f"Saved state change to database for device {state_change.device_id}")
                
        except Exception as e:
            logger.error(f"Error saving state change to database: {e}")
            
    async def _save_states_to_database(self):
        """Save all device states to database."""
        try:
            for device_state in self._device_states.values():
                await self._save_device_state_to_database(device_state)
            logger.info("Saved all device states to database")
            
        except Exception as e:
            logger.error(f"Error saving device states to database: {e}")
            
    async def _monitor_device_states(self):
        """Monitor device states for anomalies."""
        while True:
            try:
                current_time = datetime.utcnow()
                
                for device_state in self._device_states.values():
                    # Check for devices that have been in error state for too long
                    if device_state.is_error():
                        error_duration = device_state.get_state_duration()
                        if error_duration > 3600:  # 1 hour
                            logger.warning(f"Device {device_state.device_id} has been in error state for {error_duration:.0f} seconds")
                            
                    # Check for devices that have been offline for too long
                    elif not device_state.is_online():
                        offline_duration = device_state.get_state_duration()
                        if offline_duration > 86400:  # 24 hours
                            logger.warning(f"Device {device_state.device_id} has been offline for {offline_duration:.0f} seconds")
                            
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in state monitoring: {e}")
                await asyncio.sleep(300)
                
    async def _cleanup_old_states(self):
        """Clean up old device states."""
        while True:
            try:
                current_time = datetime.utcnow()
                cleanup_threshold = timedelta(days=30)  # 30 days
                
                devices_to_remove = []
                for device_id, device_state in self._device_states.items():
                    if current_time - device_state.last_updated > cleanup_threshold:
                        devices_to_remove.append(device_id)
                        
                for device_id in devices_to_remove:
                    await self.unregister_device(device_id)
                    
                if devices_to_remove:
                    logger.info(f"Cleaned up {len(devices_to_remove)} old device states")
                    
                await asyncio.sleep(3600)  # Check every hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(3600)
