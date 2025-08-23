"""
Device Onboarding Workflow
Manages the device onboarding process from discovery to full integration.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from enum import Enum

from ..agent import DeviceInfo, ConnectionStatus

logger = logging.getLogger(__name__)


class OnboardingStep(Enum):
    """Onboarding workflow steps."""
    DISCOVERED = "discovered"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    ESTABLISHING_TRUST = "establishing_trust"
    TRUSTED = "trusted"
    CONFIGURING = "configuring"
    CONFIGURED = "configured"
    INTEGRATED = "integrated"
    FAILED = "failed"


class OnboardingWorkflow:
    """Manages device onboarding workflow."""
    
    def __init__(self):
        self._workflows: Dict[str, Dict[str, Any]] = {}
        self._step_handlers: Dict[OnboardingStep, Callable] = {}
        self._setup_step_handlers()
        
    def _setup_step_handlers(self):
        """Setup handlers for each onboarding step."""
        self._step_handlers = {
            OnboardingStep.DISCOVERED: self._handle_discovered,
            OnboardingStep.CONNECTING: self._handle_connecting,
            OnboardingStep.CONNECTED: self._handle_connected,
            OnboardingStep.AUTHENTICATING: self._handle_authenticating,
            OnboardingStep.AUTHENTICATED: self._handle_authenticated,
            OnboardingStep.ESTABLISHING_TRUST: self._handle_establishing_trust,
            OnboardingStep.TRUSTED: self._handle_trusted,
            OnboardingStep.CONFIGURING: self._handle_configuring,
            OnboardingStep.CONFIGURED: self._handle_configured,
            OnboardingStep.INTEGRATED: self._handle_integrated,
            OnboardingStep.FAILED: self._handle_failed
        }
        
    async def start_onboarding(self, device_info: DeviceInfo) -> str:
        """Start onboarding workflow for a device."""
        workflow_id = f"onboarding_{device_info.device_id}_{datetime.utcnow().timestamp()}"
        
        workflow = {
            'id': workflow_id,
            'device_info': device_info,
            'current_step': OnboardingStep.DISCOVERED,
            'steps_completed': [],
            'steps_failed': [],
            'start_time': datetime.utcnow(),
            'last_updated': datetime.utcnow(),
            'status': 'running',
            'error': None
        }
        
        self._workflows[workflow_id] = workflow
        
        # Start the workflow
        asyncio.create_task(self._execute_workflow(workflow_id))
        
        logger.info(f"Started onboarding workflow {workflow_id} for device {device_info.name}")
        return workflow_id
        
    async def _execute_workflow(self, workflow_id: str):
        """Execute the onboarding workflow."""
        workflow = self._workflows[workflow_id]
        device_info = workflow['device_info']
        
        try:
            # Execute each step in sequence
            steps = [
                OnboardingStep.CONNECTING,
                OnboardingStep.CONNECTED,
                OnboardingStep.AUTHENTICATING,
                OnboardingStep.AUTHENTICATED,
                OnboardingStep.ESTABLISHING_TRUST,
                OnboardingStep.TRUSTED,
                OnboardingStep.CONFIGURING,
                OnboardingStep.CONFIGURED,
                OnboardingStep.INTEGRATED
            ]
            
            for step in steps:
                workflow['current_step'] = step
                workflow['last_updated'] = datetime.utcnow()
                
                logger.info(f"Workflow {workflow_id}: Executing step {step.value}")
                
                # Execute step handler
                handler = self._step_handlers.get(step)
                if handler:
                    success = await handler(device_info)
                    
                    if success:
                        workflow['steps_completed'].append(step.value)
                        logger.info(f"Workflow {workflow_id}: Step {step.value} completed")
                    else:
                        workflow['steps_failed'].append(step.value)
                        workflow['current_step'] = OnboardingStep.FAILED
                        workflow['status'] = 'failed'
                        workflow['error'] = f"Step {step.value} failed"
                        logger.error(f"Workflow {workflow_id}: Step {step.value} failed")
                        break
                else:
                    logger.warning(f"Workflow {workflow_id}: No handler for step {step.value}")
                    workflow['steps_completed'].append(step.value)
                    
                # Add delay between steps
                await asyncio.sleep(1)
                
            if workflow['status'] != 'failed':
                workflow['status'] = 'completed'
                logger.info(f"Workflow {workflow_id}: Completed successfully")
                
        except Exception as e:
            workflow['current_step'] = OnboardingStep.FAILED
            workflow['status'] = 'failed'
            workflow['error'] = str(e)
            logger.error(f"Workflow {workflow_id}: Failed with error: {e}")
            
    async def _handle_discovered(self, device_info: DeviceInfo) -> bool:
        """Handle discovered step."""
        logger.info(f"Device {device_info.name} discovered")
        return True
        
    async def _handle_connecting(self, device_info: DeviceInfo) -> bool:
        """Handle connecting step."""
        logger.info(f"Connecting to device {device_info.name}")
        
        # This would call the connection agent
        # For now, simulate connection
        await asyncio.sleep(2)
        
        # Simulate connection success/failure
        return True  # 90% success rate simulation
        
    async def _handle_connected(self, device_info: DeviceInfo) -> bool:
        """Handle connected step."""
        logger.info(f"Device {device_info.name} connected")
        device_info.status = ConnectionStatus.CONNECTED
        return True
        
    async def _handle_authenticating(self, device_info: DeviceInfo) -> bool:
        """Handle authenticating step."""
        logger.info(f"Authenticating device {device_info.name}")
        
        # This would call the connection agent's authenticate method
        # For now, simulate authentication
        await asyncio.sleep(1)
        
        # Simulate authentication success/failure
        return True  # 85% success rate simulation
        
    async def _handle_authenticated(self, device_info: DeviceInfo) -> bool:
        """Handle authenticated step."""
        logger.info(f"Device {device_info.name} authenticated")
        device_info.status = ConnectionStatus.AUTHENTICATED
        return True
        
    async def _handle_establishing_trust(self, device_info: DeviceInfo) -> bool:
        """Handle establishing trust step."""
        logger.info(f"Establishing trust with device {device_info.name}")
        
        # This would call the trust manager
        # For now, simulate trust establishment
        await asyncio.sleep(2)
        
        # Simulate trust establishment success/failure
        return True  # 80% success rate simulation
        
    async def _handle_trusted(self, device_info: DeviceInfo) -> bool:
        """Handle trusted step."""
        logger.info(f"Device {device_info.name} trusted")
        device_info.status = ConnectionStatus.TRUSTED
        return True
        
    async def _handle_configuring(self, device_info: DeviceInfo) -> bool:
        """Handle configuring step."""
        logger.info(f"Configuring device {device_info.name}")
        
        # This would configure device settings, capabilities, etc.
        # For now, simulate configuration
        await asyncio.sleep(1)
        
        # Simulate configuration success/failure
        return True  # 95% success rate simulation
        
    async def _handle_configured(self, device_info: DeviceInfo) -> bool:
        """Handle configured step."""
        logger.info(f"Device {device_info.name} configured")
        return True
        
    async def _handle_integrated(self, device_info: DeviceInfo) -> bool:
        """Handle integrated step."""
        logger.info(f"Device {device_info.name} integrated into system")
        return True
        
    async def _handle_failed(self, device_info: DeviceInfo) -> bool:
        """Handle failed step."""
        logger.error(f"Device {device_info.name} onboarding failed")
        device_info.status = ConnectionStatus.FAILED
        return False
        
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific workflow."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None
            
        return {
            'id': workflow['id'],
            'device_name': workflow['device_info'].name,
            'current_step': workflow['current_step'].value,
            'status': workflow['status'],
            'steps_completed': workflow['steps_completed'],
            'steps_failed': workflow['steps_failed'],
            'start_time': workflow['start_time'].isoformat(),
            'last_updated': workflow['last_updated'].isoformat(),
            'error': workflow['error']
        }
        
    def get_all_workflows(self) -> List[Dict[str, Any]]:
        """Get status of all workflows."""
        return [self.get_workflow_status(workflow_id) for workflow_id in self._workflows.keys()]
        
    def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return False
            
        if workflow['status'] == 'running':
            workflow['status'] = 'cancelled'
            workflow['current_step'] = OnboardingStep.FAILED
            workflow['error'] = 'Workflow cancelled by user'
            logger.info(f"Workflow {workflow_id} cancelled")
            return True
            
        return False
        
    def cleanup_completed_workflows(self, max_age_hours: int = 24):
        """Clean up completed workflows older than specified age."""
        cutoff_time = datetime.utcnow().timestamp() - (max_age_hours * 3600)
        
        workflows_to_remove = []
        for workflow_id, workflow in self._workflows.items():
            if (workflow['status'] in ['completed', 'failed', 'cancelled'] and 
                workflow['start_time'].timestamp() < cutoff_time):
                workflows_to_remove.append(workflow_id)
                
        for workflow_id in workflows_to_remove:
            del self._workflows[workflow_id]
            
        if workflows_to_remove:
            logger.info(f"Cleaned up {len(workflows_to_remove)} old workflows")
