"""
Communication Module
Handles device communication protocols and APIs.
"""

from .manager import CommunicationManager
from .protocols import CommunicationProtocol, MessageType
from .apis import DeviceAPI, APIManager

__all__ = [
    'CommunicationManager',
    'CommunicationProtocol',
    'MessageType',
    'DeviceAPI',
    'APIManager'
]
