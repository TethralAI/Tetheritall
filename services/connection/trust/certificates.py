"""
Certificate Management
Handles digital certificates for device trust and authentication.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import hashlib
import secrets
import json
import base64

from ..agent import DeviceInfo

logger = logging.getLogger(__name__)


class Certificate:
    """Represents a digital certificate for device authentication."""
    
    def __init__(self, device_id: str, public_key: str, issuer: str = "Tethral"):
        self.device_id = device_id
        self.public_key = public_key
        self.issuer = issuer
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(days=365)  # 1 year validity
        self.certificate_id = self._generate_certificate_id()
        self.is_revoked = False
        self.revocation_reason = None
        
    def _generate_certificate_id(self) -> str:
        """Generate unique certificate ID."""
        data = f"{self.device_id}:{self.public_key}:{self.created_at.timestamp()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
        
    def is_valid(self) -> bool:
        """Check if certificate is valid."""
        return (
            not self.is_revoked and
            datetime.utcnow() < self.expires_at
        )
        
    def revoke(self, reason: str = "Unknown"):
        """Revoke the certificate."""
        self.is_revoked = True
        self.revocation_reason = reason
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert certificate to dictionary."""
        return {
            'certificate_id': self.certificate_id,
            'device_id': self.device_id,
            'public_key': self.public_key,
            'issuer': self.issuer,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'is_valid': self.is_valid(),
            'is_revoked': self.is_revoked,
            'revocation_reason': self.revocation_reason
        }


class CertificateAuthority:
    """Certificate Authority for managing device certificates."""
    
    def __init__(self):
        self._certificates: Dict[str, Certificate] = {}
        self._private_key = secrets.token_hex(32)  # CA private key
        self._public_key = hashlib.sha256(self._private_key.encode()).hexdigest()  # CA public key
        
    def issue_certificate(self, device_info: DeviceInfo) -> Certificate:
        """Issue a certificate for a device."""
        try:
            # Generate device public key (in real implementation, this would come from the device)
            device_public_key = self._generate_device_public_key(device_info)
            
            # Create certificate
            certificate = Certificate(
                device_id=device_info.device_id,
                public_key=device_public_key,
                issuer="Tethral CA"
            )
            
            # Store certificate
            self._certificates[certificate.certificate_id] = certificate
            
            logger.info(f"Issued certificate {certificate.certificate_id} for device {device_info.name}")
            return certificate
            
        except Exception as e:
            logger.error(f"Error issuing certificate for device {device_info.name}: {e}")
            raise
            
    def _generate_device_public_key(self, device_info: DeviceInfo) -> str:
        """Generate a public key for the device."""
        # In a real implementation, this would be the actual device public key
        # For now, generate a deterministic key based on device info
        data = f"{device_info.device_id}:{device_info.name}:{device_info.manufacturer}"
        return hashlib.sha256(data.encode()).hexdigest()
        
    def verify_certificate(self, certificate_id: str) -> bool:
        """Verify a certificate is valid."""
        certificate = self._certificates.get(certificate_id)
        if not certificate:
            return False
            
        return certificate.is_valid()
        
    def revoke_certificate(self, certificate_id: str, reason: str = "Security violation") -> bool:
        """Revoke a certificate."""
        certificate = self._certificates.get(certificate_id)
        if not certificate:
            return False
            
        certificate.revoke(reason)
        logger.info(f"Revoked certificate {certificate_id}: {reason}")
        return True
        
    def get_certificate(self, certificate_id: str) -> Optional[Certificate]:
        """Get certificate by ID."""
        return self._certificates.get(certificate_id)
        
    def get_device_certificates(self, device_id: str) -> List[Certificate]:
        """Get all certificates for a device."""
        return [
            cert for cert in self._certificates.values()
            if cert.device_id == device_id
        ]
        
    def get_valid_certificates(self) -> List[Certificate]:
        """Get all valid certificates."""
        return [cert for cert in self._certificates.values() if cert.is_valid()]
        
    def get_expired_certificates(self) -> List[Certificate]:
        """Get all expired certificates."""
        return [cert for cert in self._certificates.values() if not cert.is_valid()]
        
    def cleanup_expired_certificates(self):
        """Remove expired certificates."""
        expired_certificates = self.get_expired_certificates()
        
        for certificate in expired_certificates:
            del self._certificates[certificate.certificate_id]
            
        if expired_certificates:
            logger.info(f"Cleaned up {len(expired_certificates)} expired certificates")
            
    def get_ca_public_key(self) -> str:
        """Get CA public key."""
        return self._public_key


class CertificateManager:
    """Manages certificates for device trust."""
    
    def __init__(self):
        self._ca = CertificateAuthority()
        self._device_certificates: Dict[str, str] = {}  # device_id -> certificate_id
        
    async def issue_device_certificate(self, device_info: DeviceInfo) -> Dict[str, Any]:
        """Issue a certificate for a device."""
        try:
            certificate = self._ca.issue_certificate(device_info)
            self._device_certificates[device_info.device_id] = certificate.certificate_id
            
            return {
                'success': True,
                'certificate_id': certificate.certificate_id,
                'device_id': certificate.device_id,
                'issued_at': certificate.created_at.isoformat(),
                'expires_at': certificate.expires_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error issuing certificate: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    async def verify_device_certificate(self, device_id: str) -> bool:
        """Verify device certificate."""
        certificate_id = self._device_certificates.get(device_id)
        if not certificate_id:
            return False
            
        return self._ca.verify_certificate(certificate_id)
        
    async def revoke_device_certificate(self, device_id: str, reason: str = "Security violation") -> bool:
        """Revoke device certificate."""
        certificate_id = self._device_certificates.get(device_id)
        if not certificate_id:
            return False
            
        success = self._ca.revoke_certificate(certificate_id, reason)
        if success:
            del self._device_certificates[device_id]
            
        return success
        
    def get_device_certificate_info(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get certificate information for a device."""
        certificate_id = self._device_certificates.get(device_id)
        if not certificate_id:
            return None
            
        certificate = self._ca.get_certificate(certificate_id)
        if not certificate:
            return None
            
        return certificate.to_dict()
        
    def get_all_certificates(self) -> List[Dict[str, Any]]:
        """Get all certificates."""
        return [
            {
                'device_id': device_id,
                'certificate_id': cert_id,
                'certificate_info': self._ca.get_certificate(cert_id).to_dict() if self._ca.get_certificate(cert_id) else None
            }
            for device_id, cert_id in self._device_certificates.items()
        ]
        
    def get_ca_info(self) -> Dict[str, Any]:
        """Get CA information."""
        return {
            'public_key': self._ca.get_ca_public_key(),
            'total_certificates': len(self._ca._certificates),
            'valid_certificates': len(self._ca.get_valid_certificates()),
            'expired_certificates': len(self._ca.get_expired_certificates())
        }
        
    def cleanup_expired_certificates(self):
        """Clean up expired certificates."""
        self._ca.cleanup_expired_certificates()
        
        # Remove references to expired certificates
        expired_device_ids = []
        for device_id, cert_id in self._device_certificates.items():
            if not self._ca.verify_certificate(cert_id):
                expired_device_ids.append(device_id)
                
        for device_id in expired_device_ids:
            del self._device_certificates[device_id]
            
        if expired_device_ids:
            logger.info(f"Removed {len(expired_device_ids)} expired certificate references")
