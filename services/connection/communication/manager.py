"""
Communication Manager
Orchestrates communication protocols and manages message routing.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
import json
import uuid

from .protocols import Message, Command, Response, MessageType, CommunicationProtocol, ProtocolHandler
from .apis import APIManager
from ..registry import DeviceRegistry

logger = logging.getLogger(__name__)


class CommunicationManager:
    """Manages device communication and message routing."""
    
    def __init__(self):
        self._protocol_handlers: Dict[CommunicationProtocol, ProtocolHandler] = {}
        self._message_queue: List[Message] = []
        self._pending_responses: Dict[str, asyncio.Future] = {}
        self._callbacks: Dict[str, List[Callable]] = {
            'message_sent': [],
            'message_received': [],
            'message_delivered': [],
            'message_failed': [],
            'protocol_connected': [],
            'protocol_disconnected': []
        }
        self._api_manager = APIManager()
        self._device_registry: Optional[DeviceRegistry] = None
        self._message_processor_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def start(self, device_registry: DeviceRegistry):
        """Start the communication manager."""
        logger.info("Starting communication manager")
        
        self._device_registry = device_registry
        
        # Start API manager
        await self._api_manager.start()
        
        # Start background tasks
        self._message_processor_task = asyncio.create_task(self._process_message_queue())
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_messages())
        
        logger.info("Communication manager started")
        
    async def stop(self):
        """Stop the communication manager."""
        logger.info("Stopping communication manager")
        
        # Cancel background tasks
        if self._message_processor_task:
            self._message_processor_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
            
        # Stop API manager
        await self._api_manager.stop()
        
        logger.info("Communication manager stopped")
        
    async def register_protocol_handler(self, protocol: CommunicationProtocol, handler: ProtocolHandler):
        """Register a protocol handler."""
        try:
            self._protocol_handlers[protocol] = handler
            await self._notify_callbacks('protocol_connected', protocol)
            logger.info(f"Registered protocol handler: {protocol.value}")
            
        except Exception as e:
            logger.error(f"Error registering protocol handler {protocol.value}: {e}")
            
    async def unregister_protocol_handler(self, protocol: CommunicationProtocol):
        """Unregister a protocol handler."""
        try:
            if protocol in self._protocol_handlers:
                handler = self._protocol_handlers[protocol]
                await handler.disconnect()
                del self._protocol_handlers[protocol]
                await self._notify_callbacks('protocol_disconnected', protocol)
                logger.info(f"Unregistered protocol handler: {protocol.value}")
                
        except Exception as e:
            logger.error(f"Error unregistering protocol handler {protocol.value}: {e}")
            
    async def send_message(self, message: Message) -> bool:
        """Send a message to a device."""
        try:
            # Add message to queue
            self._message_queue.append(message)
            
            # Create future for response if needed
            if message.message_type == MessageType.COMMAND:
                future = asyncio.Future()
                self._pending_responses[message.message_id] = future
                
            await self._notify_callbacks('message_sent', message)
            logger.debug(f"Queued message: {message.message_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending message {message.message_id}: {e}")
            return False
            
    async def send_command(self, device_id: str, command_type: str, parameters: Dict[str, Any] = None, timeout: int = 30) -> Optional[Response]:
        """Send a command to a device and wait for response."""
        try:
            # Create command
            command = Command(
                command_id=str(uuid.uuid4()),
                device_id=device_id,
                command_type=command_type,
                parameters=parameters or {},
                timeout=timeout
            )
            
            # Convert to message
            message = command.to_message("communication_manager")
            
            # Send message
            if await self.send_message(message):
                # Wait for response
                if message.message_id in self._pending_responses:
                    try:
                        response_message = await asyncio.wait_for(
                            self._pending_responses[message.message_id],
                            timeout=timeout
                        )
                        return Response.from_message(response_message)
                    except asyncio.TimeoutError:
                        logger.error(f"Command timeout: {command.command_id}")
                        return Response(
                            response_id=str(uuid.uuid4()),
                            command_id=command.command_id,
                            device_id=device_id,
                            success=False,
                            error="Command timeout"
                        )
                    finally:
                        # Clean up pending response
                        if message.message_id in self._pending_responses:
                            del self._pending_responses[message.message_id]
                            
            return None
            
        except Exception as e:
            logger.error(f"Error sending command to device {device_id}: {e}")
            return None
            
    async def broadcast_message(self, message_type: MessageType, payload: Dict[str, Any], protocols: List[CommunicationProtocol] = None) -> List[bool]:
        """Broadcast a message to all devices using specified protocols."""
        try:
            if protocols is None:
                protocols = list(self._protocol_handlers.keys())
                
            results = []
            
            for protocol in protocols:
                if protocol in self._protocol_handlers:
                    # Create broadcast message
                    message = Message(
                        message_id=str(uuid.uuid4()),
                        message_type=message_type,
                        protocol=protocol,
                        source_id="communication_manager",
                        destination_id="broadcast",
                        payload=payload
                    )
                    
                    # Send message
                    success = await self.send_message(message)
                    results.append(success)
                    
            return results
            
        except Exception as e:
            logger.error(f"Error broadcasting message: {e}")
            return []
            
    async def get_message_statistics(self) -> Dict[str, Any]:
        """Get communication statistics."""
        total_messages = len(self._message_queue)
        pending_responses = len(self._pending_responses)
        active_protocols = len(self._protocol_handlers)
        
        # Get API manager statistics
        api_stats = await self._api_manager.get_api_statistics()
        
        return {
            'total_messages': total_messages,
            'pending_responses': pending_responses,
            'active_protocols': active_protocols,
            'api_statistics': api_stats
        }
        
    def add_callback(self, event: str, callback: Callable):
        """Add a callback for communication events."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
            logger.debug(f"Added callback for event: {event}")
        else:
            logger.warning(f"Unknown event type: {event}")
            
    def remove_callback(self, event: str, callback: Callable):
        """Remove a callback for communication events."""
        if event in self._callbacks and callback in self._callbacks[event]:
            self._callbacks[event].remove(callback)
            logger.debug(f"Removed callback for event: {event}")
            
    async def _process_message_queue(self):
        """Process messages in the queue."""
        while True:
            try:
                if self._message_queue:
                    message = self._message_queue.pop(0)
                    await self._route_message(message)
                    
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing message queue: {e}")
                await asyncio.sleep(1)
                
    async def _route_message(self, message: Message):
        """Route a message to the appropriate handler."""
        try:
            # Check if message has expired
            if message.is_expired():
                logger.warning(f"Message expired: {message.message_id}")
                await self._notify_callbacks('message_failed', message, error="Message expired")
                return
                
            # Get protocol handler
            handler = self._protocol_handlers.get(message.protocol)
            if not handler:
                logger.error(f"No handler for protocol: {message.protocol.value}")
                await self._notify_callbacks('message_failed', message, error="No protocol handler")
                return
                
            # Check if handler supports message type
            if not handler.supports_message_type(message.message_type):
                logger.error(f"Protocol {message.protocol.value} doesn't support message type: {message.message_type.value}")
                await self._notify_callbacks('message_failed', message, error="Unsupported message type")
                return
                
            # Send message via protocol handler
            success = await handler.send_message(message)
            
            if success:
                message.mark_delivered()
                await self._notify_callbacks('message_delivered', message)
                logger.debug(f"Message delivered: {message.message_id}")
            else:
                # Retry if possible
                if message.can_retry():
                    message.increment_retry()
                    self._message_queue.append(message)  # Re-queue for retry
                    logger.debug(f"Message queued for retry: {message.message_id}")
                else:
                    await self._notify_callbacks('message_failed', message, error="Max retries exceeded")
                    logger.error(f"Message failed after {message.max_retries} retries: {message.message_id}")
                    
        except Exception as e:
            logger.error(f"Error routing message {message.message_id}: {e}")
            await self._notify_callbacks('message_failed', message, error=str(e))
            
    async def _cleanup_expired_messages(self):
        """Clean up expired messages and pending responses."""
        while True:
            try:
                current_time = datetime.utcnow()
                
                # Clean up expired messages in queue
                expired_messages = []
                for message in self._message_queue:
                    if message.is_expired():
                        expired_messages.append(message)
                        
                for message in expired_messages:
                    self._message_queue.remove(message)
                    await self._notify_callbacks('message_failed', message, error="Message expired")
                    
                # Clean up expired pending responses
                expired_responses = []
                for message_id, future in self._pending_responses.items():
                    if not future.done():
                        # Check if response is too old (5 minutes)
                        if current_time - datetime.utcnow() > timedelta(minutes=5):
                            expired_responses.append(message_id)
                            
                for message_id in expired_responses:
                    future = self._pending_responses[message_id]
                    if not future.done():
                        future.set_exception(TimeoutError("Response timeout"))
                    del self._pending_responses[message_id]
                    
                if expired_messages or expired_responses:
                    logger.info(f"Cleaned up {len(expired_messages)} expired messages and {len(expired_responses)} expired responses")
                    
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(60)
                
    async def _notify_callbacks(self, event: str, message: Message, **kwargs):
        """Notify all callbacks for an event."""
        if event in self._callbacks:
            for callback in self._callbacks[event]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(message, **kwargs)
                    else:
                        callback(message, **kwargs)
                except Exception as e:
                    logger.error(f"Error in callback for event {event}: {e}")
                    
    async def _handle_device_response(self, response_message: Message):
        """Handle response from a device."""
        try:
            # Check if we're waiting for this response
            if response_message.message_id in self._pending_responses:
                future = self._pending_responses[response_message.message_id]
                if not future.done():
                    future.set_result(response_message)
                    
            await self._notify_callbacks('message_received', response_message)
            
        except Exception as e:
            logger.error(f"Error handling device response: {e}")
            
    # Convenience methods for common operations
    async def send_heartbeat(self, device_id: str) -> bool:
        """Send heartbeat to a device."""
        try:
            response = await self.send_command(device_id, "heartbeat", timeout=10)
            return response is not None and response.success
            
        except Exception as e:
            logger.error(f"Error sending heartbeat to device {device_id}: {e}")
            return False
            
    async def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """Get device status."""
        try:
            response = await self.send_command(device_id, "get_status", timeout=15)
            if response and response.success:
                return response.data
            else:
                return {'error': response.error if response else 'No response'}
                
        except Exception as e:
            logger.error(f"Error getting status for device {device_id}: {e}")
            return {'error': str(e)}
            
    async def update_device_config(self, device_id: str, config: Dict[str, Any]) -> bool:
        """Update device configuration."""
        try:
            response = await self.send_command(device_id, "update_config", parameters=config, timeout=30)
            return response is not None and response.success
            
        except Exception as e:
            logger.error(f"Error updating config for device {device_id}: {e}")
            return False
