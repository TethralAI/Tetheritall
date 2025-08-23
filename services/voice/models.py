"""
Voice Control Data Models

Defines data structures for voice commands, intents, and responses.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid


class VoiceAssistant(Enum):
    """Voice assistant platforms."""
    ALEXA = "alexa"
    GOOGLE_ASSISTANT = "google_assistant"
    SIRI = "siri"
    CUSTOM = "custom"


class IntentType(Enum):
    """Types of voice intents."""
    DEVICE_CONTROL = "device_control"
    DEVICE_STATUS = "device_status"
    SCENE_CONTROL = "scene_control"
    SYSTEM_STATUS = "system_status"
    HELP = "help"
    UNKNOWN = "unknown"


class EntityType(Enum):
    """Types of entities in voice commands."""
    DEVICE_NAME = "device_name"
    DEVICE_TYPE = "device_type"
    ACTION = "action"
    VALUE = "value"
    ROOM = "room"
    TIME = "time"
    SCENE = "scene"


class ConfidenceLevel(Enum):
    """Confidence levels for voice recognition."""
    HIGH = "high"     # 0.8-1.0
    MEDIUM = "medium" # 0.5-0.8
    LOW = "low"       # 0.0-0.5


@dataclass
class Entity:
    """Extracted entity from voice command."""
    entity_type: EntityType
    value: str
    confidence: float = 0.0
    start_index: int = 0
    end_index: int = 0
    resolved_value: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Intent:
    """Recognized intent from voice command."""
    intent_type: IntentType
    confidence: float = 0.0
    entities: List[Entity] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_entity(self, entity_type: EntityType) -> Optional[Entity]:
        """Get entity by type."""
        for entity in self.entities:
            if entity.entity_type == entity_type:
                return entity
        return None
    
    def get_entity_value(self, entity_type: EntityType) -> Optional[str]:
        """Get entity value by type."""
        entity = self.get_entity(entity_type)
        return entity.value if entity else None


@dataclass
class VoiceCommand:
    """Voice command data structure."""
    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    assistant: VoiceAssistant = VoiceAssistant.CUSTOM
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    raw_text: str = ""
    processed_text: str = ""
    intent: Optional[Intent] = None
    confidence: float = 0.0
    language: str = "en-US"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert voice command to dictionary."""
        return {
            "command_id": self.command_id,
            "assistant": self.assistant.value,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "raw_text": self.raw_text,
            "processed_text": self.processed_text,
            "intent": {
                "intent_type": self.intent.intent_type.value,
                "confidence": self.intent.confidence,
                "entities": [
                    {
                        "entity_type": entity.entity_type.value,
                        "value": entity.value,
                        "confidence": entity.confidence,
                        "start_index": entity.start_index,
                        "end_index": entity.end_index,
                        "resolved_value": entity.resolved_value,
                        "metadata": entity.metadata
                    } for entity in self.intent.entities
                ],
                "metadata": self.intent.metadata
            } if self.intent else None,
            "confidence": self.confidence,
            "language": self.language,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
            "metadata": self.metadata
        }


@dataclass
class VoiceResponse:
    """Voice response data structure."""
    response_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    command_id: str = ""
    text: str = ""
    ssml: Optional[str] = None
    should_end_session: bool = False
    reprompt_text: Optional[str] = None
    card_title: Optional[str] = None
    card_content: Optional[str] = None
    actions: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert voice response to dictionary."""
        return {
            "response_id": self.response_id,
            "command_id": self.command_id,
            "text": self.text,
            "ssml": self.ssml,
            "should_end_session": self.should_end_session,
            "reprompt_text": self.reprompt_text,
            "card_title": self.card_title,
            "card_content": self.card_content,
            "actions": self.actions,
            "metadata": self.metadata
        }


@dataclass
class DeviceVoiceMapping:
    """Mapping between voice names and device IDs."""
    device_id: str
    voice_names: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    room: Optional[str] = None
    device_type: Optional[str] = None
    capabilities: List[str] = field(default_factory=list)
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


def create_device_control_command(
    device_name: str,
    action: str,
    value: Optional[str] = None,
    user_id: Optional[str] = None,
    assistant: VoiceAssistant = VoiceAssistant.CUSTOM
) -> VoiceCommand:
    """Create a device control voice command."""
    entities = [
        Entity(EntityType.DEVICE_NAME, device_name, confidence=1.0),
        Entity(EntityType.ACTION, action, confidence=1.0)
    ]
    
    if value:
        entities.append(Entity(EntityType.VALUE, value, confidence=1.0))
    
    intent = Intent(
        intent_type=IntentType.DEVICE_CONTROL,
        confidence=1.0,
        entities=entities
    )
    
    text = f"{action} {device_name}"
    if value:
        text += f" to {value}"
    
    return VoiceCommand(
        assistant=assistant,
        user_id=user_id,
        raw_text=text,
        processed_text=text,
        intent=intent,
        confidence=1.0
    )


def create_device_status_command(
    device_name: str,
    user_id: Optional[str] = None,
    assistant: VoiceAssistant = VoiceAssistant.CUSTOM
) -> VoiceCommand:
    """Create a device status voice command."""
    entities = [
        Entity(EntityType.DEVICE_NAME, device_name, confidence=1.0),
        Entity(EntityType.ACTION, "status", confidence=1.0)
    ]
    
    intent = Intent(
        intent_type=IntentType.DEVICE_STATUS,
        confidence=1.0,
        entities=entities
    )
    
    text = f"what is the status of {device_name}"
    
    return VoiceCommand(
        assistant=assistant,
        user_id=user_id,
        raw_text=text,
        processed_text=text,
        intent=intent,
        confidence=1.0
    )


def create_success_response(
    command_id: str,
    device_name: str,
    action: str,
    result: Dict[str, Any]
) -> VoiceResponse:
    """Create a successful voice response."""
    text = f"I've {action} {device_name}"
    if result.get("state"):
        text += f". The device is now {result['state']}"
    
    return VoiceResponse(
        command_id=command_id,
        text=text,
        should_end_session=True,
        card_title=f"Device Control - {device_name}",
        card_content=f"Successfully {action} {device_name}",
        actions=[{
            "type": "device_control",
            "device_name": device_name,
            "action": action,
            "result": result
        }]
    )


def create_error_response(
    command_id: str,
    error_message: str,
    should_end_session: bool = False
) -> VoiceResponse:
    """Create an error voice response."""
    return VoiceResponse(
        command_id=command_id,
        text=f"Sorry, {error_message}",
        should_end_session=should_end_session,
        reprompt_text="Please try again or ask for help.",
        card_title="Error",
        card_content=error_message
    )
