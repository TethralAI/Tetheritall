"""
Real-time Communication Module

This module provides WebSocket connections for real-time device updates,
state changes, and live event streaming.
"""

from .websocket_manager import WebSocketManager
from .events import RealtimeEvent, EventType
from .client import WebSocketClient

__all__ = [
    "WebSocketManager",
    "RealtimeEvent", 
    "EventType",
    "WebSocketClient",
]
