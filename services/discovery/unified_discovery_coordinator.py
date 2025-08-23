"""
Unified Discovery Coordinator

Coordinates the Resource Lookup Agent (RLA) and Connection Opportunity Agent (COA)
to provide a complete IoT discovery and connection solution.

This coordinator manages the workflow between the two agents, handles state transitions,
and provides a unified interface for the rest of the system.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Set
from enum import Enum
import json
import uuid

from pydantic import BaseModel, Field

from .resource_lookup_agent import (
    ResourceLookupAgent, DeviceHint, AccountHint, EnvironmentContext, 
    UserPreferences, TriggerType as RLATriggerType, PrivacyTier
)
from .connection_opportunity_agent import (
    ConnectionOpportunityAgent, NetworkDiscovery, UserConstraints,
    TriggerType as COATriggerType, DiscoveryType, CapabilityType
)
from shared.config.policy import ConsentPolicy
from shared.database.api_database import get_session_factory, session_scope
from shared.database.models import Device, ApiEndpoint, ScanResult


logger = logging.getLogger(__name__)


class CoordinatorState(Enum):
    IDLE = "idle"
    RESOURCE_LOOKUP = "resource_lookup"
    CONNECTION_OPPORTUNITY = "connection_opportunity"
    TROUBLESHOOTING = "troubleshooting"
    LEARNING = "learning"


class WorkflowType(Enum):
    FIRST_TIME_SETUP = "first_time_setup"
    DEVICE_ADDITION = "device_addition"
    TROUBLESHOOTING = "troubleshooting"
    OPPORTUNITY_DISCOVERY = "opportunity_discovery"
    ACCOUNT_LINKING = "account_linking"


@dataclass
class CoordinatorConfig:
    """Configuration for the unified coordinator."""
    database_url: str = "sqlite:///./iot_discovery.db"
    max_concurrent_workflows: int = 3
    learning_enabled: bool = True
    privacy_by_default: bool = True
    gdpr_compliant: bool = True
    edge_first: bool = True
    cloud_fallback: bool = True
    
    # Agent-specific configs
    rla_config: Dict[str, Any] = field(default_factory=dict)
    coa_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowContext:
    """Context for a discovery workflow."""
    workflow_id: str
    workflow_type: WorkflowType
    user_id: str
    session_id: str
    start_time: datetime
    current_state: CoordinatorState
    progress: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class UnifiedDiscoveryCoordinator:
    """Main coordinator for IoT discovery workflows."""
    
    def __init__(self, config: Optional[CoordinatorConfig] = None):
        self.config = config or CoordinatorConfig()
        self._session_factory = get_session_factory(self.config.database_url)
        
        # Initialize agents
        self.rla = ResourceLookupAgent(self.config.rla_config)
        self.coa = ConnectionOpportunityAgent(self.config.coa_config)
        
        # Internal state
        self.active_workflows: Dict[str, WorkflowContext] = {}
        self.workflow_queue: asyncio.Queue = asyncio.Queue()
        self.state_subscribers: List[asyncio.Queue] = []
        self._running = False
        
        # Privacy and consent tracking
        self.consent_policy = ConsentPolicy()
        self.privacy_audit_log: List[Dict[str, Any]] = []
        
    async def start(self) -> None:
        """Start the coordinator."""
        self._running = True
        logger.info("Unified Discovery Coordinator started")
        
        # Start workflow processor
        asyncio.create_task(self._workflow_processor())
        
    async def stop(self) -> None:
        """Stop the coordinator."""
        self._running = False
        logger.info("Unified Discovery Coordinator stopped")
        
    def subscribe_state(self) -> asyncio.Queue:
        """Subscribe to state updates."""
        q: asyncio.Queue = asyncio.Queue()
        self.state_subscribers.append(q)
        return q
        
    def unsubscribe_state(self, q: asyncio.Queue) -> None:
        """Unsubscribe from state updates."""
        if q in self.state_subscribers:
            self.state_subscribers.remove(q)
    
    async def _broadcast_state(self, message: Dict[str, Any]) -> None:
        """Broadcast state update to subscribers."""
        for q in list(self.state_subscribers):
            try:
                q.put_nowait(message)
            except Exception:
                self.unsubscribe_state(q)
    
    async def _workflow_processor(self) -> None:
        """Process workflow queue."""
        while self._running:
            try:
                workflow = await asyncio.wait_for(self.workflow_queue.get(), timeout=1.0)
                await self._process_workflow(workflow)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing workflow: {e}")
    
    async def _process_workflow(self, workflow: WorkflowContext) -> None:
        """Process a single workflow."""
        try:
            logger.info(f"Processing workflow {workflow.workflow_id}: {workflow.workflow_type}")
            
            if workflow.workflow_type == WorkflowType.FIRST_TIME_SETUP:
                await self._handle_first_time_setup(workflow)
            elif workflow.workflow_type == WorkflowType.DEVICE_ADDITION:
                await self._handle_device_addition(workflow)
            elif workflow.workflow_type == WorkflowType.TROUBLESHOOTING:
                await self._handle_troubleshooting(workflow)
            elif workflow.workflow_type == WorkflowType.OPPORTUNITY_DISCOVERY:
                await self._handle_opportunity_discovery(workflow)
            elif workflow.workflow_type == WorkflowType.ACCOUNT_LINKING:
                await self._handle_account_linking(workflow)
            
            # Mark workflow as complete
            workflow.current_state = CoordinatorState.IDLE
            await self._broadcast_state({
                "type": "workflow_complete",
                "workflow_id": workflow.workflow_id,
                "results": workflow.results,
            })
            
        except Exception as e:
            logger.error(f"Error in workflow {workflow.workflow_id}: {e}")
            workflow.current_state = CoordinatorState.IDLE
            workflow.results["error"] = str(e)
    
    async def start_first_time_setup(self, user_id: str, session_id: str,
                                   initial_preferences: Optional[Dict[str, Any]] = None) -> str:
        """Start first-time setup workflow."""
        workflow_id = str(uuid.uuid4())
        workflow = WorkflowContext(
            workflow_id=workflow_id,
            workflow_type=WorkflowType.FIRST_TIME_SETUP,
            user_id=user_id,
            session_id=session_id,
            start_time=datetime.now(),
            current_state=CoordinatorState.RESOURCE_LOOKUP,
            metadata={"initial_preferences": initial_preferences or {}},
        )
        
        self.active_workflows[workflow_id] = workflow
        await self.workflow_queue.put(workflow)
        
        await self._broadcast_state({
            "type": "workflow_started",
            "workflow_id": workflow_id,
            "workflow_type": "first_time_setup",
        })
        
        return workflow_id
    
    async def add_device(self, user_id: str, session_id: str,
                        device_hint: DeviceHint,
                        account_hint: Optional[AccountHint] = None) -> str:
        """Start device addition workflow."""
        workflow_id = str(uuid.uuid4())
        workflow = WorkflowContext(
            workflow_id=workflow_id,
            workflow_type=WorkflowType.DEVICE_ADDITION,
            user_id=user_id,
            session_id=session_id,
            start_time=datetime.now(),
            current_state=CoordinatorState.RESOURCE_LOOKUP,
            metadata={"device_hint": device_hint, "account_hint": account_hint},
        )
        
        self.active_workflows[workflow_id] = workflow
        await self.workflow_queue.put(workflow)
        
        return workflow_id
    
    async def start_opportunity_discovery(self, user_id: str, session_id: str,
                                        user_constraints: UserConstraints,
                                        env_context: Dict[str, Any]) -> str:
        """Start opportunity discovery workflow."""
        workflow_id = str(uuid.uuid4())
        workflow = WorkflowContext(
            workflow_id=workflow_id,
            workflow_type=WorkflowType.OPPORTUNITY_DISCOVERY,
            user_id=user_id,
            session_id=session_id,
            start_time=datetime.now(),
            current_state=CoordinatorState.CONNECTION_OPPORTUNITY,
            metadata={"user_constraints": user_constraints, "env_context": env_context},
        )
        
        self.active_workflows[workflow_id] = workflow
        await self.workflow_queue.put(workflow)
        
        return workflow_id
    
    async def troubleshoot_connection(self, user_id: str, session_id: str,
                                    error_message: str, context: Dict[str, Any]) -> str:
        """Start troubleshooting workflow."""
        workflow_id = str(uuid.uuid4())
        workflow = WorkflowContext(
            workflow_id=workflow_id,
            workflow_type=WorkflowType.TROUBLESHOOTING,
            user_id=user_id,
            session_id=session_id,
            start_time=datetime.now(),
            current_state=CoordinatorState.TROUBLESHOOTING,
            metadata={"error_message": error_message, "context": context},
        )
        
        self.active_workflows[workflow_id] = workflow
        await self.workflow_queue.put(workflow)
        
        return workflow_id
    
    async def _handle_first_time_setup(self, workflow: WorkflowContext) -> None:
        """Handle first-time setup workflow."""
        logger.info(f"Starting first-time setup for user {workflow.user_id}")
        
        # Step 1: Environment assessment
        workflow.current_state = CoordinatorState.RESOURCE_LOOKUP
        await self._broadcast_state({
            "type": "state_change",
            "workflow_id": workflow.workflow_id,
            "state": "assessing_environment",
        })
        
        env_context = await self._assess_environment()
        workflow.progress["environment_assessed"] = True
        workflow.results["environment"] = env_context
        
        # Step 2: Initial opportunity discovery
        workflow.current_state = CoordinatorState.CONNECTION_OPPORTUNITY
        await self._broadcast_state({
            "type": "state_change",
            "workflow_id": workflow.workflow_id,
            "state": "discovering_opportunities",
        })
        
        # Mock discoveries for first-time setup
        mock_discoveries = await self._generate_mock_discoveries()
        
        user_constraints = UserConstraints(
            privacy_tier="standard",
            time_budget_minutes=60,
            noise_sensitivity=False,
        )
        
        opportunity_results = await self.coa.process_discoveries(
            mock_discoveries, user_constraints, env_context
        )
        
        workflow.progress["opportunities_discovered"] = True
        workflow.results["opportunities"] = opportunity_results
        
        # Step 3: Generate onboarding plan
        workflow.current_state = CoordinatorState.LEARNING
        await self._broadcast_state({
            "type": "state_change",
            "workflow_id": workflow.workflow_id,
            "state": "generating_plan",
        })
        
        onboarding_plan = self._generate_onboarding_plan(opportunity_results, env_context)
        workflow.results["onboarding_plan"] = onboarding_plan
        
        logger.info(f"First-time setup completed for user {workflow.user_id}")
    
    async def _handle_device_addition(self, workflow: WorkflowContext) -> None:
        """Handle device addition workflow."""
        device_hint = workflow.metadata["device_hint"]
        account_hint = workflow.metadata.get("account_hint")
        
        logger.info(f"Adding device for user {workflow.user_id}: {device_hint}")
        
        # Step 1: Resource lookup
        workflow.current_state = CoordinatorState.RESOURCE_LOOKUP
        await self._broadcast_state({
            "type": "state_change",
            "workflow_id": workflow.workflow_id,
            "state": "looking_up_resources",
        })
        
        env_context = await self._assess_environment()
        user_prefs = UserPreferences(privacy_tier=PrivacyTier.STANDARD)
        
        rla_results = await self.rla.process_device_hint(
            device_hint, account_hint, env_context, user_prefs, RLATriggerType.DEVICE_DECLARATION
        )
        
        workflow.progress["resources_looked_up"] = True
        workflow.results["resource_lookup"] = rla_results
        
        # Step 2: Execute connection flow
        if rla_results["scores"]["readiness_score"] > 0.5:
            workflow.current_state = CoordinatorState.CONNECTION_OPPORTUNITY
            await self._broadcast_state({
                "type": "state_change",
                "workflow_id": workflow.workflow_id,
                "state": "executing_connection",
            })
            
            # Execute the connection flow
            connection_result = await self._execute_connection_flow(rla_results)
            workflow.results["connection_result"] = connection_result
            
            # Step 3: Look for additional opportunities
            if connection_result.get("success"):
                await self._handle_post_connection_opportunities(workflow)
        
        logger.info(f"Device addition completed for user {workflow.user_id}")
    
    async def _handle_troubleshooting(self, workflow: WorkflowContext) -> None:
        """Handle troubleshooting workflow."""
        error_message = workflow.metadata["error_message"]
        context = workflow.metadata["context"]
        
        logger.info(f"Troubleshooting for user {workflow.user_id}: {error_message}")
        
        workflow.current_state = CoordinatorState.TROUBLESHOOTING
        await self._broadcast_state({
            "type": "state_change",
            "workflow_id": workflow.workflow_id,
            "state": "analyzing_error",
        })
        
        # Use RLA's troubleshooting capabilities
        troubleshoot_results = await self.rla.troubleshoot_failure(error_message, context)
        
        workflow.results["troubleshoot"] = troubleshoot_results
        
        # If troubleshooting suggests device addition, trigger that workflow
        if troubleshoot_results.get("recommended_fixes"):
            # Check if any fixes involve adding new devices
            for fix in troubleshoot_results["recommended_fixes"]:
                if "add device" in fix["fix"].lower():
                    # Trigger device addition workflow
                    device_hint = DeviceHint(brand="unknown", model="unknown")
                    await self.add_device(workflow.user_id, workflow.session_id, device_hint)
                    break
        
        logger.info(f"Troubleshooting completed for user {workflow.user_id}")
    
    async def _handle_opportunity_discovery(self, workflow: WorkflowContext) -> None:
        """Handle opportunity discovery workflow."""
        user_constraints = workflow.metadata["user_constraints"]
        env_context = workflow.metadata["env_context"]
        
        logger.info(f"Opportunity discovery for user {workflow.user_id}")
        
        workflow.current_state = CoordinatorState.CONNECTION_OPPORTUNITY
        await self._broadcast_state({
            "type": "state_change",
            "workflow_id": workflow.workflow_id,
            "state": "scanning_network",
        })
        
        # Perform network discovery
        discoveries = await self._perform_network_discovery(env_context)
        
        # Process discoveries
        opportunity_results = await self.coa.process_discoveries(
            discoveries, user_constraints, env_context
        )
        
        workflow.results["opportunities"] = opportunity_results
        
        logger.info(f"Opportunity discovery completed for user {workflow.user_id}")
    
    async def _handle_account_linking(self, workflow: WorkflowContext) -> None:
        """Handle account linking workflow."""
        logger.info(f"Account linking for user {workflow.user_id}")
        
        # This would involve the RLA to look up provider information
        # and the COA to suggest account linking opportunities
        workflow.results["account_linking"] = {"status": "not_implemented"}
        
        logger.info(f"Account linking completed for user {workflow.user_id}")
    
    async def _assess_environment(self) -> EnvironmentContext:
        """Assess the current environment."""
        # TODO: Implement actual environment assessment
        # For now, return mock data
        return EnvironmentContext(
            ssid="HomeNetwork",
            band="5GHz",
            dhcp_enabled=True,
            bluetooth_available=True,
            wifi_6_available=True,
            matter_commissioning_available=True,
        )
    
    async def _generate_mock_discoveries(self) -> List[NetworkDiscovery]:
        """Generate mock discoveries for testing."""
        return [
            NetworkDiscovery(
                discovery_id="mock_1",
                discovery_type=DiscoveryType.BLE,
                device_info={"name": "Philips Hue Bulb", "manufacturer": "Philips"},
                protocol_candidates=["bluetooth", "zigbee"],
                confidence_score=0.9,
                timestamp=datetime.now(),
            ),
            NetworkDiscovery(
                discovery_id="mock_2",
                discovery_type=DiscoveryType.MDNS,
                device_info={"name": "IKEA Tradfri Gateway", "manufacturer": "IKEA"},
                protocol_candidates=["zigbee", "thread"],
                confidence_score=0.8,
                timestamp=datetime.now(),
            ),
        ]
    
    async def _perform_network_discovery(self, env_context: Dict[str, Any]) -> List[NetworkDiscovery]:
        """Perform actual network discovery."""
        # TODO: Implement actual network discovery
        # This would integrate with the existing network scanner
        return []
    
    async def _execute_connection_flow(self, rla_results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a connection flow from RLA results."""
        # TODO: Implement actual connection execution
        # This would involve following the steps in the connection flow
        return {"success": True, "steps_completed": 3}
    
    async def _handle_post_connection_opportunities(self, workflow: WorkflowContext) -> None:
        """Handle opportunities that arise after successful connection."""
        # Trigger opportunity discovery after successful connection
        user_constraints = UserConstraints(
            privacy_tier="standard",
            time_budget_minutes=15,
        )
        
        env_context = await self._assess_environment()
        await self.start_opportunity_discovery(
            workflow.user_id, workflow.session_id, user_constraints, env_context
        )
    
    def _generate_onboarding_plan(self, opportunity_results: Dict[str, Any], 
                                env_context: EnvironmentContext) -> Dict[str, Any]:
        """Generate onboarding plan for first-time users."""
        return {
            "recommended_devices": opportunity_results.get("selected_opportunities", [])[:3],
            "estimated_time": "30 minutes",
            "privacy_level": "standard",
            "next_steps": [
                "Connect your first smart light",
                "Set up basic automation",
                "Explore additional devices",
            ],
        }
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific workflow."""
        if workflow_id not in self.active_workflows:
            return None
        
        workflow = self.active_workflows[workflow_id]
        return {
            "workflow_id": workflow.workflow_id,
            "workflow_type": workflow.workflow_type.value,
            "current_state": workflow.current_state.value,
            "progress": workflow.progress,
            "results": workflow.results,
            "start_time": workflow.start_time.isoformat(),
            "duration": (datetime.now() - workflow.start_time).total_seconds(),
        }
    
    async def get_user_summary(self, user_id: str) -> Dict[str, Any]:
        """Get summary of user's discovery and connection status."""
        user_workflows = [
            w for w in self.active_workflows.values() 
            if w.user_id == user_id
        ]
        
        # Get coverage summary from COA
        coverage_summary = await self.coa.get_coverage_summary()
        
        return {
            "user_id": user_id,
            "active_workflows": len(user_workflows),
            "coverage_summary": coverage_summary,
            "recent_activity": [
                {
                    "workflow_id": w.workflow_id,
                    "type": w.workflow_type.value,
                    "start_time": w.start_time.isoformat(),
                }
                for w in user_workflows
            ],
        }
    
    async def record_user_action(self, workflow_id: str, action: str, 
                               data: Optional[Dict[str, Any]] = None) -> None:
        """Record user action for learning."""
        if workflow_id not in self.active_workflows:
            return
        
        workflow = self.active_workflows[workflow_id]
        
        # Record action for learning
        if self.config.learning_enabled:
            await self._record_learning_signal(workflow, action, data)
        
        # Update workflow progress
        workflow.progress[f"user_action_{action}"] = {
            "timestamp": datetime.now().isoformat(),
            "data": data or {},
        }
        
        logger.info(f"Recorded user action: {workflow_id} - {action}")
    
    async def _record_learning_signal(self, workflow: WorkflowContext, action: str, 
                                    data: Optional[Dict[str, Any]]) -> None:
        """Record learning signal for ML models."""
        # Record for RLA learning
        if workflow.workflow_type == WorkflowType.DEVICE_ADDITION:
            device_id = workflow.results.get("resource_lookup", {}).get("entity_profile", {}).get("canonical_device_id")
            if device_id:
                await self.rla.record_step_completion(
                    device_id, action, True, 0, data.get("feedback")
                )
        
        # Record for COA learning
        if workflow.workflow_type == WorkflowType.OPPORTUNITY_DISCOVERY:
            opportunities = workflow.results.get("opportunities", {}).get("selected_opportunities", [])
            for opp in opportunities:
                await self.coa.record_user_action(opp.opportunity_id, action, data)
    
    def get_privacy_audit_log(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get privacy audit log."""
        if user_id:
            return [log for log in self.privacy_audit_log if log.get("user_id") == user_id]
        return self.privacy_audit_log
    
    def _log_privacy_event(self, event_type: str, user_id: str, data: Dict[str, Any]) -> None:
        """Log privacy-related event."""
        if self.config.gdpr_compliant:
            self.privacy_audit_log.append({
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                "user_id": user_id,
                "data": data,
            })
