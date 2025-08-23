"""
Enhanced IoT Discovery System

This module contains all 14 planned enhancements to make IoT device discovery
and onboarding easier for users.
"""

__version__ = "2.0.0"
__author__ = "Tetheritall Team"

# Import core components
from .core.enhanced_coordinator import EnhancedDiscoveryCoordinator
from .core.plugin_manager import PluginManager
from .core.event_bus import EventBus

# Import enhancement modules
from .recognition import ComputerVision, VoiceRecognition, NFCHandler
from .proactive import NetworkMonitor, BeaconScanner, EmailParser
from .wizards import BrandWizards, TroubleshootingAI, ProgressTracker
from .ai import PredictiveSuggestions, ErrorRecovery, LearningEngine
from .privacy import GranularControls, PrivacyScoring, DataRetention
from .security import DeviceFingerprinting, NetworkIsolation, FirmwareMonitor
from .ux import SimplifiedInterface, SmartNotifications, Accessibility
from .performance import ParallelDiscovery, Caching, BackgroundProcessing
from .integrations import VoiceAssistants, SmartHomeStandards, CloudSync
from .analytics import SetupAnalytics, UserBehavior, ABTesting
from .management import DeviceGroups, RemoteAccess, MaintenanceScheduler
from .community import SetupSharing, TroubleshootingForum, DeviceReviews

__all__ = [
    # Core
    "EnhancedDiscoveryCoordinator",
    "PluginManager", 
    "EventBus",
    
    # Recognition
    "ComputerVision",
    "VoiceRecognition", 
    "NFCHandler",
    
    # Proactive
    "NetworkMonitor",
    "BeaconScanner",
    "EmailParser",
    
    # Wizards
    "BrandWizards",
    "TroubleshootingAI",
    "ProgressTracker",
    
    # AI
    "PredictiveSuggestions",
    "ErrorRecovery",
    "LearningEngine",
    
    # Privacy
    "GranularControls",
    "PrivacyScoring", 
    "DataRetention",
    
    # Security
    "DeviceFingerprinting",
    "NetworkIsolation",
    "FirmwareMonitor",
    
    # UX
    "SimplifiedInterface",
    "SmartNotifications",
    "Accessibility",
    
    # Performance
    "ParallelDiscovery",
    "Caching",
    "BackgroundProcessing",
    
    # Integrations
    "VoiceAssistants",
    "SmartHomeStandards",
    "CloudSync",
    
    # Analytics
    "SetupAnalytics",
    "UserBehavior",
    "ABTesting",
    
    # Management
    "DeviceGroups",
    "RemoteAccess",
    "MaintenanceScheduler",
    
    # Community
    "SetupSharing",
    "TroubleshootingForum",
    "DeviceReviews",
]
