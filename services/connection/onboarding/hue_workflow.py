"""
Philips Hue Onboarding Workflow
Specialized onboarding workflow for Philips Hue devices and bridges.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

from ..agent import DeviceInfo, ConnectionStatus
from .workflow import OnboardingWorkflow, OnboardingStep

logger = logging.getLogger(__name__)


class HueOnboardingStep(Enum):
    """Philips Hue specific onboarding steps."""
    BRIDGE_DISCOVERY = "bridge_discovery"
    BRIDGE_PAIRING = "bridge_pairing"
    BRIDGE_CONNECTED = "bridge_connected"
    DEVICE_DISCOVERY = "device_discovery"
    DEVICE_ANALYSIS = "device_analysis"
    DEVICE_COMMISSIONING = "device_commissioning"
    CAPABILITY_MAPPING = "capability_mapping"
    INTEGRATION_COMPLETE = "integration_complete"


class HueOnboardingWorkflow(OnboardingWorkflow):
    """Specialized onboarding workflow for Philips Hue devices."""
    
    def __init__(self):
        super().__init__()
        self._hue_commissioning_service = None
        self._setup_hue_handlers()
        
    def _setup_hue_handlers(self):
        """Setup Hue-specific step handlers."""
        try:
            from iot_api_discovery.tools.hue.commissioning import HueCommissioningService
            self._hue_commissioning_service = HueCommissioningService()
        except ImportError:
            logger.warning("Hue commissioning service not available")
    
    async def start_hue_onboarding(self, bridge_ip: str, app_name: str = "iot-orchestrator", device_name: str = "server") -> str:
        """Start Hue-specific onboarding workflow."""
        workflow_id = f"hue_onboarding_{bridge_ip.replace('.', '_')}_{datetime.utcnow().timestamp()}"
        
        # Create device info for the bridge
        device_info = DeviceInfo(
            device_id=f"hue_bridge_{bridge_ip.replace('.', '_')}",
            name=f"Philips Hue Bridge ({bridge_ip})",
            model="Philips Hue Bridge",
            manufacturer="Philips",
            ip_address=bridge_ip,
            protocol="http",
            capabilities=["hub", "zigbee"],
            endpoints=[f"http://{bridge_ip}/api"],
            status=ConnectionStatus.DISCOVERED
        )
        
        workflow = {
            'id': workflow_id,
            'device_info': device_info,
            'current_step': HueOnboardingStep.BRIDGE_DISCOVERY,
            'steps_completed': [],
            'steps_failed': [],
            'start_time': datetime.utcnow(),
            'last_updated': datetime.utcnow(),
            'status': 'running',
            'error': None,
            'hue_specific': {
                'bridge_ip': bridge_ip,
                'app_name': app_name,
                'device_name': device_name,
                'discovered_devices': [],
                'commissioned_devices': []
            }
        }
        
        self._workflows[workflow_id] = workflow
        
        # Start the workflow
        asyncio.create_task(self._execute_hue_workflow(workflow_id))
        
        logger.info(f"Started Hue onboarding workflow {workflow_id} for bridge {bridge_ip}")
        return workflow_id
    
    async def _execute_hue_workflow(self, workflow_id: str):
        """Execute the Hue-specific onboarding workflow."""
        workflow = self._workflows[workflow_id]
        device_info = workflow['device_info']
        hue_data = workflow['hue_specific']
        
        try:
            # Execute Hue-specific steps
            steps = [
                HueOnboardingStep.BRIDGE_DISCOVERY,
                HueOnboardingStep.BRIDGE_PAIRING,
                HueOnboardingStep.BRIDGE_CONNECTED,
                HueOnboardingStep.DEVICE_DISCOVERY,
                HueOnboardingStep.DEVICE_ANALYSIS,
                HueOnboardingStep.DEVICE_COMMISSIONING,
                HueOnboardingStep.CAPABILITY_MAPPING,
                HueOnboardingStep.INTEGRATION_COMPLETE
            ]
            
            for step in steps:
                workflow['current_step'] = step
                workflow['last_updated'] = datetime.utcnow()
                
                logger.info(f"Hue workflow {workflow_id}: Executing step {step.value}")
                
                # Execute step handler
                handler = self._step_handlers.get(step)
                if handler:
                    success = await handler(device_info, hue_data)
                    
                    if success:
                        workflow['steps_completed'].append(step.value)
                        logger.info(f"Hue workflow {workflow_id}: Step {step.value} completed")
                    else:
                        workflow['steps_failed'].append(step.value)
                        workflow['current_step'] = OnboardingStep.FAILED
                        workflow['status'] = 'failed'
                        workflow['error'] = f"Hue step {step.value} failed"
                        logger.error(f"Hue workflow {workflow_id}: Step {step.value} failed")
                        break
                else:
                    logger.warning(f"Hue workflow {workflow_id}: No handler for step {step.value}")
                    workflow['steps_completed'].append(step.value)
                    
                # Add delay between steps
                await asyncio.sleep(1)
                
            if workflow['status'] != 'failed':
                workflow['status'] = 'completed'
                logger.info(f"Hue workflow {workflow_id}: Completed successfully")
                
        except Exception as e:
            workflow['current_step'] = OnboardingStep.FAILED
            workflow['status'] = 'failed'
            workflow['error'] = str(e)
            logger.error(f"Hue workflow {workflow_id}: Failed with error: {e}")
    
    async def _handle_bridge_discovery(self, device_info: DeviceInfo, hue_data: Dict[str, Any]) -> bool:
        """Handle bridge discovery step."""
        try:
            if not self._hue_commissioning_service:
                logger.error("Hue commissioning service not available")
                return False
            
            # Discover bridges
            bridges = await self._hue_commissioning_service.discover_hue_bridges()
            
            # Check if our target bridge is found
            target_ip = hue_data['bridge_ip']
            bridge_found = any(b['ip_address'] == target_ip for b in bridges)
            
            if bridge_found:
                logger.info(f"Bridge {target_ip} discovered successfully")
                device_info.status = ConnectionStatus.DISCOVERED
                return True
            else:
                logger.warning(f"Bridge {target_ip} not found in discovery results")
                return False
                
        except Exception as e:
            logger.error(f"Error in bridge discovery: {e}")
            return False
    
    async def _handle_bridge_pairing(self, device_info: DeviceInfo, hue_data: Dict[str, Any]) -> bool:
        """Handle bridge pairing step."""
        try:
            if not self._hue_commissioning_service:
                return False
            
            # Attempt pairing
            result = await self._hue_commissioning_service.pair_bridge(
                hue_data['bridge_ip'],
                hue_data['app_name'],
                hue_data['device_name']
            )
            
            if result.get('ok'):
                logger.info(f"Bridge {hue_data['bridge_ip']} paired successfully")
                device_info.status = ConnectionStatus.AUTHENTICATED
                hue_data['bridge_id'] = result.get('bridge_id')
                return True
            else:
                logger.warning(f"Bridge pairing failed: {result.get('message')}")
                return False
                
        except Exception as e:
            logger.error(f"Error in bridge pairing: {e}")
            return False
    
    async def _handle_bridge_connected(self, device_info: DeviceInfo, hue_data: Dict[str, Any]) -> bool:
        """Handle bridge connected step."""
        try:
            logger.info(f"Bridge {hue_data['bridge_ip']} connected and authenticated")
            device_info.status = ConnectionStatus.CONNECTED
            return True
            
        except Exception as e:
            logger.error(f"Error in bridge connection: {e}")
            return False
    
    async def _handle_device_discovery(self, device_info: DeviceInfo, hue_data: Dict[str, Any]) -> bool:
        """Handle device discovery step."""
        try:
            if not self._hue_commissioning_service or not hue_data.get('bridge_id'):
                return False
            
            # Discover devices on the bridge
            devices = await self._hue_commissioning_service.discover_devices(hue_data['bridge_id'])
            
            if devices:
                hue_data['discovered_devices'] = devices
                logger.info(f"Discovered {len(devices)} devices on bridge {hue_data['bridge_id']}")
                return True
            else:
                logger.warning(f"No devices discovered on bridge {hue_data['bridge_id']}")
                return False
                
        except Exception as e:
            logger.error(f"Error in device discovery: {e}")
            return False
    
    async def _handle_device_analysis(self, device_info: DeviceInfo, hue_data: Dict[str, Any]) -> bool:
        """Handle device analysis step."""
        try:
            devices = hue_data.get('discovered_devices', [])
            
            for device in devices:
                # Analyze device capabilities
                capabilities = device.get('capabilities', [])
                logger.info(f"Device {device['name']} has capabilities: {capabilities}")
                
                # Map capabilities to our system
                mapped_capabilities = []
                for cap in capabilities:
                    if cap == 'switchable':
                        mapped_capabilities.append('switch')
                    elif cap == 'dimmable':
                        mapped_capabilities.append('dimmer')
                    elif cap == 'color_control':
                        mapped_capabilities.append('color')
                    elif cap == 'color_temperature':
                        mapped_capabilities.append('temperature')
                
                device['mapped_capabilities'] = mapped_capabilities
            
            logger.info(f"Analyzed {len(devices)} devices")
            return True
            
        except Exception as e:
            logger.error(f"Error in device analysis: {e}")
            return False
    
    async def _handle_device_commissioning(self, device_info: DeviceInfo, hue_data: Dict[str, Any]) -> bool:
        """Handle device commissioning step."""
        try:
            devices = hue_data.get('discovered_devices', [])
            commissioned_count = 0
            
            for device in devices:
                # Test communication with each device
                test_result = await self._hue_commissioning_service.test_device_communication(
                    device['device_id']
                )
                
                if test_result.get('ok'):
                    # Commission the device
                    commission_result = await self._hue_commissioning_service.commission_device(
                        device['device_id'],
                        {'name': device['name']}
                    )
                    
                    if commission_result.get('ok'):
                        commissioned_count += 1
                        device['commissioned'] = True
                        device['commissioned_at'] = commission_result.get('commissioned_at')
                    else:
                        device['commissioned'] = False
                        device['commission_error'] = commission_result.get('message')
                else:
                    device['commissioned'] = False
                    device['commission_error'] = test_result.get('error')
            
            hue_data['commissioned_devices'] = [d for d in devices if d.get('commissioned')]
            logger.info(f"Commissioned {commissioned_count} out of {len(devices)} devices")
            
            return commissioned_count > 0
            
        except Exception as e:
            logger.error(f"Error in device commissioning: {e}")
            return False
    
    async def _handle_capability_mapping(self, device_info: DeviceInfo, hue_data: Dict[str, Any]) -> bool:
        """Handle capability mapping step."""
        try:
            devices = hue_data.get('commissioned_devices', [])
            
            for device in devices:
                # Map device capabilities to our capability registry
                capabilities = device.get('mapped_capabilities', [])
                
                # This would integrate with the capability registry
                # For now, just log the mapping
                logger.info(f"Mapped capabilities for {device['name']}: {capabilities}")
            
            logger.info(f"Mapped capabilities for {len(devices)} devices")
            return True
            
        except Exception as e:
            logger.error(f"Error in capability mapping: {e}")
            return False
    
    async def _handle_integration_complete(self, device_info: DeviceInfo, hue_data: Dict[str, Any]) -> bool:
        """Handle integration complete step."""
        try:
            logger.info(f"Hue integration complete for bridge {hue_data['bridge_ip']}")
            device_info.status = ConnectionStatus.INTEGRATED
            
            # Summary
            total_devices = len(hue_data.get('discovered_devices', []))
            commissioned_devices = len(hue_data.get('commissioned_devices', []))
            
            logger.info(f"Hue integration summary: {commissioned_devices}/{total_devices} devices commissioned")
            return True
            
        except Exception as e:
            logger.error(f"Error in integration completion: {e}")
            return False
    
    def get_hue_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific Hue workflow."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None
        
        base_status = self.get_workflow_status(workflow_id)
        if not base_status:
            return None
        
        # Add Hue-specific information
        hue_data = workflow.get('hue_specific', {})
        base_status.update({
            'bridge_ip': hue_data.get('bridge_ip'),
            'bridge_id': hue_data.get('bridge_id'),
            'discovered_devices_count': len(hue_data.get('discovered_devices', [])),
            'commissioned_devices_count': len(hue_data.get('commissioned_devices', [])),
            'discovered_devices': hue_data.get('discovered_devices', []),
            'commissioned_devices': hue_data.get('commissioned_devices', [])
        })
        
        return base_status
