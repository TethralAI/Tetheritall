"""
Device Verification
Handles device verification during onboarding process.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..agent import DeviceInfo

logger = logging.getLogger(__name__)


class DeviceVerification:
    """Handles device verification during onboarding."""
    
    def __init__(self):
        self._verification_results: Dict[str, Dict[str, Any]] = {}
        
    async def verify_device(self, device_info: DeviceInfo) -> Dict[str, Any]:
        """Perform comprehensive device verification."""
        verification_id = f"verify_{device_info.device_id}_{datetime.utcnow().timestamp()}"
        
        verification_result = {
            'id': verification_id,
            'device_id': device_info.device_id,
            'device_name': device_info.name,
            'verification_time': datetime.utcnow(),
            'overall_status': 'pending',
            'checks': {},
            'warnings': [],
            'errors': []
        }
        
        try:
            # Perform various verification checks
            checks = [
                ('identity', self._verify_identity),
                ('capabilities', self._verify_capabilities),
                ('communication', self._verify_communication),
                ('security', self._verify_security),
                ('compatibility', self._verify_compatibility)
            ]
            
            for check_name, check_function in checks:
                try:
                    check_result = await check_function(device_info)
                    verification_result['checks'][check_name] = check_result
                    
                    if not check_result['passed']:
                        verification_result['errors'].append(check_result['error'])
                    elif check_result.get('warning'):
                        verification_result['warnings'].append(check_result['warning'])
                        
                except Exception as e:
                    verification_result['checks'][check_name] = {
                        'passed': False,
                        'error': f"Verification check failed: {str(e)}"
                    }
                    verification_result['errors'].append(f"{check_name} check failed: {str(e)}")
                    
            # Determine overall status
            failed_checks = sum(1 for check in verification_result['checks'].values() if not check.get('passed', False))
            total_checks = len(verification_result['checks'])
            
            if failed_checks == 0:
                verification_result['overall_status'] = 'passed'
            elif failed_checks <= total_checks // 2:
                verification_result['overall_status'] = 'warning'
            else:
                verification_result['overall_status'] = 'failed'
                
            # Store result
            self._verification_results[verification_id] = verification_result
            
            logger.info(f"Device verification {verification_id} completed with status: {verification_result['overall_status']}")
            
        except Exception as e:
            verification_result['overall_status'] = 'failed'
            verification_result['errors'].append(f"Verification process failed: {str(e)}")
            logger.error(f"Device verification failed: {e}")
            
        return verification_result
        
    async def _verify_identity(self, device_info: DeviceInfo) -> Dict[str, Any]:
        """Verify device identity."""
        try:
            # Check device ID format
            if not device_info.device_id or len(device_info.device_id) < 3:
                return {
                    'passed': False,
                    'error': 'Invalid device ID format'
                }
                
            # Check device name
            if not device_info.name or len(device_info.name) < 1:
                return {
                    'passed': False,
                    'error': 'Device name is required'
                }
                
            # Check manufacturer
            if not device_info.manufacturer:
                return {
                    'passed': False,
                    'warning': 'Manufacturer information is missing'
                }
                
            # Check model
            if not device_info.model:
                return {
                    'passed': False,
                    'warning': 'Model information is missing'
                }
                
            return {
                'passed': True,
                'details': {
                    'device_id': device_info.device_id,
                    'name': device_info.name,
                    'manufacturer': device_info.manufacturer,
                    'model': device_info.model
                }
            }
            
        except Exception as e:
            return {
                'passed': False,
                'error': f'Identity verification failed: {str(e)}'
            }
            
    async def _verify_capabilities(self, device_info: DeviceInfo) -> Dict[str, Any]:
        """Verify device capabilities."""
        try:
            if not device_info.capabilities:
                return {
                    'passed': False,
                    'error': 'No capabilities defined'
                }
                
            if len(device_info.capabilities) == 0:
                return {
                    'passed': False,
                    'error': 'Empty capabilities list'
                }
                
            # Check for valid capability names
            valid_capabilities = [
                'network', 'bluetooth', 'wifi', 'zigbee', 'zwave', 'matter',
                'lighting', 'temperature_control', 'security', 'audio',
                'video', 'sensing', 'actuation', 'energy_monitoring',
                'health_monitoring', 'access_control', 'protocol_bridge'
            ]
            
            invalid_capabilities = []
            for capability in device_info.capabilities:
                if capability not in valid_capabilities:
                    invalid_capabilities.append(capability)
                    
            if invalid_capabilities:
                return {
                    'passed': False,
                    'error': f'Invalid capabilities: {invalid_capabilities}'
                }
                
            return {
                'passed': True,
                'details': {
                    'capabilities': device_info.capabilities,
                    'capability_count': len(device_info.capabilities)
                }
            }
            
        except Exception as e:
            return {
                'passed': False,
                'error': f'Capabilities verification failed: {str(e)}'
            }
            
    async def _verify_communication(self, device_info: DeviceInfo) -> Dict[str, Any]:
        """Verify device communication."""
        try:
            if not device_info.endpoints:
                return {
                    'passed': False,
                    'error': 'No communication endpoints defined'
                }
                
            if len(device_info.endpoints) == 0:
                return {
                    'passed': False,
                    'error': 'Empty endpoints list'
                }
                
            # Check endpoint format
            invalid_endpoints = []
            for endpoint in device_info.endpoints:
                if not self._is_valid_endpoint(endpoint):
                    invalid_endpoints.append(endpoint)
                    
            if invalid_endpoints:
                return {
                    'passed': False,
                    'error': f'Invalid endpoints: {invalid_endpoints}'
                }
                
            return {
                'passed': True,
                'details': {
                    'endpoints': device_info.endpoints,
                    'endpoint_count': len(device_info.endpoints)
                }
            }
            
        except Exception as e:
            return {
                'passed': False,
                'error': f'Communication verification failed: {str(e)}'
            }
            
    async def _verify_security(self, device_info: DeviceInfo) -> Dict[str, Any]:
        """Verify device security."""
        try:
            security_issues = []
            
            # Check protocol security
            if device_info.protocol.value in ['wifi', 'api']:
                # WiFi and API devices need additional security checks
                if not device_info.endpoints:
                    security_issues.append('No secure endpoints defined')
                    
            # Check for basic security capabilities
            if 'security' not in device_info.capabilities:
                security_issues.append('No security capabilities declared')
                
            if security_issues:
                return {
                    'passed': False,
                    'error': f'Security issues: {", ".join(security_issues)}'
                }
                
            return {
                'passed': True,
                'details': {
                    'protocol': device_info.protocol.value,
                    'security_capabilities': 'security' in device_info.capabilities
                }
            }
            
        except Exception as e:
            return {
                'passed': False,
                'error': f'Security verification failed: {str(e)}'
            }
            
    async def _verify_compatibility(self, device_info: DeviceInfo) -> Dict[str, Any]:
        """Verify device compatibility."""
        try:
            compatibility_issues = []
            
            # Check protocol compatibility
            supported_protocols = ['wifi', 'bluetooth', 'zigbee', 'zwave', 'matter', 'api']
            if device_info.protocol.value not in supported_protocols:
                compatibility_issues.append(f'Unsupported protocol: {device_info.protocol.value}')
                
            # Check manufacturer compatibility
            known_manufacturers = [
                'Philips', 'Google', 'Amazon', 'Apple', 'Samsung', 'Xiaomi',
                'Wyze', 'Tuya', 'IKEA', 'Sonos', 'Bose', 'Fitbit', 'Garmin',
                'Withings', 'August', 'Schlage', 'Kwikset', 'Yale', 'Ecobee', 'Honeywell'
            ]
            
            if device_info.manufacturer not in known_manufacturers:
                compatibility_issues.append(f'Unknown manufacturer: {device_info.manufacturer}')
                
            if compatibility_issues:
                return {
                    'passed': False,
                    'error': f'Compatibility issues: {", ".join(compatibility_issues)}'
                }
                
            return {
                'passed': True,
                'details': {
                    'protocol_supported': True,
                    'manufacturer_known': device_info.manufacturer in known_manufacturers
                }
            }
            
        except Exception as e:
            return {
                'passed': False,
                'error': f'Compatibility verification failed: {str(e)}'
            }
            
    def _is_valid_endpoint(self, endpoint: str) -> bool:
        """Check if endpoint format is valid."""
        try:
            # Check for basic URL format
            if endpoint.startswith(('http://', 'https://', 'bluetooth://', 'wifi://')):
                return True
                
            # Check for IP address format
            if ':' in endpoint and '.' in endpoint:
                return True
                
            return False
            
        except Exception:
            return False
            
    def get_verification_result(self, verification_id: str) -> Optional[Dict[str, Any]]:
        """Get verification result by ID."""
        return self._verification_results.get(verification_id)
        
    def get_all_verification_results(self) -> List[Dict[str, Any]]:
        """Get all verification results."""
        return [
            {
                'id': result['id'],
                'device_id': result['device_id'],
                'device_name': result['device_name'],
                'overall_status': result['overall_status'],
                'verification_time': result['verification_time'].isoformat(),
                'check_count': len(result['checks']),
                'error_count': len(result['errors']),
                'warning_count': len(result['warnings'])
            }
            for result in self._verification_results.values()
        ]
        
    def cleanup_old_results(self, max_age_hours: int = 24):
        """Clean up old verification results."""
        cutoff_time = datetime.utcnow().timestamp() - (max_age_hours * 3600)
        
        results_to_remove = []
        for verification_id, result in self._verification_results.items():
            if result['verification_time'].timestamp() < cutoff_time:
                results_to_remove.append(verification_id)
                
        for verification_id in results_to_remove:
            del self._verification_results[verification_id]
            
        if results_to_remove:
            logger.info(f"Cleaned up {len(results_to_remove)} old verification results")
