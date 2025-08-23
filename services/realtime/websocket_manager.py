"""
WebSocket Manager

Manages WebSocket connections for real-time communication with clients.
Handles connection lifecycle, message broadcasting, and client subscriptions.
"""

import asyncio
import logging
import json
from typing import Dict, List, Set, Optional, Any, Callable
from datetime import datetime, timedelta
import uuid
from enum import Enum
from dataclasses import dataclass, field
import weakref

from fastapi import WebSocket, WebSocketDisconnect
from .events import RealtimeEvent, EventType, Priority

logger = logging.getLogger(__name__)


class ClientType(Enum):
    """WebSocket client types."""
    WEB_APP = "web_app"
    MOBILE_APP = "mobile_app"
    DASHBOARD = "dashboard"
    API_CLIENT = "api_client"
    ADMIN = "admin"


class SubscriptionType(Enum):
    """Event subscription types."""
    ALL = "all"
    DEVICE_EVENTS = "device_events"
    HUB_EVENTS = "hub_events"
    SECURITY_EVENTS = "security_events"
    SYSTEM_EVENTS = "system_events"
    USER_EVENTS = "user_events"


@dataclass
class ClientConnection:
    """WebSocket client connection information."""
    client_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    websocket: WebSocket = None
    client_type: ClientType = ClientType.WEB_APP
    user_id: Optional[str] = None
    subscriptions: Set[SubscriptionType] = field(default_factory=lambda: {SubscriptionType.ALL})
    device_filters: Set[str] = field(default_factory=set)  # Device IDs to filter
    hub_filters: Set[str] = field(default_factory=set)  # Hub IDs to filter
    priority_filter: Priority = Priority.LOW  # Minimum priority level
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_ping: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class WebSocketManager:
    """Manages WebSocket connections and real-time event broadcasting."""
    
    def __init__(self):
        self.connections: Dict[str, ClientConnection] = {}
        self.user_connections: Dict[str, List[str]] = {}  # user_id -> client_ids
        self.event_handlers: Dict[EventType, List[Callable]] = {}
        self._running = False
        self._cleanup_task: Optional[asyncio.Task] = None
        self._ping_task: Optional[asyncio.Task] = None
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._broadcast_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start the WebSocket manager."""
        self._running = True
        
        # Start background tasks
        self._cleanup_task = asyncio.create_task(self._cleanup_connections())
        self._ping_task = asyncio.create_task(self._ping_clients())
        self._broadcast_task = asyncio.create_task(self._process_event_queue())
        
        logger.info("WebSocket Manager started")
        
    async def stop(self):
        """Stop the WebSocket manager."""
        self._running = False
        
        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._ping_task:
            self._ping_task.cancel()
        if self._broadcast_task:
            self._broadcast_task.cancel()
            
        # Close all connections
        for client_id in list(self.connections.keys()):
            await self.disconnect_client(client_id)
            
        logger.info("WebSocket Manager stopped")
        
    async def connect_client(
        self,
        websocket: WebSocket,
        client_type: ClientType = ClientType.WEB_APP,
        user_id: Optional[str] = None,
        subscriptions: Optional[Set[SubscriptionType]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Connect a new WebSocket client."""
        try:
            await websocket.accept()
            
            # Create client connection
            client = ClientConnection(
                websocket=websocket,
                client_type=client_type,
                user_id=user_id,
                subscriptions=subscriptions or {SubscriptionType.ALL},
                metadata=metadata or {}
            )
            
            # Store connection
            self.connections[client.client_id] = client
            
            # Track user connections
            if user_id:
                if user_id not in self.user_connections:
                    self.user_connections[user_id] = []
                self.user_connections[user_id].append(client.client_id)
            
            # Send welcome message
            welcome_event = RealtimeEvent(
                event_type=EventType.USER_ACTION,
                source="websocket_manager",
                data={
                    "action": "connected",
                    "client_id": client.client_id,
                    "message": "WebSocket connection established"
                },
                user_id=user_id
            )
            await self._send_to_client(client.client_id, welcome_event)
            
            logger.info(f"Client {client.client_id} connected (type: {client_type.value}, user: {user_id})")
            return client.client_id
            
        except Exception as e:
            logger.error(f"Error connecting client: {e}")
            raise
            
    async def disconnect_client(self, client_id: str):
        """Disconnect a WebSocket client."""
        try:
            if client_id not in self.connections:
                return
                
            client = self.connections[client_id]
            
            # Close WebSocket connection
            try:
                await client.websocket.close()
            except Exception:
                pass  # Connection might already be closed
                
            # Remove from user connections
            if client.user_id and client.user_id in self.user_connections:
                if client_id in self.user_connections[client.user_id]:
                    self.user_connections[client.user_id].remove(client_id)
                if not self.user_connections[client.user_id]:
                    del self.user_connections[client.user_id]
                    
            # Remove connection
            del self.connections[client_id]
            
            logger.info(f"Client {client_id} disconnected")
            
        except Exception as e:
            logger.error(f"Error disconnecting client {client_id}: {e}")
            
    async def update_client_subscriptions(
        self,
        client_id: str,
        subscriptions: Set[SubscriptionType],
        device_filters: Optional[Set[str]] = None,
        hub_filters: Optional[Set[str]] = None,
        priority_filter: Optional[Priority] = None
    ):
        """Update client subscription preferences."""
        if client_id not in self.connections:
            return False
            
        client = self.connections[client_id]
        client.subscriptions = subscriptions
        
        if device_filters is not None:
            client.device_filters = device_filters
        if hub_filters is not None:
            client.hub_filters = hub_filters
        if priority_filter is not None:
            client.priority_filter = priority_filter
            
        logger.info(f"Updated subscriptions for client {client_id}")
        return True
        
    async def broadcast_event(self, event: RealtimeEvent):
        """Broadcast an event to all relevant clients."""
        await self._event_queue.put(event)
        
    async def send_to_user(self, user_id: str, event: RealtimeEvent):
        """Send an event to all connections for a specific user."""
        if user_id not in self.user_connections:
            return
            
        for client_id in self.user_connections[user_id]:
            await self._send_to_client(client_id, event)
            
    async def send_to_client(self, client_id: str, event: RealtimeEvent):
        """Send an event to a specific client."""
        await self._send_to_client(client_id, event)
        
    async def _send_to_client(self, client_id: str, event: RealtimeEvent):
        """Internal method to send event to client."""
        if client_id not in self.connections:
            return
            
        client = self.connections[client_id]
        
        # Check if client should receive this event
        if not self._should_send_to_client(client, event):
            return
            
        try:
            await client.websocket.send_text(event.to_json())
        except Exception as e:
            logger.error(f"Error sending to client {client_id}: {e}")
            # Schedule client for disconnection
            asyncio.create_task(self.disconnect_client(client_id))
            
    def _should_send_to_client(self, client: ClientConnection, event: RealtimeEvent) -> bool:
        """Check if an event should be sent to a specific client."""
        # Check priority filter
        if event.priority.value < client.priority_filter.value:
            return False
            
        # Check subscription filters
        if SubscriptionType.ALL not in client.subscriptions:
            event_subscription = self._get_event_subscription_type(event.event_type)
            if event_subscription not in client.subscriptions:
                return False
                
        # Check device filters
        if client.device_filters and event.device_id:
            if event.device_id not in client.device_filters:
                return False
                
        # Check hub filters
        if client.hub_filters and event.hub_id:
            if event.hub_id not in client.hub_filters:
                return False
                
        # Check user-specific events
        if event.user_id and event.user_id != client.user_id:
            return False
            
        return True
        
    def _get_event_subscription_type(self, event_type: EventType) -> SubscriptionType:
        """Map event type to subscription type."""
        device_events = {
            EventType.DEVICE_STATE_CHANGED,
            EventType.DEVICE_DISCOVERED,
            EventType.DEVICE_DISCONNECTED
        }
        
        hub_events = {
            EventType.HUB_STATUS_CHANGED,
            EventType.HUB_CONNECTED,
            EventType.HUB_DISCONNECTED
        }
        
        security_events = {
            EventType.SECURITY_EVENT
        }
        
        system_events = {
            EventType.SYSTEM_ALERT,
            EventType.ERROR,
            EventType.HEARTBEAT
        }
        
        user_events = {
            EventType.USER_ACTION,
            EventType.WORKFLOW_STARTED,
            EventType.WORKFLOW_COMPLETED,
            EventType.ML_INFERENCE_COMPLETED
        }
        
        if event_type in device_events:
            return SubscriptionType.DEVICE_EVENTS
        elif event_type in hub_events:
            return SubscriptionType.HUB_EVENTS
        elif event_type in security_events:
            return SubscriptionType.SECURITY_EVENTS
        elif event_type in system_events:
            return SubscriptionType.SYSTEM_EVENTS
        elif event_type in user_events:
            return SubscriptionType.USER_EVENTS
        else:
            return SubscriptionType.ALL
            
    async def _process_event_queue(self):
        """Process the event queue and broadcast events."""
        while self._running:
            try:
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                
                # Broadcast to all relevant clients
                for client_id in list(self.connections.keys()):
                    await self._send_to_client(client_id, event)
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing event queue: {e}")
                
    async def _cleanup_connections(self):
        """Clean up dead connections."""
        while self._running:
            try:
                current_time = datetime.utcnow()
                timeout = timedelta(minutes=5)
                
                dead_clients = []
                for client_id, client in self.connections.items():
                    if current_time - client.last_ping > timeout:
                        dead_clients.append(client_id)
                        
                for client_id in dead_clients:
                    await self.disconnect_client(client_id)
                    
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in connection cleanup: {e}")
                
    async def _ping_clients(self):
        """Send ping messages to maintain connections."""
        while self._running:
            try:
                ping_event = RealtimeEvent(
                    event_type=EventType.HEARTBEAT,
                    source="websocket_manager",
                    data={"timestamp": datetime.utcnow().isoformat()}
                )
                
                for client_id in list(self.connections.keys()):
                    await self._send_to_client(client_id, ping_event)
                    
                await asyncio.sleep(30)  # Ping every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in ping task: {e}")
                
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics."""
        return {
            "total_connections": len(self.connections),
            "users_online": len(self.user_connections),
            "connections_by_type": {
                client_type.value: sum(1 for c in self.connections.values() if c.client_type == client_type)
                for client_type in ClientType
            },
            "event_queue_size": self._event_queue.qsize(),
            "running": self._running
        }
        
    def get_client_info(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific client."""
        if client_id not in self.connections:
            return None
            
        client = self.connections[client_id]
        return {
            "client_id": client.client_id,
            "client_type": client.client_type.value,
            "user_id": client.user_id,
            "subscriptions": [sub.value for sub in client.subscriptions],
            "device_filters": list(client.device_filters),
            "hub_filters": list(client.hub_filters),
            "priority_filter": client.priority_filter.value,
            "connected_at": client.connected_at.isoformat(),
            "last_ping": client.last_ping.isoformat(),
            "metadata": client.metadata
        }
