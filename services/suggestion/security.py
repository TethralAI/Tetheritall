"""
Security and Privacy Service for the Suggestion Engine

Provides comprehensive security features including data encryption, access control,
privacy compliance, audit logging, and data anonymization for the Tethral Suggestion Engine.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

logger = logging.getLogger(__name__)


class PrivacyLevel(Enum):
    PUBLIC = "public"
    PERSONAL = "personal"
    SENSITIVE = "sensitive"
    CONFIDENTIAL = "confidential"


class AccessLevel(Enum):
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    OWNER = "owner"


class DataRetentionPolicy(Enum):
    IMMEDIATE = "immediate"
    DAYS_7 = "7_days"
    DAYS_30 = "30_days"
    DAYS_90 = "90_days"
    DAYS_365 = "365_days"
    PERMANENT = "permanent"


@dataclass
class SecurityContext:
    user_id: str
    session_id: str
    access_level: AccessLevel
    permissions: List[str] = field(default_factory=list)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PrivacySettings:
    user_id: str
    data_retention_policy: DataRetentionPolicy = DataRetentionPolicy.DAYS_90
    allow_analytics: bool = True
    allow_personalization: bool = True
    allow_third_party_sharing: bool = False
    encryption_level: str = "standard"
    anonymization_enabled: bool = False
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AuditLogEntry:
    timestamp: datetime
    user_id: str
    action: str
    resource: str
    result: str
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    session_id: Optional[str] = None


class SecurityService:
    """
    Comprehensive security service for the Suggestion Engine.
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        # Initialize encryption
        if encryption_key:
            self.encryption_key = encryption_key.encode()
        else:
            self.encryption_key = Fernet.generate_key()
        
        self.cipher_suite = Fernet(self.encryption_key)
        
        # Security settings
        self.max_failed_attempts = 5
        self.lockout_duration = timedelta(minutes=15)
        self.session_timeout = timedelta(hours=24)
        
        # Internal state
        self._failed_attempts: Dict[str, List[datetime]] = {}
        self._active_sessions: Dict[str, SecurityContext] = {}
        self._audit_log: List[AuditLogEntry] = []
        self._privacy_settings: Dict[str, PrivacySettings] = {}
        
    async def start(self):
        """Initialize the security service."""
        logger.info("Security service started")
        
    async def stop(self):
        """Cleanup the security service."""
        logger.info("Security service stopped")
    
    def encrypt_data(self, data: Union[str, bytes, Dict[str, Any]]) -> str:
        """Encrypt sensitive data."""
        try:
            if isinstance(data, dict):
                data = json.dumps(data)
            if isinstance(data, str):
                data = data.encode()
            
            encrypted_data = self.cipher_suite.encrypt(data)
            return base64.b64encode(encrypted_data).decode()
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt_data(self, encrypted_data: str) -> Union[str, Dict[str, Any]]:
        """Decrypt sensitive data."""
        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            decrypted_data = self.cipher_suite.decrypt(encrypted_bytes)
            
            # Try to parse as JSON first, fallback to string
            try:
                return json.loads(decrypted_data.decode())
            except json.JSONDecodeError:
                return decrypted_data.decode()
                
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def hash_sensitive_data(self, data: str, salt: Optional[str] = None) -> str:
        """Hash sensitive data with salt."""
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Use PBKDF2 for secure hashing
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode(),
            iterations=100000,
        )
        key = base64.b64encode(kdf.derive(data.encode()))
        return f"{salt}:{key.decode()}"
    
    def verify_hash(self, data: str, hashed_data: str) -> bool:
        """Verify hashed data."""
        try:
            salt, key = hashed_data.split(":", 1)
            expected_hash = self.hash_sensitive_data(data, salt)
            return hmac.compare_digest(hashed_data, expected_hash)
        except Exception:
            return False
    
    def anonymize_data(self, data: Dict[str, Any], privacy_level: PrivacyLevel) -> Dict[str, Any]:
        """Anonymize data based on privacy level."""
        anonymized = data.copy()
        
        if privacy_level == PrivacyLevel.PUBLIC:
            # Remove all personal identifiers
            personal_fields = ['user_id', 'email', 'phone', 'address', 'name']
            for field in personal_fields:
                anonymized.pop(field, None)
        
        elif privacy_level == PrivacyLevel.PERSONAL:
            # Keep user_id but hash other personal data
            if 'email' in anonymized:
                anonymized['email'] = self.hash_sensitive_data(anonymized['email'])
            if 'phone' in anonymized:
                anonymized['phone'] = self.hash_sensitive_data(anonymized['phone'])
        
        elif privacy_level == PrivacyLevel.SENSITIVE:
            # Hash user_id and all personal data
            if 'user_id' in anonymized:
                anonymized['user_id'] = self.hash_sensitive_data(anonymized['user_id'])
            if 'email' in anonymized:
                anonymized['email'] = self.hash_sensitive_data(anonymized['email'])
            if 'phone' in anonymized:
                anonymized['phone'] = self.hash_sensitive_data(anonymized['phone'])
        
        elif privacy_level == PrivacyLevel.CONFIDENTIAL:
            # Encrypt all data
            for key, value in anonymized.items():
                if isinstance(value, (str, dict)):
                    anonymized[key] = self.encrypt_data(value)
        
        return anonymized
    
    async def create_session(
        self,
        user_id: str,
        access_level: AccessLevel,
        permissions: Optional[List[str]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> str:
        """Create a new security session."""
        try:
            # Check if user is locked out
            if await self._is_user_locked_out(user_id):
                raise ValueError("User account is temporarily locked")
            
            # Generate session ID
            session_id = secrets.token_urlsafe(32)
            
            # Create security context
            context = SecurityContext(
                user_id=user_id,
                session_id=session_id,
                access_level=access_level,
                permissions=permissions or [],
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Store session
            self._active_sessions[session_id] = context
            
            # Log session creation
            await self._log_audit_event(
                user_id=user_id,
                action="session_created",
                resource="session",
                result="success",
                details={"session_id": session_id, "access_level": access_level.value}
            )
            
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create session for user {user_id}: {e}")
            raise
    
    async def validate_session(self, session_id: str) -> Optional[SecurityContext]:
        """Validate a security session."""
        try:
            context = self._active_sessions.get(session_id)
            if not context:
                return None
            
            # Check session timeout
            if datetime.utcnow() - context.timestamp > self.session_timeout:
                await self.invalidate_session(session_id)
                return None
            
            # Update timestamp
            context.timestamp = datetime.utcnow()
            
            return context
            
        except Exception as e:
            logger.error(f"Session validation failed: {e}")
            return None
    
    async def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a security session."""
        try:
            if session_id in self._active_sessions:
                context = self._active_sessions[session_id]
                
                # Log session invalidation
                await self._log_audit_event(
                    user_id=context.user_id,
                    action="session_invalidated",
                    resource="session",
                    result="success",
                    details={"session_id": session_id}
                )
                
                del self._active_sessions[session_id]
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Session invalidation failed: {e}")
            return False
    
    async def check_permission(
        self,
        user_id: str,
        resource: str,
        action: str,
        session_id: Optional[str] = None
    ) -> bool:
        """Check if user has permission for a specific action."""
        try:
            # Get user context
            context = None
            if session_id:
                context = await self.validate_session(session_id)
            
            if not context or context.user_id != user_id:
                return False
            
            # Check access level
            if context.access_level == AccessLevel.OWNER:
                return True
            
            # Check specific permissions
            required_permission = f"{resource}:{action}"
            if required_permission in context.permissions:
                return True
            
            # Check admin access
            if context.access_level == AccessLevel.ADMIN:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Permission check failed: {e}")
            return False
    
    async def record_failed_attempt(self, user_id: str, action: str):
        """Record a failed authentication attempt."""
        try:
            if user_id not in self._failed_attempts:
                self._failed_attempts[user_id] = []
            
            self._failed_attempts[user_id].append(datetime.utcnow())
            
            # Clean up old attempts
            cutoff_time = datetime.utcnow() - self.lockout_duration
            self._failed_attempts[user_id] = [
                attempt for attempt in self._failed_attempts[user_id]
                if attempt > cutoff_time
            ]
            
            # Log failed attempt
            await self._log_audit_event(
                user_id=user_id,
                action=f"failed_{action}",
                resource="authentication",
                result="failure",
                details={"attempt_count": len(self._failed_attempts[user_id])}
            )
            
        except Exception as e:
            logger.error(f"Failed to record failed attempt: {e}")
    
    async def _is_user_locked_out(self, user_id: str) -> bool:
        """Check if user is locked out due to too many failed attempts."""
        if user_id not in self._failed_attempts:
            return False
        
        recent_attempts = len(self._failed_attempts[user_id])
        return recent_attempts >= self.max_failed_attempts
    
    async def get_privacy_settings(self, user_id: str) -> PrivacySettings:
        """Get privacy settings for a user."""
        if user_id not in self._privacy_settings:
            # Create default settings
            self._privacy_settings[user_id] = PrivacySettings(user_id=user_id)
        
        return self._privacy_settings[user_id]
    
    async def update_privacy_settings(self, user_id: str, settings: Dict[str, Any]) -> bool:
        """Update privacy settings for a user."""
        try:
            current_settings = await self.get_privacy_settings(user_id)
            
            # Update settings
            for key, value in settings.items():
                if hasattr(current_settings, key):
                    setattr(current_settings, key, value)
            
            current_settings.last_updated = datetime.utcnow()
            
            # Log privacy settings update
            await self._log_audit_event(
                user_id=user_id,
                action="privacy_settings_updated",
                resource="privacy",
                result="success",
                details=settings
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update privacy settings: {e}")
            return False
    
    async def _log_audit_event(
        self,
        user_id: str,
        action: str,
        resource: str,
        result: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log an audit event."""
        try:
            entry = AuditLogEntry(
                timestamp=datetime.utcnow(),
                user_id=user_id,
                action=action,
                resource=resource,
                result=result,
                details=details or {}
            )
            
            self._audit_log.append(entry)
            
            # Keep only recent audit logs (last 30 days)
            cutoff_time = datetime.utcnow() - timedelta(days=30)
            self._audit_log = [
                entry for entry in self._audit_log
                if entry.timestamp > cutoff_time
            ]
            
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
    
    async def get_audit_log(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLogEntry]:
        """Get audit log entries with optional filtering."""
        try:
            entries = self._audit_log
            
            if user_id:
                entries = [e for e in entries if e.user_id == user_id]
            
            if action:
                entries = [e for e in entries if e.action == action]
            
            if start_time:
                entries = [e for e in entries if e.timestamp >= start_time]
            
            if end_time:
                entries = [e for e in entries if e.timestamp <= end_time]
            
            # Sort by timestamp (newest first) and limit
            entries.sort(key=lambda e: e.timestamp, reverse=True)
            return entries[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get audit log: {e}")
            return []
    
    async def cleanup_expired_data(self):
        """Clean up expired data based on retention policies."""
        try:
            current_time = datetime.utcnow()
            
            # Clean up expired sessions
            expired_sessions = [
                session_id for session_id, context in self._active_sessions.items()
                if current_time - context.timestamp > self.session_timeout
            ]
            
            for session_id in expired_sessions:
                await self.invalidate_session(session_id)
            
            # Clean up failed attempts older than lockout duration
            for user_id in list(self._failed_attempts.keys()):
                cutoff_time = current_time - self.lockout_duration
                self._failed_attempts[user_id] = [
                    attempt for attempt in self._failed_attempts[user_id]
                    if attempt > cutoff_time
                ]
                
                if not self._failed_attempts[user_id]:
                    del self._failed_attempts[user_id]
            
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired data: {e}")
    
    def get_security_summary(self) -> Dict[str, Any]:
        """Get a summary of security status."""
        return {
            "active_sessions": len(self._active_sessions),
            "locked_users": len([uid for uid in self._failed_attempts if self._is_user_locked_out(uid)]),
            "audit_log_entries": len(self._audit_log),
            "privacy_settings_count": len(self._privacy_settings),
            "encryption_enabled": True,
            "session_timeout_seconds": self.session_timeout.total_seconds(),
            "max_failed_attempts": self.max_failed_attempts
        }


class PrivacyCompliance:
    """
    Privacy compliance utilities for GDPR, CCPA, and other regulations.
    """
    
    @staticmethod
    def generate_data_export(user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a data export for user privacy requests."""
        return {
            "export_timestamp": datetime.utcnow().isoformat(),
            "data_categories": {
                "personal_info": user_data.get("personal_info", {}),
                "preferences": user_data.get("preferences", {}),
                "activity_history": user_data.get("activity_history", []),
                "suggestions": user_data.get("suggestions", []),
                "feedback": user_data.get("feedback", [])
            },
            "metadata": {
                "format_version": "1.0",
                "compliance_standards": ["GDPR", "CCPA"]
            }
        }
    
    @staticmethod
    def anonymize_for_analytics(data: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize data for analytics while preserving utility."""
        anonymized = data.copy()
        
        # Remove direct identifiers
        direct_identifiers = ['user_id', 'email', 'phone', 'name', 'address']
        for identifier in direct_identifiers:
            anonymized.pop(identifier, None)
        
        # Hash quasi-identifiers
        quasi_identifiers = ['ip_address', 'user_agent']
        for identifier in quasi_identifiers:
            if identifier in anonymized:
                anonymized[identifier] = hashlib.sha256(
                    anonymized[identifier].encode()
                ).hexdigest()[:16]
        
        return anonymized
    
    @staticmethod
    def check_data_retention_compliance(
        data_timestamp: datetime,
        retention_policy: DataRetentionPolicy
    ) -> bool:
        """Check if data should be retained based on policy."""
        current_time = datetime.utcnow()
        
        if retention_policy == DataRetentionPolicy.IMMEDIATE:
            return False
        elif retention_policy == DataRetentionPolicy.DAYS_7:
            return current_time - data_timestamp <= timedelta(days=7)
        elif retention_policy == DataRetentionPolicy.DAYS_30:
            return current_time - data_timestamp <= timedelta(days=30)
        elif retention_policy == DataRetentionPolicy.DAYS_90:
            return current_time - data_timestamp <= timedelta(days=90)
        elif retention_policy == DataRetentionPolicy.DAYS_365:
            return current_time - data_timestamp <= timedelta(days=365)
        elif retention_policy == DataRetentionPolicy.PERMANENT:
            return True
        
        return False


# Global security service instance
_security_service: Optional[SecurityService] = None


def get_security_service() -> SecurityService:
    """Get the global security service instance."""
    global _security_service
    if _security_service is None:
        _security_service = SecurityService()
    return _security_service


async def initialize_security():
    """Initialize the global security service."""
    global _security_service
    _security_service = SecurityService()
    await _security_service.start()


async def cleanup_security():
    """Cleanup the global security service."""
    global _security_service
    if _security_service:
        await _security_service.stop()
