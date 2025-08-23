"""
WebSocket Client

Client-side WebSocket implementation for connecting to the real-time service.
"""

import asyncio
import logging
import json
from typing import Dict, Any, Optional, Callable, Set
from datetime import datetime
import aiohttp
import websockets
from enum import Enum

from .events import RealtimeEvent, EventType, Priority
from .websocket_manager import ClientType, SubscriptionType

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """WebSocket client connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class WebSocketClient:
    """WebSocket client for real-time communication."""
    
    def __init__(
        self,
        server_url: str,
        api_key: str,
        client_type: ClientType = ClientType.API_CLIENT,
        user_id: Optional[str] = None,
        auto_reconnect: bool = True,
        reconnect_interval: int = 5,
        max_reconnect_attempts: int = 10
    ):
        self.server_url = server_url
        self.api_key = api_key
        self.client_type = client_type
        self.user_id = user_id
        self.auto_reconnect = auto_reconnect
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.state = ConnectionState.DISCONNECTED
        self.client_id: Optional[str] = None
        self.subscriptions: Set[SubscriptionType] = {SubscriptionType.ALL}
        self.device_filters: Set[str] = set()
        self.hub_filters: Set[str] = set()
        self.priority_filter = Priority.LOW
        
        self.event_handlers: Dict[EventType, List[Callable]] = {}
        self.connection_handlers: List[Callable] = []
        self.disconnection_handlers: List[Callable] = []
        
        self._running = False
        self._reconnect_task: Optional[asyncio.Task] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._reconnect_attempts = 0
        
    async def connect(self) -> bool:
        """Connect to the WebSocket server."""
        try:
            self.state = ConnectionState.CONNECTING
            
            # Build WebSocket URL
            ws_url = self.server_url.replace("http://", "ws://").replace("https://", "wss://")
            ws_url += f"/ws?api_key={self.api_key}&client_type={self.client_type.value}"
            if self.user_id:
                ws_url += f"&user_id={self.user_id}"
                
            # Connect to WebSocket
            self.websocket = await websockets.connect(
                ws_url,
                extra_headers={"X-API-Key": self.api_key}
            )
            
            self.state = ConnectionState.CONNECTED
            self._running = True
            self._reconnect_attempts = 0
            
            # Start receive task
            self._receive_task = asyncio.create_task(self._receive_messages())
            
            # Notify connection handlers
            for handler in self.connection_handlers:
                try:
                    await handler()
                except Exception as e:
                    logger.error(f"Error in connection handler: {e}")
                    
            logger.info(f"Connected to WebSocket server: {ws_url}")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to WebSocket: {e}")
            self.state = ConnectionState.ERROR
            
            if self.auto_reconnect:
                await self._schedule_reconnect()
            return False
            
    async def disconnect(self):
        """Disconnect from the WebSocket server."""
        self._running = False
        self.state = ConnectionState.DISCONNECTED
        
        # Cancel tasks
        if self._receive_task:
            self._receive_task.cancel()
        if self._reconnect_task:
            self._reconnect_task.cancel()
            
        # Close WebSocket
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            
        # Notify disconnection handlers
        for handler in self.disconnection_handlers:
            try:
                await handler()
            except Exception as e:
                logger.error(f"Error in disconnection handler: {e}")
                
        logger.info("Disconnected from WebSocket server")
        
    async def send_event(self, event: RealtimeEvent):
        """Send an event to the server."""
        if not self.websocket or self.state != ConnectionState.CONNECTED:
            logger.warning("Cannot send event: not connected")
            return False
            
        try:
            await self.websocket.send(event.to_json())
            return True
        except Exception as e:
            logger.error(f"Error sending event: {e}")
            return False
            
    async def update_subscriptions(
        self,
        subscriptions: Set[SubscriptionType],
        device_filters: Optional[Set[str]] = None,
        hub_filters: Optional[Set[str]] = None,
        priority_filter: Optional[Priority] = None
    ):
        """Update event subscriptions."""
        self.subscriptions = subscriptions
        if device_filters is not None:
            self.device_filters = device_filters
        if hub_filters is not None:
            self.hub_filters = hub_filters
        if priority_filter is not None:
            self.priority_filter = priority_filter
            
        # Send subscription update to server
        update_event = RealtimeEvent(
            event_type=EventType.USER_ACTION,
            source="client",
            data={
                "action": "update_subscriptions",
                "subscriptions": [sub.value for sub in subscriptions],
                "device_filters": list(self.device_filters),
                "hub_filters": list(self.hub_filters),
                "priority_filter": self.priority_filter.value
            },
            user_id=self.user_id
        )
        
        await self.send_event(update_event)
        
    def add_event_handler(self, event_type: EventType, handler: Callable):
        """Add an event handler for a specific event type."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        
    def remove_event_handler(self, event_type: EventType, handler: Callable):
        """Remove an event handler."""
        if event_type in self.event_handlers and handler in self.event_handlers[event_type]:
            self.event_handlers[event_type].remove(handler)
            
    def add_connection_handler(self, handler: Callable):
        """Add a connection event handler."""
        self.connection_handlers.append(handler)
        
    def add_disconnection_handler(self, handler: Callable):
        """Add a disconnection event handler."""
        self.disconnection_handlers.append(handler)
        
    async def _receive_messages(self):
        """Receive and process messages from the server."""
        try:
            async for message in self.websocket:
                try:
                    event = RealtimeEvent.from_json(message)
                    await self._handle_event(event)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error in receive loop: {e}")
        finally:
            if self._running and self.auto_reconnect:
                await self._schedule_reconnect()
                
    async def _handle_event(self, event: RealtimeEvent):
        """Handle received event."""
        # Update client_id from welcome message
        if event.event_type == EventType.USER_ACTION and event.data.get("action") == "connected":
            self.client_id = event.data.get("client_id")
            
        # Call event handlers
        if event.event_type in self.event_handlers:
            for handler in self.event_handlers[event.event_type]:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error(f"Error in event handler: {e}")
                    
    async def _schedule_reconnect(self):
        """Schedule a reconnection attempt."""
        if not self.auto_reconnect or self._reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Maximum reconnection attempts reached")
            return
            
        self.state = ConnectionState.RECONNECTING
        self._reconnect_attempts += 1
        
        logger.info(f"Scheduling reconnection attempt {self._reconnect_attempts} in {self.reconnect_interval} seconds")
        
        self._reconnect_task = asyncio.create_task(self._perform_reconnect())
        
    async def _perform_reconnect(self):
        """Perform reconnection after delay."""
        await asyncio.sleep(self.reconnect_interval)
        
        if self._running:
            await self.connect()
            
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self.state == ConnectionState.CONNECTED and self.websocket is not None
        
    def get_status(self) -> Dict[str, Any]:
        """Get client status information."""
        return {
            "state": self.state.value,
            "client_id": self.client_id,
            "user_id": self.user_id,
            "client_type": self.client_type.value,
            "connected": self.is_connected(),
            "reconnect_attempts": self._reconnect_attempts,
            "subscriptions": [sub.value for sub in self.subscriptions],
            "device_filters": list(self.device_filters),
            "hub_filters": list(self.hub_filters),
            "priority_filter": self.priority_filter.value
        }
