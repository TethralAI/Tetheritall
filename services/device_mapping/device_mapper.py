"""
Device Mapper

Main class for managing device mappings and app connections.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
import json
import uuid

from .models import (
    DeviceMapping, DeviceCategory, ControlMapping, UserPreference, RoomMapping,
    MappingStatus, ControlType, create_light_mapping, create_thermostat_mapping, create_switch_mapping
)

logger = logging.getLogger(__name__)


class DeviceMapper:
    """
    Main device mapper for managing device-to-app connections.
    
    Provides comprehensive device mapping capabilities including:
    - Device discovery and mapping
    - Room organization
    - Control mapping
    - User preferences
    - Voice integration
    - App connectivity
    """
    
    def __init__(self):
        """Initialize the device mapper."""
        self._mappings: Dict[str, DeviceMapping] = {}
        self._rooms: Dict[str, RoomMapping] = {}
        self._user_mappings: Dict[str, List[str]] = {}  # user_id -> [mapping_ids]
        self._device_mappings: Dict[str, str] = {}  # device_id -> mapping_id
        self._category_mappings: Dict[DeviceCategory, List[str]] = {}  # category -> [mapping_ids]
        self._voice_aliases: Dict[str, str] = {}  # alias -> mapping_id
        self._running = False
        self._stats = {
            "total_mappings": 0,
            "active_mappings": 0,
            "total_rooms": 0,
            "total_users": 0,
            "mappings_by_category": {},
            "last_updated": None
        }
        
    async def start(self):
        """Start the device mapper."""
        if self._running:
            return
            
        logger.info("Starting Device Mapper")
        self._running = True
        
        # Initialize default rooms
        await self._initialize_default_rooms()
        
        # Start background tasks
        asyncio.create_task(self._update_statistics_loop())
        
        logger.info("Device Mapper started successfully")
        
    async def stop(self):
        """Stop the device mapper."""
        if not self._running:
            return
            
        logger.info("Stopping Device Mapper")
        self._running = False
        logger.info("Device Mapper stopped")
        
    def is_running(self) -> bool:
        """Check if the mapper is running."""
        return self._running
        
    async def _initialize_default_rooms(self):
        """Initialize default room mappings."""
        default_rooms = [
            RoomMapping(
                room_id="living-room",
                name="Living Room",
                description="Main living area",
                floor="1",
                icon="sofa",
                color="#4CAF50"
            ),
            RoomMapping(
                room_id="bedroom",
                name="Bedroom",
                description="Main bedroom",
                floor="1", 
                icon="bed",
                color="#2196F3"
            ),
            RoomMapping(
                room_id="kitchen",
                name="Kitchen",
                description="Kitchen area",
                floor="1",
                icon="kitchen",
                color="#FF9800"
            ),
            RoomMapping(
                room_id="bathroom",
                name="Bathroom",
                description="Main bathroom",
                floor="1",
                icon="bathroom",
                color="#9C27B0"
            ),
            RoomMapping(
                room_id="office",
                name="Office",
                description="Home office",
                floor="1",
                icon="desk",
                color="#607D8B"
            )
        ]
        
        for room in default_rooms:
            self._rooms[room.room_id] = room
            
        logger.info(f"Initialized {len(default_rooms)} default rooms")
        
    async def _update_statistics_loop(self):
        """Background task to update statistics."""
        while self._running:
            try:
                await self._update_statistics()
                await asyncio.sleep(30)  # Update every 30 seconds
            except Exception as e:
                logger.error(f"Error updating statistics: {e}")
                await asyncio.sleep(60)  # Wait longer on error
                
    async def _update_statistics(self):
        """Update mapper statistics."""
        active_mappings = sum(1 for m in self._mappings.values() if m.status == MappingStatus.ACTIVE)
        
        # Count by category
        category_counts = {}
        for category in DeviceCategory:
            category_counts[category.value] = len(self._category_mappings.get(category, []))
            
        self._stats.update({
            "total_mappings": len(self._mappings),
            "active_mappings": active_mappings,
            "total_rooms": len(self._rooms),
            "total_users": len(self._user_mappings),
            "mappings_by_category": category_counts,
            "last_updated": datetime.utcnow().isoformat()
        })
        
    # Device Mapping Methods
    
    async def create_device_mapping(
        self,
        device_id: str,
        hub_id: str,
        user_id: str,
        name: str,
        category: DeviceCategory,
        room_id: Optional[str] = None,
        controls: Optional[List[ControlMapping]] = None,
        voice_aliases: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> DeviceMapping:
        """Create a new device mapping."""
        # Check if device is already mapped
        if device_id in self._device_mappings:
            raise ValueError(f"Device {device_id} is already mapped")
            
        # Create mapping
        mapping = DeviceMapping(
            device_id=device_id,
            hub_id=hub_id,
            user_id=user_id,
            name=name,
            display_name=name,
            category=category,
            room_id=room_id,
            status=MappingStatus.ACTIVE,
            controls=controls or [],
            voice_aliases=voice_aliases or [],
            tags=tags or []
        )
        
        # Store mapping
        self._mappings[mapping.mapping_id] = mapping
        self._device_mappings[device_id] = mapping.mapping_id
        
        # Update user mappings
        if user_id not in self._user_mappings:
            self._user_mappings[user_id] = []
        self._user_mappings[user_id].append(mapping.mapping_id)
        
        # Update category mappings
        if category not in self._category_mappings:
            self._category_mappings[category] = []
        self._category_mappings[category].append(mapping.mapping_id)
        
        # Update voice aliases
        for alias in mapping.voice_aliases:
            self._voice_aliases[alias.lower()] = mapping.mapping_id
            
        logger.info(f"Created device mapping for {name} (ID: {mapping.mapping_id})")
        return mapping
        
    async def create_standard_mapping(
        self,
        device_id: str,
        hub_id: str,
        user_id: str,
        name: str,
        device_type: str,
        room_id: Optional[str] = None
    ) -> DeviceMapping:
        """Create a standard device mapping based on device type."""
        device_type = device_type.lower()
        
        if device_type in ["light", "bulb", "lamp", "lighting"]:
            return await self.create_device_mapping(
                device_id=device_id,
                hub_id=hub_id,
                user_id=user_id,
                name=name,
                category=DeviceCategory.LIGHTING,
                room_id=room_id,
                controls=create_light_mapping(device_id, hub_id, user_id, name, room_id).controls,
                voice_aliases=[name.lower(), f"the {name.lower()}", f"{name.lower()} light"],
                tags=["lighting", "smart"]
            )
        elif device_type in ["thermostat", "climate"]:
            return await self.create_device_mapping(
                device_id=device_id,
                hub_id=hub_id,
                user_id=user_id,
                name=name,
                category=DeviceCategory.THERMOSTAT,
                room_id=room_id,
                controls=create_thermostat_mapping(device_id, hub_id, user_id, name, room_id).controls,
                voice_aliases=[name.lower(), f"the {name.lower()}", f"{name.lower()} thermostat"],
                tags=["climate", "thermostat", "smart"]
            )
        elif device_type in ["switch", "outlet", "plug"]:
            return await self.create_device_mapping(
                device_id=device_id,
                hub_id=hub_id,
                user_id=user_id,
                name=name,
                category=DeviceCategory.SWITCH,
                room_id=room_id,
                controls=create_switch_mapping(device_id, hub_id, user_id, name, room_id).controls,
                voice_aliases=[name.lower(), f"the {name.lower()}", f"{name.lower()} switch"],
                tags=["switch", "smart"]
            )
        else:
            # Generic mapping
            return await self.create_device_mapping(
                device_id=device_id,
                hub_id=hub_id,
                user_id=user_id,
                name=name,
                category=DeviceCategory.OTHER,
                room_id=room_id,
                controls=[ControlMapping(name="Power", description="Turn device on/off")],
                voice_aliases=[name.lower()],
                tags=["smart"]
            )
            
    async def get_device_mapping(self, mapping_id: str) -> Optional[DeviceMapping]:
        """Get a device mapping by ID."""
        return self._mappings.get(mapping_id)
        
    async def get_device_mapping_by_device_id(self, device_id: str) -> Optional[DeviceMapping]:
        """Get a device mapping by device ID."""
        mapping_id = self._device_mappings.get(device_id)
        if mapping_id:
            return self._mappings.get(mapping_id)
        return None
        
    async def get_user_mappings(self, user_id: str) -> List[DeviceMapping]:
        """Get all mappings for a user."""
        mapping_ids = self._user_mappings.get(user_id, [])
        return [self._mappings[mapping_id] for mapping_id in mapping_ids if mapping_id in self._mappings]
        
    async def get_mappings_by_category(self, category: DeviceCategory) -> List[DeviceMapping]:
        """Get all mappings for a category."""
        mapping_ids = self._category_mappings.get(category, [])
        return [self._mappings[mapping_id] for mapping_id in mapping_ids if mapping_id in self._mappings]
        
    async def get_mappings_by_room(self, room_id: str) -> List[DeviceMapping]:
        """Get all mappings for a room."""
        return [mapping for mapping in self._mappings.values() if mapping.room_id == room_id]
        
    async def update_device_mapping(self, mapping_id: str, updates: Dict[str, Any]) -> Optional[DeviceMapping]:
        """Update a device mapping."""
        mapping = self._mappings.get(mapping_id)
        if not mapping:
            return None
            
        # Update fields
        for key, value in updates.items():
            if hasattr(mapping, key):
                setattr(mapping, key, value)
                
        mapping.updated_at = datetime.utcnow()
        
        # Update voice aliases if changed
        if "voice_aliases" in updates:
            # Remove old aliases
            for alias in mapping.voice_aliases:
                if alias.lower() in self._voice_aliases:
                    del self._voice_aliases[alias.lower()]
            # Add new aliases
            for alias in mapping.voice_aliases:
                self._voice_aliases[alias.lower()] = mapping_id
                
        logger.info(f"Updated device mapping {mapping_id}")
        return mapping
        
    async def delete_device_mapping(self, mapping_id: str) -> bool:
        """Delete a device mapping."""
        mapping = self._mappings.get(mapping_id)
        if not mapping:
            return False
            
        # Remove from all indexes
        if mapping.device_id in self._device_mappings:
            del self._device_mappings[mapping.device_id]
            
        if mapping.user_id in self._user_mappings:
            self._user_mappings[mapping.user_id] = [
                mid for mid in self._user_mappings[mapping.user_id] if mid != mapping_id
            ]
            
        if mapping.category in self._category_mappings:
            self._category_mappings[mapping.category] = [
                mid for mid in self._category_mappings[mapping.category] if mid != mapping_id
            ]
            
        # Remove voice aliases
        for alias in mapping.voice_aliases:
            if alias.lower() in self._voice_aliases:
                del self._voice_aliases[alias.lower()]
                
        # Remove mapping
        del self._mappings[mapping_id]
        
        logger.info(f"Deleted device mapping {mapping_id}")
        return True
        
    # Room Management Methods
    
    async def create_room(self, room_data: Dict[str, Any]) -> RoomMapping:
        """Create a new room."""
        room = RoomMapping.from_dict(room_data)
        self._rooms[room.room_id] = room
        logger.info(f"Created room: {room.name} (ID: {room.room_id})")
        return room
        
    async def get_room(self, room_id: str) -> Optional[RoomMapping]:
        """Get a room by ID."""
        return self._rooms.get(room_id)
        
    async def get_all_rooms(self) -> List[RoomMapping]:
        """Get all rooms."""
        return list(self._rooms.values())
        
    async def update_room(self, room_id: str, updates: Dict[str, Any]) -> Optional[RoomMapping]:
        """Update a room."""
        room = self._rooms.get(room_id)
        if not room:
            return None
            
        for key, value in updates.items():
            if hasattr(room, key):
                setattr(room, key, value)
                
        logger.info(f"Updated room: {room.name}")
        return room
        
    async def delete_room(self, room_id: str) -> bool:
        """Delete a room."""
        if room_id not in self._rooms:
            return False
            
        # Check if room has devices
        devices_in_room = await self.get_mappings_by_room(room_id)
        if devices_in_room:
            raise ValueError(f"Cannot delete room {room_id} - it contains {len(devices_in_room)} devices")
            
        room_name = self._rooms[room_id].name
        del self._rooms[room_id]
        logger.info(f"Deleted room: {room_name}")
        return True
        
    # Voice Integration Methods
    
    async def find_device_by_voice_alias(self, alias: str) -> Optional[DeviceMapping]:
        """Find a device by voice alias."""
        mapping_id = self._voice_aliases.get(alias.lower())
        if mapping_id:
            return self._mappings.get(mapping_id)
        return None
        
    async def get_voice_aliases(self) -> Dict[str, str]:
        """Get all voice aliases."""
        return self._voice_aliases.copy()
        
    # Control Methods
    
    async def get_device_controls(self, mapping_id: str) -> List[ControlMapping]:
        """Get controls for a device mapping."""
        mapping = self._mappings.get(mapping_id)
        if mapping:
            return mapping.controls
        return []
        
    async def add_device_control(self, mapping_id: str, control: ControlMapping) -> bool:
        """Add a control to a device mapping."""
        mapping = self._mappings.get(mapping_id)
        if not mapping:
            return False
            
        mapping.controls.append(control)
        mapping.updated_at = datetime.utcnow()
        logger.info(f"Added control {control.name} to device {mapping.name}")
        return True
        
    async def update_device_control(self, mapping_id: str, control_id: str, updates: Dict[str, Any]) -> bool:
        """Update a device control."""
        mapping = self._mappings.get(mapping_id)
        if not mapping:
            return False
            
        for control in mapping.controls:
            if control.control_id == control_id:
                for key, value in updates.items():
                    if hasattr(control, key):
                        setattr(control, key, value)
                mapping.updated_at = datetime.utcnow()
                logger.info(f"Updated control {control.name} for device {mapping.name}")
                return True
                
        return False
        
    # User Preference Methods
    
    async def get_user_preferences(self, user_id: str, device_id: str) -> Optional[UserPreference]:
        """Get user preferences for a device."""
        mapping = await self.get_device_mapping_by_device_id(device_id)
        if mapping and mapping.user_preferences.user_id == user_id:
            return mapping.user_preferences
        return None
        
    async def update_user_preferences(self, user_id: str, device_id: str, preferences: Dict[str, Any]) -> bool:
        """Update user preferences for a device."""
        mapping = await self.get_device_mapping_by_device_id(device_id)
        if not mapping:
            return False
            
        for key, value in preferences.items():
            if hasattr(mapping.user_preferences, key):
                setattr(mapping.user_preferences, key, value)
                
        mapping.updated_at = datetime.utcnow()
        logger.info(f"Updated preferences for user {user_id} device {device_id}")
        return True
        
    # Statistics and Reporting
    
    async def get_mapper_statistics(self) -> Dict[str, Any]:
        """Get mapper statistics."""
        return self._stats.copy()
        
    async def get_mapping_summary(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get a summary of mappings."""
        if user_id:
            mappings = await self.get_user_mappings(user_id)
        else:
            mappings = list(self._mappings.values())
            
        summary = {
            "total_devices": len(mappings),
            "by_category": {},
            "by_room": {},
            "by_status": {},
            "recently_used": [],
            "favorites": []
        }
        
        for mapping in mappings:
            # Category breakdown
            category = mapping.category.value
            summary["by_category"][category] = summary["by_category"].get(category, 0) + 1
            
            # Room breakdown
            room = mapping.room_id or "unassigned"
            summary["by_room"][room] = summary["by_room"].get(room, 0) + 1
            
            # Status breakdown
            status = mapping.status.value
            summary["by_status"][status] = summary["by_status"].get(status, 0) + 1
            
            # Recently used
            if mapping.last_used:
                summary["recently_used"].append({
                    "mapping_id": mapping.mapping_id,
                    "name": mapping.display_name,
                    "last_used": mapping.last_used.isoformat()
                })
                
            # Favorites
            if mapping.user_preferences.favorite:
                summary["favorites"].append({
                    "mapping_id": mapping.mapping_id,
                    "name": mapping.display_name,
                    "category": mapping.category.value
                })
                
        # Sort recently used by timestamp
        summary["recently_used"].sort(key=lambda x: x["last_used"], reverse=True)
        summary["recently_used"] = summary["recently_used"][:10]  # Top 10
        
        return summary
        
    # Search and Discovery
    
    async def search_devices(self, query: str, user_id: Optional[str] = None) -> List[DeviceMapping]:
        """Search for devices by name, alias, or tag."""
        query = query.lower()
        results = []
        
        mappings = await self.get_user_mappings(user_id) if user_id else list(self._mappings.values())
        
        for mapping in mappings:
            # Search in name
            if query in mapping.name.lower() or query in mapping.display_name.lower():
                results.append(mapping)
                continue
                
            # Search in voice aliases
            if any(query in alias.lower() for alias in mapping.voice_aliases):
                results.append(mapping)
                continue
                
            # Search in tags
            if any(query in tag.lower() for tag in mapping.tags):
                results.append(mapping)
                continue
                
        return results
        
    async def discover_devices_for_mapping(self, hub_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Discover devices available for mapping from a hub."""
        # This would integrate with the IoT hub manager to get available devices
        # For now, return a mock list
        return [
            {
                "device_id": f"device_{hub_id}_1",
                "name": "Living Room Light",
                "type": "light",
                "capabilities": ["on/off", "dimming", "color"],
                "status": "online"
            },
            {
                "device_id": f"device_{hub_id}_2", 
                "name": "Kitchen Thermostat",
                "type": "thermostat",
                "capabilities": ["temperature", "mode"],
                "status": "online"
            }
        ]
