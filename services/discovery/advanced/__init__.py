"""
Advanced IoT Discovery System - Optimizations 15-30

This module contains all 16 additional advanced optimizations that extend
the existing 14 enhancements with cutting-edge features.
"""

__version__ = "3.0.0"
__author__ = "Tetheritall Team"

# Import core components
from .core.advanced_coordinator import AdvancedDiscoveryCoordinator
from .core.federated_learning import FederatedLearningManager
from .core.edge_ai import EdgeAIManager
from .core.distributed_computing import DistributedComputingManager

# Import AI & ML components
from .ai.edge_models import EdgeModelManager
from .ai.federated_learning import FederatedLearningEngine
from .ai.model_compression import ModelCompressionEngine
from .ai.incremental_learning import IncrementalLearningEngine

# Import multimodal components
from .multimodal.cross_protocol_correlation import CrossProtocolCorrelator
from .multimodal.behavioral_fingerprinting import BehavioralFingerprinter
from .multimodal.temporal_analysis import TemporalAnalyzer
from .multimodal.contextual_awareness import ContextualAwarenessEngine

# Import network components
from .network.topology_mapping import NetworkTopologyMapper
from .network.traffic_analysis import TrafficAnalyzer
from .network.protocol_bridging import ProtocolBridgeManager
from .network.load_balancing import LoadBalancer

# Import maintenance components
from .maintenance.health_monitoring import HealthMonitor
from .maintenance.predictive_maintenance import PredictiveMaintenanceEngine
from .maintenance.usage_optimization import UsageOptimizer
from .maintenance.energy_efficiency import EnergyEfficiencyManager

# Import UX components
from .ux.adaptive_interfaces import AdaptiveInterfaceManager
from .ux.gesture_control import GestureController
from .ux.augmented_reality import AugmentedRealityManager
from .ux.haptic_feedback import HapticFeedbackManager

# Import blockchain components
from .blockchain.device_identity import DeviceIdentityManager
from .blockchain.decentralized_trust import DecentralizedTrustManager
from .blockchain.smart_contracts import SmartContractManager
from .blockchain.audit_trails import AuditTrailManager

# Import security components
from .security.zero_knowledge_proofs import ZeroKnowledgeProofManager
from .security.homomorphic_encryption import HomomorphicEncryptionManager
from .security.differential_privacy import DifferentialPrivacyManager
from .security.quantum_resistant import QuantumResistantCryptoManager

# Import ecosystem components
from .ecosystem.marketplace_integration import MarketplaceIntegrator
from .ecosystem.third_party_connectors import ThirdPartyConnectorManager
from .ecosystem.api_gateway import APIGatewayManager
from .ecosystem.service_mesh import ServiceMeshManager

# Import analytics components
from .analytics.predictive_analytics import PredictiveAnalyticsEngine
from .analytics.anomaly_detection import AnomalyDetector
from .analytics.usage_optimization import UsageOptimizationAnalytics
from .analytics.roi_analysis import ROIAnalyzer

# Import mobile components
from .mobile.progressive_web_app import ProgressiveWebAppManager
from .mobile.offline_first import OfflineFirstManager
from .mobile.mobile_features import MobileFeaturesManager
from .mobile.cross_platform_sync import CrossPlatformSyncManager

# Import enterprise components
from .enterprise.multi_user_management import MultiUserManager
from .enterprise.role_based_access import RoleBasedAccessManager
from .enterprise.audit_logging import AuditLoggingManager
from .enterprise.compliance_reporting import ComplianceReportingManager

# Import automation components
from .automation.workflow_automation import WorkflowAutomationManager
from .automation.conditional_logic import ConditionalLogicManager
from .automation.integration_testing import IntegrationTestingManager
from .automation.rollback_capabilities import RollbackCapabilitiesManager

# Import edge computing components
from .edge_computing.edge_processing import EdgeProcessingManager
from .edge_computing.fog_computing import FogComputingManager
from .edge_computing.local_decision_making import LocalDecisionMakingManager
from .edge_computing.bandwidth_optimization import BandwidthOptimizationManager

# Import device capabilities components
from .device_capabilities.device_cloning import DeviceCloningManager
from .device_capabilities.template_management import TemplateManagementManager
from .device_capabilities.version_control import VersionControlManager
from .device_capabilities.migration_tools import MigrationToolsManager

# Import social components
from .social.device_sharing import DeviceSharingManager
from .social.collaborative_setup import CollaborativeSetupManager
from .social.expert_mode import ExpertModeManager
from .social.community_challenges import CommunityChallengesManager

# Import sustainability components
from .sustainability.energy_monitoring import EnergyMonitoringManager
from .sustainability.carbon_footprint import CarbonFootprintManager
from .sustainability.sustainable_practices import SustainablePracticesManager
from .sustainability.recycling_integration import RecyclingIntegrationManager

__all__ = [
    # Core
    "AdvancedDiscoveryCoordinator",
    "FederatedLearningManager",
    "EdgeAIManager",
    "DistributedComputingManager",

    # AI & ML
    "EdgeModelManager",
    "FederatedLearningEngine",
    "ModelCompressionEngine",
    "IncrementalLearningEngine",

    # Multimodal
    "CrossProtocolCorrelator",
    "BehavioralFingerprinter",
    "TemporalAnalyzer",
    "ContextualAwarenessEngine",

    # Network
    "NetworkTopologyMapper",
    "TrafficAnalyzer",
    "ProtocolBridgeManager",
    "LoadBalancer",

    # Maintenance
    "HealthMonitor",
    "PredictiveMaintenanceEngine",
    "UsageOptimizer",
    "EnergyEfficiencyManager",

    # UX
    "AdaptiveInterfaceManager",
    "GestureController",
    "AugmentedRealityManager",
    "HapticFeedbackManager",

    # Blockchain
    "DeviceIdentityManager",
    "DecentralizedTrustManager",
    "SmartContractManager",
    "AuditTrailManager",

    # Security
    "ZeroKnowledgeProofManager",
    "HomomorphicEncryptionManager",
    "DifferentialPrivacyManager",
    "QuantumResistantCryptoManager",

    # Ecosystem
    "MarketplaceIntegrator",
    "ThirdPartyConnectorManager",
    "APIGatewayManager",
    "ServiceMeshManager",

    # Analytics
    "PredictiveAnalyticsEngine",
    "AnomalyDetector",
    "UsageOptimizationAnalytics",
    "ROIAnalyzer",

    # Mobile
    "ProgressiveWebAppManager",
    "OfflineFirstManager",
    "MobileFeaturesManager",
    "CrossPlatformSyncManager",

    # Enterprise
    "MultiUserManager",
    "RoleBasedAccessManager",
    "AuditLoggingManager",
    "ComplianceReportingManager",

    # Automation
    "WorkflowAutomationManager",
    "ConditionalLogicManager",
    "IntegrationTestingManager",
    "RollbackCapabilitiesManager",

    # Edge Computing
    "EdgeProcessingManager",
    "FogComputingManager",
    "LocalDecisionMakingManager",
    "BandwidthOptimizationManager",

    # Device Capabilities
    "DeviceCloningManager",
    "TemplateManagementManager",
    "VersionControlManager",
    "MigrationToolsManager",

    # Social
    "DeviceSharingManager",
    "CollaborativeSetupManager",
    "ExpertModeManager",
    "CommunityChallengesManager",

    # Sustainability
    "EnergyMonitoringManager",
    "CarbonFootprintManager",
    "SustainablePracticesManager",
    "RecyclingIntegrationManager",
]
