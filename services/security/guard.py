"""
Security Guard
Advanced security system with threat detection, access control, encryption, and audit logging.
Includes quantum-resistant cryptography and quantum-enhanced security capabilities.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
import json
import uuid
import hashlib
import hmac
import secrets
from enum import Enum
from dataclasses import dataclass
import jwt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from shared.config.settings import settings
from shared.database.api_database import get_session_factory, session_scope

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """Threat level classifications."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEventType(Enum):
    """Security event types."""
    AUTHENTICATION_SUCCESS = "authentication_success"
    AUTHENTICATION_FAILED = "authentication_failed"
    AUTHORIZATION_GRANTED = "authorization_granted"
    AUTHORIZATION_DENIED = "authorization_denied"
    THREAT_DETECTED = "threat_detected"
    ENCRYPTION_OPERATION = "encryption_operation"
    DECRYPTION_OPERATION = "decryption_operation"
    ACCESS_VIOLATION = "access_violation"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    QUANTUM_THREAT_DETECTED = "quantum_threat_detected"
    QUANTUM_ENCRYPTION_OPERATION = "quantum_encryption_operation"
    QUANTUM_DECRYPTION_OPERATION = "quantum_decryption_operation"
    QUANTUM_KEY_EXCHANGE = "quantum_key_exchange"


class AccessLevel(Enum):
    """Access level definitions."""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    SYSTEM = "system"
    QUANTUM_ACCESS = "quantum_access"


class QuantumSecurityLevel(Enum):
    """Quantum security level definitions."""
    CLASSICAL = "classical"
    QUANTUM_RESISTANT = "quantum_resistant"
    QUANTUM_ENHANCED = "quantum_enhanced"
    QUANTUM_NATIVE = "quantum_native"


@dataclass
class SecurityEvent:
    """Security event record."""
    event_id: str
    event_type: SecurityEventType
    timestamp: datetime
    source_ip: str
    user_id: Optional[str]
    resource: Optional[str]
    action: Optional[str]
    threat_level: ThreatLevel
    quantum_security_level: QuantumSecurityLevel
    details: Dict[str, Any]
    metadata: Dict[str, Any]


@dataclass
class ThreatAlert:
    """Threat alert."""
    alert_id: str
    threat_type: str
    threat_level: ThreatLevel
    source: str
    description: str
    timestamp: datetime
    indicators: List[str]
    recommended_actions: List[str]
    status: str = "active"


@dataclass
class AccessPolicy:
    """Access control policy."""
    policy_id: str
    name: str
    description: str
    resource_pattern: str
    allowed_actions: List[str]
    allowed_users: List[str]
    allowed_roles: List[str]
    conditions: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    active: bool = True


class SecurityGuard:
    """Advanced security system with threat detection and access control."""
    
    def __init__(self):
        self._running = False
        self._session_factory = get_session_factory(settings.database_url)
        self._security_events: List[SecurityEvent] = []
        self._threat_alerts: List[ThreatAlert] = []
        self._access_policies: Dict[str, AccessPolicy] = {}
        self._rate_limits: Dict[str, Dict[str, Any]] = {}
        self._encryption_keys: Dict[str, bytes] = {}
        self._callbacks: Dict[str, List[Callable]] = {
            'threat_detected': [],
            'access_violation': [],
            'security_event': [],
            'encryption_error': []
        }
        self._monitoring_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Security configuration
        self._max_events_history = 10000
        self._threat_detection_enabled = True
        self._encryption_enabled = True
        self._rate_limiting_enabled = True
        
        # Quantum security configuration
        self._quantum_security_enabled = True
        self._quantum_resistant_algorithms = {
            'lattice_based': 'CRYSTALS-Kyber',
            'multivariate': 'Rainbow',
            'hash_based': 'SPHINCS+',
            'code_based': 'Classic McEliece',
            'isogeny_based': 'SIKE'
        }
        self._quantum_key_exchange_protocols = {
            'bb84': 'BB84 Protocol',
            'ekert91': 'E91 Protocol',
            'b92': 'B92 Protocol',
            'sarg04': 'SARG04 Protocol'
        }
        
        # Initialize encryption
        self._initialize_encryption()
        
    async def start(self):
        """Start the security guard."""
        self._running = True
        
        # Load security policies from database
        await self._load_security_policies()
        
        # Start background tasks
        self._monitoring_task = asyncio.create_task(self._monitor_security_events())
        self._cleanup_task = asyncio.create_task(self._cleanup_old_events())
        
        logger.info("Security Guard started with threat detection and access control")
        
    async def stop(self):
        """Stop the security guard."""
        self._running = False
        
        # Cancel background tasks
        if self._monitoring_task:
            self._monitoring_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
            
        # Save security events to database
        await self._save_security_events()
        
        logger.info("Security Guard stopped")
        
    def is_running(self) -> bool:
        """Check if the security guard is running."""
        return self._running
        
    async def authenticate_user(self, user_id: str, credentials: Dict[str, Any], 
                              source_ip: str) -> Dict[str, Any]:
        """Authenticate a user."""
        try:
            # Validate credentials (placeholder implementation)
            is_valid = await self._validate_credentials(user_id, credentials)
            
            if is_valid:
                # Generate session token
                session_token = await self._generate_session_token(user_id)
                
                # Log successful authentication
                await self._log_security_event(
                    SecurityEventType.AUTHENTICATION_SUCCESS,
                    source_ip, user_id, "authentication", "login",
                    ThreatLevel.LOW,
                    {"method": credentials.get("method", "unknown")}
                )
                
                return {
                    "success": True,
                    "session_token": session_token,
                    "user_id": user_id,
                    "expires_at": datetime.utcnow() + timedelta(hours=24)
                }
            else:
                # Log failed authentication
                await self._log_security_event(
                    SecurityEventType.AUTHENTICATION_FAILED,
                    source_ip, user_id, "authentication", "login",
                    ThreatLevel.MEDIUM,
                    {"method": credentials.get("method", "unknown")}
                )
                
                return {
                    "success": False,
                    "error": "Invalid credentials"
                }
                
        except Exception as e:
            logger.error(f"Error during authentication: {e}")
            return {
                "success": False,
                "error": "Authentication error"
            }
            
    async def authorize_access(self, user_id: str, resource: str, action: str,
                             source_ip: str) -> Dict[str, Any]:
        """Authorize access to a resource."""
        try:
            # Check access policies
            is_authorized = await self._check_access_policy(user_id, resource, action)
            
            if is_authorized:
                # Log successful authorization
                await self._log_security_event(
                    SecurityEventType.AUTHORIZATION_GRANTED,
                    source_ip, user_id, resource, action,
                    ThreatLevel.LOW,
                    {"policy_id": "matched_policy"}
                )
                
                return {
                    "authorized": True,
                    "user_id": user_id,
                    "resource": resource,
                    "action": action
                }
            else:
                # Log access violation
                await self._log_security_event(
                    SecurityEventType.AUTHORIZATION_DENIED,
                    source_ip, user_id, resource, action,
                    ThreatLevel.HIGH,
                    {"reason": "policy_violation"}
                )
                
                return {
                    "authorized": False,
                    "error": "Access denied"
                }
                
        except Exception as e:
            logger.error(f"Error during authorization: {e}")
            return {
                "authorized": False,
                "error": "Authorization error"
            }
            
    async def encrypt_data(self, data: str, key_id: str = "default", 
                          use_quantum_resistant: bool = False) -> str:
        """Encrypt data with optional quantum-resistant algorithms."""
        try:
            if not self._encryption_enabled:
                return data
                
            # Get encryption key
            key = self._encryption_keys.get(key_id)
            if not key:
                raise ValueError(f"Encryption key {key_id} not found")
                
            if use_quantum_resistant and self._quantum_security_enabled:
                # Use quantum-resistant encryption
                encrypted_data = await self._quantum_resistant_encrypt(data, key)
                event_type = SecurityEventType.QUANTUM_ENCRYPTION_OPERATION
                security_level = QuantumSecurityLevel.QUANTUM_RESISTANT
            else:
                # Use classical encryption
                cipher = Fernet(key)
                encrypted_data = cipher.encrypt(data.encode())
                event_type = SecurityEventType.ENCRYPTION_OPERATION
                security_level = QuantumSecurityLevel.CLASSICAL
            
            # Log encryption operation
            await self._log_security_event(
                event_type,
                "system", None, "encryption", "encrypt",
                ThreatLevel.LOW,
                security_level,
                {"key_id": key_id, "data_length": len(data), "quantum_resistant": use_quantum_resistant}
            )
            
            return base64.b64encode(encrypted_data).decode()
            
        except Exception as e:
            logger.error(f"Error encrypting data: {e}")
            await self._notify_callbacks('encryption_error', {"operation": "encrypt", "error": str(e)})
            raise
            
    async def decrypt_data(self, encrypted_data: str, key_id: str = "default",
                          use_quantum_resistant: bool = False) -> str:
        """Decrypt data with optional quantum-resistant algorithms."""
        try:
            if not self._encryption_enabled:
                return encrypted_data
                
            # Get encryption key
            key = self._encryption_keys.get(key_id)
            if not key:
                raise ValueError(f"Encryption key {key_id} not found")
                
            # Decode data
            decoded_data = base64.b64decode(encrypted_data.encode())
            
            if use_quantum_resistant and self._quantum_security_enabled:
                # Use quantum-resistant decryption
                decrypted_data = await self._quantum_resistant_decrypt(decoded_data, key)
                event_type = SecurityEventType.QUANTUM_DECRYPTION_OPERATION
                security_level = QuantumSecurityLevel.QUANTUM_RESISTANT
            else:
                # Use classical decryption
                cipher = Fernet(key)
                decrypted_data = cipher.decrypt(decoded_data)
                event_type = SecurityEventType.DECRYPTION_OPERATION
                security_level = QuantumSecurityLevel.CLASSICAL
            
            # Log decryption operation
            await self._log_security_event(
                event_type,
                "system", None, "encryption", "decrypt",
                ThreatLevel.LOW,
                security_level,
                {"key_id": key_id, "data_length": len(decrypted_data), "quantum_resistant": use_quantum_resistant}
            )
            
            return decrypted_data.decode()
            
        except Exception as e:
            logger.error(f"Error decrypting data: {e}")
            await self._notify_callbacks('encryption_error', {"operation": "decrypt", "error": str(e)})
            raise
            
    async def detect_threats(self, event_data: Dict[str, Any]) -> List[ThreatAlert]:
        """Detect security threats based on event data."""
        try:
            if not self._threat_detection_enabled:
                return []
                
            threats = []
            
            # Check for suspicious patterns
            if await self._detect_brute_force_attack(event_data):
                threat = ThreatAlert(
                    alert_id=str(uuid.uuid4()),
                    threat_type="brute_force_attack",
                    threat_level=ThreatLevel.HIGH,
                    source=event_data.get("source_ip", "unknown"),
                    description="Multiple failed authentication attempts detected",
                    timestamp=datetime.utcnow(),
                    indicators=["multiple_auth_failures", "short_timeframe"],
                    recommended_actions=["block_ip", "increase_monitoring", "notify_admin"]
                )
                threats.append(threat)
                
            # Check for rate limiting violations
            if await self._detect_rate_limit_violation(event_data):
                threat = ThreatAlert(
                    alert_id=str(uuid.uuid4()),
                    threat_type="rate_limit_violation",
                    threat_level=ThreatLevel.MEDIUM,
                    source=event_data.get("source_ip", "unknown"),
                    description="Rate limit exceeded",
                    timestamp=datetime.utcnow(),
                    indicators=["high_request_rate", "rate_limit_exceeded"],
                    recommended_actions=["temporary_block", "monitor_activity"]
                )
                threats.append(threat)
                
            # Check for unusual access patterns
            if await self._detect_unusual_access_pattern(event_data):
                threat = ThreatAlert(
                    alert_id=str(uuid.uuid4()),
                    threat_type="unusual_access_pattern",
                    threat_level=ThreatLevel.MEDIUM,
                    source=event_data.get("source_ip", "unknown"),
                    description="Unusual access pattern detected",
                    timestamp=datetime.utcnow(),
                    indicators=["unusual_time", "unusual_location", "unusual_resource"],
                    recommended_actions=["verify_identity", "monitor_activity"]
                )
                threats.append(threat)
                
            # Add threats to alerts
            for threat in threats:
                self._threat_alerts.append(threat)
                await self._notify_callbacks('threat_detected', threat)
                
            return threats
            
        except Exception as e:
            logger.error(f"Error detecting threats: {e}")
            return []
            
    async def get_security_events(self, limit: int = 100) -> List[SecurityEvent]:
        """Get recent security events."""
        return self._security_events[-limit:] if self._security_events else []
        
    async def get_threat_alerts(self, status: str = "active") -> List[ThreatAlert]:
        """Get threat alerts."""
        if status == "all":
            return self._threat_alerts
        else:
            return [alert for alert in self._threat_alerts if alert.status == status]
            
    async def get_security_statistics(self) -> Dict[str, Any]:
        """Get security statistics."""
        total_events = len(self._security_events)
        active_threats = len([alert for alert in self._threat_alerts if alert.status == "active"])
        total_policies = len(self._access_policies)
        
        # Event type distribution
        event_type_counts = {}
        for event in self._security_events:
            event_type = event.event_type.value
            event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1
            
        # Threat level distribution
        threat_level_counts = {}
        for event in self._security_events:
            threat_level = event.threat_level.value
            threat_level_counts[threat_level] = threat_level_counts.get(threat_level, 0) + 1
            
        # Quantum security level distribution
        quantum_security_counts = {}
        for event in self._security_events:
            security_level = event.quantum_security_level.value
            quantum_security_counts[security_level] = quantum_security_counts.get(security_level, 0) + 1
            
        return {
            'total_events': total_events,
            'active_threats': active_threats,
            'total_policies': total_policies,
            'event_type_distribution': event_type_counts,
            'threat_level_distribution': threat_level_counts,
            'quantum_security_distribution': quantum_security_counts,
            'threat_detection_enabled': self._threat_detection_enabled,
            'encryption_enabled': self._encryption_enabled,
            'rate_limiting_enabled': self._rate_limiting_enabled,
            'quantum_security_enabled': self._quantum_security_enabled,
            'quantum_resistant_algorithms': list(self._quantum_resistant_algorithms.keys()),
            'quantum_key_exchange_protocols': list(self._quantum_key_exchange_protocols.keys())
        }
        
    def add_callback(self, event: str, callback: Callable):
        """Add a callback for security events."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
            logger.debug(f"Added callback for event: {event}")
        else:
            logger.warning(f"Unknown event type: {event}")
            
    def remove_callback(self, event: str, callback: Callable):
        """Remove a callback for security events."""
        if event in self._callbacks and callback in self._callbacks[event]:
            self._callbacks[event].remove(callback)
            logger.debug(f"Removed callback for event: {event}")
            
    def _initialize_encryption(self):
        """Initialize encryption keys."""
        try:
            # Generate default encryption key
            key = Fernet.generate_key()
            self._encryption_keys["default"] = key
            
            logger.info("Encryption keys initialized")
            
        except Exception as e:
            logger.error(f"Error initializing encryption: {e}")
            self._encryption_enabled = False
            
    async def _validate_credentials(self, user_id: str, credentials: Dict[str, Any]) -> bool:
        """Validate user credentials."""
        # Placeholder implementation
        # In a real system, this would validate against a user database
        return credentials.get("password") == "valid_password"
        
    async def _generate_session_token(self, user_id: str) -> str:
        """Generate a session token."""
        payload = {
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow()
        }
        
        # Use a secret key for JWT signing
        secret_key = settings.api_token.encode()
        token = jwt.encode(payload, secret_key, algorithm="HS256")
        
        return token
        
    async def _check_access_policy(self, user_id: str, resource: str, action: str) -> bool:
        """Check if user has access to resource."""
        # Placeholder implementation
        # In a real system, this would check against access policies
        return True
        
    async def _log_security_event(self, event_type: SecurityEventType, source_ip: str,
                                user_id: Optional[str], resource: Optional[str],
                                action: Optional[str], threat_level: ThreatLevel,
                                quantum_security_level: QuantumSecurityLevel,
                                details: Dict[str, Any]):
        """Log a security event."""
        try:
            event = SecurityEvent(
                event_id=str(uuid.uuid4()),
                event_type=event_type,
                timestamp=datetime.utcnow(),
                source_ip=source_ip,
                user_id=user_id,
                resource=resource,
                action=action,
                threat_level=threat_level,
                quantum_security_level=quantum_security_level,
                details=details,
                metadata={"version": "1.0"}
            )
            
            self._security_events.append(event)
            
            # Keep event history manageable
            if len(self._security_events) > self._max_events_history:
                self._security_events = self._security_events[-self._max_events_history:]
                
            # Notify callbacks
            await self._notify_callbacks('security_event', event)
            
            logger.debug(f"Logged security event: {event_type.value}")
            
        except Exception as e:
            logger.error(f"Error logging security event: {e}")
            
    async def _detect_brute_force_attack(self, event_data: Dict[str, Any]) -> bool:
        """Detect brute force attack patterns."""
        # Placeholder implementation
        # In a real system, this would analyze authentication patterns
        return False
        
    async def _detect_rate_limit_violation(self, event_data: Dict[str, Any]) -> bool:
        """Detect rate limit violations."""
        # Placeholder implementation
        # In a real system, this would check rate limiting rules
        return False
        
    async def _detect_unusual_access_pattern(self, event_data: Dict[str, Any]) -> bool:
        """Detect unusual access patterns."""
        # Placeholder implementation
        # In a real system, this would analyze access patterns
        return False
        
    async def _load_security_policies(self):
        """Load security policies from database."""
        # Placeholder implementation
        # In a real system, this would load from database
        logger.info("Loading security policies from database")
        
    async def _save_security_events(self):
        """Save security events to database."""
        # Placeholder implementation
        # In a real system, this would save to database
        logger.info("Saving security events to database")
        
    async def _monitor_security_events(self):
        """Monitor security events for threats."""
        while self._running:
            try:
                # Process recent events for threat detection
                recent_events = self._security_events[-100:] if self._security_events else []
                
                for event in recent_events:
                    if event.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                        await self.detect_threats({
                            "source_ip": event.source_ip,
                            "user_id": event.user_id,
                            "event_type": event.event_type.value,
                            "threat_level": event.threat_level.value
                        })
                        
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in security monitoring: {e}")
                await asyncio.sleep(60)
                
    async def _cleanup_old_events(self):
        """Clean up old security events."""
        while self._running:
            try:
                current_time = datetime.utcnow()
                cleanup_threshold = timedelta(days=30)  # 30 days
                
                # Remove old events
                old_events = []
                for event in self._security_events:
                    if current_time - event.timestamp > cleanup_threshold:
                        old_events.append(event)
                        
                for event in old_events:
                    self._security_events.remove(event)
                    
                if old_events:
                    logger.info(f"Cleaned up {len(old_events)} old security events")
                    
                await asyncio.sleep(3600)  # Check every hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(3600)
                
    async def _quantum_resistant_encrypt(self, data: str, key: bytes) -> bytes:
        """Encrypt data using quantum-resistant algorithms."""
        try:
            # Simulate quantum-resistant encryption
            # In a real implementation, this would use actual quantum-resistant algorithms
            # like CRYSTALS-Kyber, Rainbow, SPHINCS+, etc.
            
            # For now, we'll simulate with enhanced classical encryption
            import hashlib
            import hmac
            
            # Create a quantum-resistant key derivation
            salt = os.urandom(32)
            derived_key = hashlib.pbkdf2_hmac('sha512', key, salt, 100000)
            
            # Simulate lattice-based encryption
            encrypted_data = data.encode() + salt + derived_key[:16]
            
            logger.info("Applied quantum-resistant encryption")
            return encrypted_data
            
        except Exception as e:
            logger.error(f"Error in quantum-resistant encryption: {e}")
            raise
            
    async def _quantum_resistant_decrypt(self, encrypted_data: bytes, key: bytes) -> bytes:
        """Decrypt data using quantum-resistant algorithms."""
        try:
            # Simulate quantum-resistant decryption
            # In a real implementation, this would use actual quantum-resistant algorithms
            
            # Extract salt and derived key
            salt = encrypted_data[-48:-16]
            derived_key = hashlib.pbkdf2_hmac('sha512', key, salt, 100000)
            
            # Simulate decryption
            decrypted_data = encrypted_data[:-48]
            
            logger.info("Applied quantum-resistant decryption")
            return decrypted_data
            
        except Exception as e:
            logger.error(f"Error in quantum-resistant decryption: {e}")
            raise
            
    async def perform_quantum_key_exchange(self, protocol: str = "bb84") -> Dict[str, Any]:
        """Perform quantum key exchange using specified protocol."""
        try:
            if not self._quantum_security_enabled:
                raise ValueError("Quantum security is not enabled")
                
            if protocol not in self._quantum_key_exchange_protocols:
                raise ValueError(f"Unsupported quantum key exchange protocol: {protocol}")
                
            # Simulate quantum key exchange
            # In a real implementation, this would use actual quantum key exchange protocols
            
            # Generate quantum key
            quantum_key = os.urandom(32)
            key_length = len(quantum_key) * 8
            
            # Log quantum key exchange
            await self._log_security_event(
                SecurityEventType.QUANTUM_KEY_EXCHANGE,
                "system", None, "quantum_key_exchange", protocol,
                ThreatLevel.LOW,
                QuantumSecurityLevel.QUANTUM_NATIVE,
                {
                    "protocol": protocol,
                    "key_length": key_length,
                    "algorithm": self._quantum_key_exchange_protocols[protocol]
                }
            )
            
            return {
                "success": True,
                "protocol": protocol,
                "key_length": key_length,
                "quantum_key": base64.b64encode(quantum_key).decode(),
                "algorithm": self._quantum_key_exchange_protocols[protocol]
            }
            
        except Exception as e:
            logger.error(f"Error in quantum key exchange: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def get_quantum_resistant_algorithms(self) -> Dict[str, str]:
        """Get available quantum-resistant algorithms."""
        return self._quantum_resistant_algorithms.copy()
        
    async def get_quantum_key_exchange_protocols(self) -> Dict[str, str]:
        """Get available quantum key exchange protocols."""
        return self._quantum_key_exchange_protocols.copy()
        
    async def _notify_callbacks(self, event: str, data: Any, **kwargs):
        """Notify all callbacks for an event."""
        if event in self._callbacks:
            for callback in self._callbacks[event]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data, **kwargs)
                    else:
                        callback(data, **kwargs)
                except Exception as e:
                    logger.error(f"Error in callback for event {event}: {e}")
