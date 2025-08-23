"""
Voice Manager

Central manager for voice control integration across multiple platforms.
"""

import asyncio
import logging
import re
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta

from .models import (
    VoiceCommand, VoiceResponse, Intent, Entity, IntentType, EntityType,
    VoiceAssistant, DeviceVoiceMapping, ConfidenceLevel
)

logger = logging.getLogger(__name__)


class VoiceManager:
    """Manages voice control integration and command processing."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.device_mappings: Dict[str, DeviceVoiceMapping] = {}
        self.command_history: List[VoiceCommand] = []
        self.response_history: List[VoiceResponse] = []
        
        # NLP configuration
        self.enable_fuzzy_matching = self.config.get("enable_fuzzy_matching", True)
        self.confidence_threshold = self.config.get("confidence_threshold", 0.7)
        self.max_history_entries = self.config.get("max_history_entries", 1000)
        
        # Command processors for different assistants
        self.processors: Dict[VoiceAssistant, Callable] = {}
        
        # Intent handlers
        self.intent_handlers: Dict[IntentType, Callable] = {}
        
        # Event handlers
        self.command_handlers: List[Callable] = []
        self.response_handlers: List[Callable] = []
        
        # Background tasks
        self._running = False
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            "commands_processed": 0,
            "successful_commands": 0,
            "failed_commands": 0,
            "by_assistant": {},
            "by_intent": {},
            "average_confidence": 0.0
        }
        
        # Initialize default intent handlers
        self._initialize_default_handlers()
        
    async def start(self):
        """Start the voice manager."""
        self._running = True
        
        # Load device mappings
        await self._load_device_mappings()
        
        # Start background tasks
        self._cleanup_task = asyncio.create_task(self._cleanup_history())
        
        logger.info("Voice Manager started")
        
    async def stop(self):
        """Stop the voice manager."""
        self._running = False
        
        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
            
        logger.info("Voice Manager stopped")
        
    async def process_voice_command(
        self,
        raw_text: str,
        assistant: VoiceAssistant = VoiceAssistant.CUSTOM,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> VoiceResponse:
        """Process a voice command and return a response."""
        try:
            # Create voice command
            command = VoiceCommand(
                assistant=assistant,
                user_id=user_id,
                session_id=session_id,
                raw_text=raw_text,
                processed_text=self._preprocess_text(raw_text),
                context=context or {}
            )
            
            # Process command based on assistant type
            if assistant in self.processors:
                command = await self.processors[assistant](command)
            else:
                command = await self._process_generic_command(command)
                
            # Store command in history
            self.command_history.append(command)
            
            # Generate response
            response = await self._generate_response(command)
            
            # Store response in history
            self.response_history.append(response)
            
            # Update statistics
            await self._update_statistics(command, response)
            
            # Trigger event handlers
            await self._trigger_command_handlers(command)
            await self._trigger_response_handlers(response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing voice command: {e}")
            return VoiceResponse(
                text="Sorry, I encountered an error processing your request.",
                should_end_session=True
            )
            
    async def _process_generic_command(self, command: VoiceCommand) -> VoiceCommand:
        """Process a generic voice command using built-in NLP."""
        try:
            # Extract intent and entities
            intent = await self._extract_intent(command.processed_text)
            command.intent = intent
            command.confidence = intent.confidence if intent else 0.0
            
            return command
            
        except Exception as e:
            logger.error(f"Error processing generic command: {e}")
            command.confidence = 0.0
            return command
            
    async def _extract_intent(self, text: str) -> Optional[Intent]:
        """Extract intent and entities from text using rule-based NLP."""
        text_lower = text.lower()
        
        # Device control patterns
        control_patterns = [
            (r"(turn|switch) (on|off) (?:the )?(.+)", IntentType.DEVICE_CONTROL),
            (r"(set|adjust) (?:the )?(.+) to (.+)", IntentType.DEVICE_CONTROL),
            (r"(dim|brighten) (?:the )?(.+)", IntentType.DEVICE_CONTROL),
            (r"(start|stop|pause) (?:the )?(.+)", IntentType.DEVICE_CONTROL),
            (r"(open|close) (?:the )?(.+)", IntentType.DEVICE_CONTROL),
            (r"(lock|unlock) (?:the )?(.+)", IntentType.DEVICE_CONTROL),
        ]
        
        # Status query patterns
        status_patterns = [
            (r"what.+status.+(.+)", IntentType.DEVICE_STATUS),
            (r"how.+(.+)", IntentType.DEVICE_STATUS),
            (r"is (?:the )?(.+) (on|off|open|closed|locked|unlocked)", IntentType.DEVICE_STATUS),
            (r"check (?:the )?(.+)", IntentType.DEVICE_STATUS),
        ]
        
        # Try control patterns
        for pattern, intent_type in control_patterns:
            match = re.search(pattern, text_lower)
            if match:
                return await self._create_control_intent(match, intent_type)
                
        # Try status patterns
        for pattern, intent_type in status_patterns:
            match = re.search(pattern, text_lower)
            if match:
                return await self._create_status_intent(match, intent_type)
                
        # Help patterns
        if any(word in text_lower for word in ["help", "what can you do", "commands"]):
            return Intent(intent_type=IntentType.HELP, confidence=0.9)
            
        # Default to unknown
        return Intent(intent_type=IntentType.UNKNOWN, confidence=0.1)
        
    async def _create_control_intent(self, match, intent_type: IntentType) -> Intent:
        """Create a device control intent from regex match."""
        entities = []
        groups = match.groups()
        
        if len(groups) >= 2:
            action = groups[0]
            device_name = groups[-1] if len(groups) == 2 else groups[1]
            
            entities.append(Entity(
                entity_type=EntityType.ACTION,
                value=action,
                confidence=0.9,
                start_index=match.start(1),
                end_index=match.end(1)
            ))
            
            # Resolve device name
            resolved_device = await self._resolve_device_name(device_name)
            entities.append(Entity(
                entity_type=EntityType.DEVICE_NAME,
                value=device_name,
                confidence=0.8 if resolved_device else 0.5,
                resolved_value=resolved_device,
                start_index=match.start(-1),
                end_index=match.end(-1)
            ))
            
            # Add value if present (for 3-group matches)
            if len(groups) >= 3:
                value = groups[2] if len(groups) == 3 else groups[1]
                entities.append(Entity(
                    entity_type=EntityType.VALUE,
                    value=value,
                    confidence=0.8,
                    start_index=match.start(2) if len(groups) == 3 else match.start(1),
                    end_index=match.end(2) if len(groups) == 3 else match.end(1)
                ))
                
        confidence = 0.9 if entities and any(e.resolved_value for e in entities if e.entity_type == EntityType.DEVICE_NAME) else 0.6
        
        return Intent(
            intent_type=intent_type,
            confidence=confidence,
            entities=entities
        )
        
    async def _create_status_intent(self, match, intent_type: IntentType) -> Intent:
        """Create a device status intent from regex match."""
        entities = []
        groups = match.groups()
        
        if groups:
            device_name = groups[0]
            
            # Resolve device name
            resolved_device = await self._resolve_device_name(device_name)
            entities.append(Entity(
                entity_type=EntityType.DEVICE_NAME,
                value=device_name,
                confidence=0.8 if resolved_device else 0.5,
                resolved_value=resolved_device,
                start_index=match.start(1),
                end_index=match.end(1)
            ))
            
        confidence = 0.8 if entities and any(e.resolved_value for e in entities) else 0.5
        
        return Intent(
            intent_type=intent_type,
            confidence=confidence,
            entities=entities
        )
        
    async def _resolve_device_name(self, voice_name: str) -> Optional[str]:
        """Resolve voice name to device ID."""
        voice_name_lower = voice_name.lower().strip()
        
        # Exact match
        for device_id, mapping in self.device_mappings.items():
            if voice_name_lower in [name.lower() for name in mapping.voice_names]:
                return device_id
            if voice_name_lower in [alias.lower() for alias in mapping.aliases]:
                return device_id
                
        # Fuzzy matching
        if self.enable_fuzzy_matching:
            best_match = None
            best_score = 0
            
            for device_id, mapping in self.device_mappings.items():
                all_names = mapping.voice_names + mapping.aliases
                for name in all_names:
                    score = self._calculate_similarity(voice_name_lower, name.lower())
                    if score > best_score and score > 0.7:
                        best_score = score
                        best_match = device_id
                        
            return best_match
            
        return None
        
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two strings."""
        # Simple similarity calculation (could use more advanced algorithms)
        if text1 == text2:
            return 1.0
            
        # Check if one is contained in the other
        if text1 in text2 or text2 in text1:
            return 0.8
            
        # Check word overlap
        words1 = set(text1.split())
        words2 = set(text2.split())
        overlap = len(words1.intersection(words2))
        total = len(words1.union(words2))
        
        return overlap / total if total > 0 else 0.0
        
    async def _generate_response(self, command: VoiceCommand) -> VoiceResponse:
        """Generate response for a voice command."""
        try:
            if not command.intent:
                return VoiceResponse(
                    command_id=command.command_id,
                    text="I didn't understand that command. Please try again.",
                    should_end_session=False,
                    reprompt_text="You can say things like 'turn on the lights' or 'check the thermostat'."
                )
                
            # Handle based on intent type
            if command.intent.intent_type in self.intent_handlers:
                return await self.intent_handlers[command.intent.intent_type](command)
            else:
                return VoiceResponse(
                    command_id=command.command_id,
                    text="I understand what you want to do, but I'm not sure how to handle that yet.",
                    should_end_session=True
                )
                
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return VoiceResponse(
                command_id=command.command_id,
                text="Sorry, I encountered an error processing your request.",
                should_end_session=True
            )
            
    def _initialize_default_handlers(self):
        """Initialize default intent handlers."""
        self.intent_handlers[IntentType.DEVICE_CONTROL] = self._handle_device_control
        self.intent_handlers[IntentType.DEVICE_STATUS] = self._handle_device_status
        self.intent_handlers[IntentType.HELP] = self._handle_help
        self.intent_handlers[IntentType.UNKNOWN] = self._handle_unknown
        
    async def _handle_device_control(self, command: VoiceCommand) -> VoiceResponse:
        """Handle device control intent."""
        try:
            if not command.intent:
                return VoiceResponse(
                    command_id=command.command_id,
                    text="I couldn't understand the device control command.",
                    should_end_session=True
                )
                
            device_entity = command.intent.get_entity(EntityType.DEVICE_NAME)
            action_entity = command.intent.get_entity(EntityType.ACTION)
            value_entity = command.intent.get_entity(EntityType.VALUE)
            
            if not device_entity or not device_entity.resolved_value:
                return VoiceResponse(
                    command_id=command.command_id,
                    text="I couldn't identify which device you want to control.",
                    should_end_session=False,
                    reprompt_text="Please specify the device name clearly."
                )
                
            if not action_entity:
                return VoiceResponse(
                    command_id=command.command_id,
                    text="I couldn't understand what action to perform.",
                    should_end_session=False,
                    reprompt_text="Please specify what you want to do with the device."
                )
                
            # Execute device command
            result = await self._execute_device_command(
                device_id=device_entity.resolved_value,
                action=action_entity.value,
                value=value_entity.value if value_entity else None
            )
            
            if result.get("success"):
                device_name = device_entity.value
                action = action_entity.value
                text = f"I've {action} the {device_name}"
                
                if result.get("state"):
                    text += f". It's now {result['state']}"
                    
                return VoiceResponse(
                    command_id=command.command_id,
                    text=text,
                    should_end_session=True,
                    card_title=f"Device Control - {device_name}",
                    card_content=f"Successfully {action} {device_name}"
                )
            else:
                error_msg = result.get("error", "unknown error")
                return VoiceResponse(
                    command_id=command.command_id,
                    text=f"I couldn't control the device. {error_msg}",
                    should_end_session=True
                )
                
        except Exception as e:
            logger.error(f"Error handling device control: {e}")
            return VoiceResponse(
                command_id=command.command_id,
                text="I encountered an error while controlling the device.",
                should_end_session=True
            )
            
    async def _handle_device_status(self, command: VoiceCommand) -> VoiceResponse:
        """Handle device status intent."""
        try:
            if not command.intent:
                return VoiceResponse(
                    command_id=command.command_id,
                    text="I couldn't understand the status request.",
                    should_end_session=True
                )
                
            device_entity = command.intent.get_entity(EntityType.DEVICE_NAME)
            
            if not device_entity or not device_entity.resolved_value:
                return VoiceResponse(
                    command_id=command.command_id,
                    text="I couldn't identify which device you're asking about.",
                    should_end_session=False,
                    reprompt_text="Please specify the device name clearly."
                )
                
            # Get device status
            status = await self._get_device_status(device_entity.resolved_value)
            
            if status:
                device_name = device_entity.value
                state_text = self._format_device_state(status)
                text = f"The {device_name} is {state_text}"
                
                return VoiceResponse(
                    command_id=command.command_id,
                    text=text,
                    should_end_session=True,
                    card_title=f"Device Status - {device_name}",
                    card_content=f"Status: {state_text}"
                )
            else:
                return VoiceResponse(
                    command_id=command.command_id,
                    text="I couldn't get the status of that device.",
                    should_end_session=True
                )
                
        except Exception as e:
            logger.error(f"Error handling device status: {e}")
            return VoiceResponse(
                command_id=command.command_id,
                text="I encountered an error while checking the device status.",
                should_end_session=True
            )
            
    async def _handle_help(self, command: VoiceCommand) -> VoiceResponse:
        """Handle help intent."""
        help_text = (
            "I can help you control your smart home devices. "
            "You can say things like: 'turn on the lights', 'set the thermostat to 72', "
            "'check the front door lock', or 'dim the bedroom lights'. "
            "What would you like to do?"
        )
        
        return VoiceResponse(
            command_id=command.command_id,
            text=help_text,
            should_end_session=False,
            reprompt_text="What device would you like to control?",
            card_title="Voice Control Help",
            card_content=help_text
        )
        
    async def _handle_unknown(self, command: VoiceCommand) -> VoiceResponse:
        """Handle unknown intent."""
        return VoiceResponse(
            command_id=command.command_id,
            text="I didn't understand that command. You can ask for help to learn what I can do.",
            should_end_session=False,
            reprompt_text="Try saying 'help' to learn about available commands."
        )
        
    async def _execute_device_command(
        self,
        device_id: str,
        action: str,
        value: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a device command."""
        # This would integrate with your IoT hub manager
        # For now, return a mock response
        try:
            # Simulate command execution
            await asyncio.sleep(0.1)
            
            # Mock successful response
            return {
                "success": True,
                "device_id": device_id,
                "action": action,
                "value": value,
                "state": "on" if action in ["turn on", "start", "open", "unlock"] else "off",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
            
    async def _get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device status."""
        # This would integrate with your IoT hub manager
        # For now, return a mock response
        try:
            await asyncio.sleep(0.1)
            
            return {
                "device_id": device_id,
                "state": "on",
                "brightness": 75,
                "temperature": 72,
                "battery": 85,
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting device status: {e}")
            return None
            
    def _format_device_state(self, status: Dict[str, Any]) -> str:
        """Format device state for voice response."""
        state_parts = []
        
        if "state" in status:
            state_parts.append(status["state"])
            
        if "brightness" in status and status["brightness"] is not None:
            state_parts.append(f"{status['brightness']}% brightness")
            
        if "temperature" in status and status["temperature"] is not None:
            state_parts.append(f"{status['temperature']} degrees")
            
        if "battery" in status and status["battery"] is not None:
            state_parts.append(f"{status['battery']}% battery")
            
        return ", ".join(state_parts) if state_parts else "unknown"
        
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for better NLP."""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Expand contractions
        contractions = {
            "i'm": "i am",
            "you're": "you are",
            "it's": "it is",
            "that's": "that is",
            "what's": "what is",
            "where's": "where is",
            "how's": "how is",
            "here's": "here is",
            "there's": "there is",
            "can't": "cannot",
            "won't": "will not",
            "shouldn't": "should not",
            "couldn't": "could not",
            "wouldn't": "would not"
        }
        
        for contraction, expansion in contractions.items():
            text = text.replace(contraction, expansion)
            text = text.replace(contraction.capitalize(), expansion.capitalize())
            
        return text
        
    async def add_device_mapping(
        self,
        device_id: str,
        voice_names: List[str],
        aliases: Optional[List[str]] = None,
        room: Optional[str] = None,
        device_type: Optional[str] = None,
        capabilities: Optional[List[str]] = None
    ) -> bool:
        """Add device voice mapping."""
        try:
            mapping = DeviceVoiceMapping(
                device_id=device_id,
                voice_names=voice_names,
                aliases=aliases or [],
                room=room,
                device_type=device_type,
                capabilities=capabilities or []
            )
            
            self.device_mappings[device_id] = mapping
            logger.info(f"Added voice mapping for device {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding device mapping: {e}")
            return False
            
    async def remove_device_mapping(self, device_id: str) -> bool:
        """Remove device voice mapping."""
        try:
            if device_id in self.device_mappings:
                del self.device_mappings[device_id]
                logger.info(f"Removed voice mapping for device {device_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error removing device mapping: {e}")
            return False
            
    async def _load_device_mappings(self):
        """Load device mappings from configuration or database."""
        # In a real implementation, this would load from persistent storage
        # For now, add some example mappings
        example_mappings = [
            ("light_001", ["living room light", "main light"], ["front light", "big light"]),
            ("thermostat_001", ["thermostat", "temperature"], ["heat", "cooling"]),
            ("lock_001", ["front door", "main door"], ["entrance", "door lock"]),
            ("garage_001", ["garage door", "garage"], ["car door"]),
        ]
        
        for device_id, names, aliases in example_mappings:
            await self.add_device_mapping(device_id, names, aliases)
            
    async def _cleanup_history(self):
        """Clean up old command and response history."""
        while self._running:
            try:
                # Keep only recent entries
                if len(self.command_history) > self.max_history_entries:
                    self.command_history = self.command_history[-self.max_history_entries:]
                    
                if len(self.response_history) > self.max_history_entries:
                    self.response_history = self.response_history[-self.max_history_entries:]
                    
                await asyncio.sleep(3600)  # Run every hour
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                
    async def _update_statistics(self, command: VoiceCommand, response: VoiceResponse):
        """Update voice control statistics."""
        self.stats["commands_processed"] += 1
        
        # Track by assistant
        assistant = command.assistant.value
        if assistant not in self.stats["by_assistant"]:
            self.stats["by_assistant"][assistant] = 0
        self.stats["by_assistant"][assistant] += 1
        
        # Track by intent
        if command.intent:
            intent_type = command.intent.intent_type.value
            if intent_type not in self.stats["by_intent"]:
                self.stats["by_intent"][intent_type] = 0
            self.stats["by_intent"][intent_type] += 1
            
        # Track success/failure
        if "error" not in response.text.lower() and "sorry" not in response.text.lower():
            self.stats["successful_commands"] += 1
        else:
            self.stats["failed_commands"] += 1
            
        # Update average confidence
        total_confidence = sum(cmd.confidence for cmd in self.command_history)
        self.stats["average_confidence"] = total_confidence / len(self.command_history)
        
    async def _trigger_command_handlers(self, command: VoiceCommand):
        """Trigger command event handlers."""
        for handler in self.command_handlers:
            try:
                await handler(command)
            except Exception as e:
                logger.error(f"Error in command handler: {e}")
                
    async def _trigger_response_handlers(self, response: VoiceResponse):
        """Trigger response event handlers."""
        for handler in self.response_handlers:
            try:
                await handler(response)
            except Exception as e:
                logger.error(f"Error in response handler: {e}")
                
    def add_command_handler(self, handler: Callable):
        """Add command event handler."""
        self.command_handlers.append(handler)
        
    def add_response_handler(self, handler: Callable):
        """Add response event handler."""
        self.response_handlers.append(handler)
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get voice control statistics."""
        return {
            **self.stats,
            "total_device_mappings": len(self.device_mappings),
            "command_history_length": len(self.command_history),
            "response_history_length": len(self.response_history),
            "running": self._running
        }
