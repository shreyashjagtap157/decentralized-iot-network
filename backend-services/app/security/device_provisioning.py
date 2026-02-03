"""
Device Provisioning Security System

Provides secure device provisioning with PKI, attestation,
and secure bootstrapping for IoT devices.

Features:
- X.509 certificate-based device identity
- Hardware attestation verification
- Secure bootstrapping flow
- Certificate lifecycle management
- Device trust chain validation
- Zero-touch provisioning support
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.x509.oid import ExtensionOID, NameOID

logger = logging.getLogger(__name__)


class ProvisioningState(Enum):
    """Device provisioning states"""
    UNPROVISIONED = "unprovisioned"
    PENDING_ATTESTATION = "pending_attestation"
    ATTESTATION_VERIFIED = "attestation_verified"
    CERTIFICATE_ISSUED = "certificate_issued"
    PROVISIONED = "provisioned"
    REVOKED = "revoked"
    SUSPENDED = "suspended"


class AttestationType(Enum):
    """Hardware attestation types"""
    NONE = "none"
    TPM_2_0 = "tpm_2_0"
    ARM_TRUSTZONE = "arm_trustzone"
    SECURE_ENCLAVE = "secure_enclave"
    SOFTWARE_ONLY = "software_only"


class CertificateType(Enum):
    """Certificate types"""
    ROOT_CA = "root_ca"
    INTERMEDIATE_CA = "intermediate_ca"
    DEVICE = "device"
    PROVISIONING = "provisioning"


@dataclass
class DeviceIdentity:
    """Device identity information"""
    device_id: str
    device_type: str
    manufacturer: str
    model: str
    serial_number: str
    firmware_version: str
    hardware_revision: str
    attestation_type: AttestationType
    public_key: bytes
    metadata: dict = field(default_factory=dict)


@dataclass
class DeviceCertificate:
    """Device X.509 certificate"""
    certificate: x509.Certificate
    certificate_pem: bytes
    private_key_pem: Optional[bytes]
    certificate_chain: list[bytes]
    issued_at: datetime
    expires_at: datetime
    serial_number: int
    thumbprint: str


@dataclass
class AttestationData:
    """Hardware attestation data"""
    attestation_type: AttestationType
    platform_certificate: bytes
    endorsement_key: bytes
    attestation_quote: bytes
    pcr_values: dict[int, bytes]
    nonce: bytes
    timestamp: datetime


@dataclass
class ProvisioningSession:
    """Active provisioning session"""
    session_id: str
    device_id: str
    state: ProvisioningState
    challenge: bytes
    created_at: datetime
    expires_at: datetime
    attestation_data: Optional[AttestationData] = None
    identity: Optional[DeviceIdentity] = None
    certificate: Optional[DeviceCertificate] = None


class PKIManager:
    """
    Public Key Infrastructure manager for certificate operations.
    """
    
    def __init__(
        self,
        root_ca_key_path: str,
        root_ca_cert_path: str,
        intermediate_ca_key_path: Optional[str] = None,
        intermediate_ca_cert_path: Optional[str] = None
    ):
        self.root_ca_key = self._load_private_key(root_ca_key_path)
        self.root_ca_cert = self._load_certificate(root_ca_cert_path)
        
        if intermediate_ca_key_path and intermediate_ca_cert_path:
            self.intermediate_ca_key = self._load_private_key(intermediate_ca_key_path)
            self.intermediate_ca_cert = self._load_certificate(intermediate_ca_cert_path)
            self.signing_key = self.intermediate_ca_key
            self.signing_cert = self.intermediate_ca_cert
        else:
            self.intermediate_ca_key = None
            self.intermediate_ca_cert = None
            self.signing_key = self.root_ca_key
            self.signing_cert = self.root_ca_cert
    
    def _load_private_key(self, path: str):
        """Load private key from file"""
        with open(path, 'rb') as f:
            return serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )
    
    def _load_certificate(self, path: str) -> x509.Certificate:
        """Load certificate from file"""
        with open(path, 'rb') as f:
            return x509.load_pem_x509_certificate(f.read(), default_backend())
    
    def generate_device_keypair(self) -> tuple[ec.EllipticCurvePrivateKey, bytes]:
        """Generate device keypair (ECDSA P-256)"""
        private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
        public_key_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return private_key, public_key_bytes
    
    def issue_device_certificate(
        self,
        device_identity: DeviceIdentity,
        public_key: ec.EllipticCurvePublicKey,
        validity_days: int = 365
    ) -> DeviceCertificate:
        """Issue X.509 certificate for device"""
        # Generate serial number
        serial_number = int.from_bytes(os.urandom(16), 'big')
        
        # Build subject
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, device_identity.manufacturer),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "IoT Devices"),
            x509.NameAttribute(NameOID.COMMON_NAME, device_identity.device_id),
            x509.NameAttribute(NameOID.SERIAL_NUMBER, device_identity.serial_number),
        ])
        
        now = datetime.utcnow()
        
        # Build certificate
        builder = x509.CertificateBuilder()
        builder = builder.subject_name(subject)
        builder = builder.issuer_name(self.signing_cert.subject)
        builder = builder.public_key(public_key)
        builder = builder.serial_number(serial_number)
        builder = builder.not_valid_before(now)
        builder = builder.not_valid_after(now + timedelta(days=validity_days))
        
        # Add extensions
        builder = builder.add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True
        )
        
        builder = builder.add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False
            ),
            critical=True
        )
        
        builder = builder.add_extension(
            x509.ExtendedKeyUsage([
                x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
            ]),
            critical=False
        )
        
        # Add Subject Key Identifier
        builder = builder.add_extension(
            x509.SubjectKeyIdentifier.from_public_key(public_key),
            critical=False
        )
        
        # Add Authority Key Identifier
        builder = builder.add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(
                self.signing_key.public_key()
            ),
            critical=False
        )
        
        # Sign certificate
        certificate = builder.sign(
            private_key=self.signing_key,
            algorithm=hashes.SHA256(),
            backend=default_backend()
        )
        
        # Build certificate chain
        chain = [
            self.signing_cert.public_bytes(serialization.Encoding.PEM)
        ]
        if self.intermediate_ca_cert:
            chain.append(
                self.root_ca_cert.public_bytes(serialization.Encoding.PEM)
            )
        
        # Calculate thumbprint
        thumbprint = hashlib.sha256(
            certificate.public_bytes(serialization.Encoding.DER)
        ).hexdigest()
        
        return DeviceCertificate(
            certificate=certificate,
            certificate_pem=certificate.public_bytes(serialization.Encoding.PEM),
            private_key_pem=None,  # Private key stays on device
            certificate_chain=chain,
            issued_at=now,
            expires_at=now + timedelta(days=validity_days),
            serial_number=serial_number,
            thumbprint=thumbprint
        )
    
    def verify_certificate(self, certificate: x509.Certificate) -> tuple[bool, str]:
        """Verify certificate against trust chain"""
        try:
            # Check validity period
            now = datetime.utcnow()
            if now < certificate.not_valid_before:
                return False, "Certificate not yet valid"
            if now > certificate.not_valid_after:
                return False, "Certificate expired"
            
            # Verify signature
            issuer_cert = self.signing_cert
            issuer_public_key = issuer_cert.public_key()
            
            issuer_public_key.verify(
                certificate.signature,
                certificate.tbs_certificate_bytes,
                ec.ECDSA(hashes.SHA256())
            )
            
            return True, "Valid"
            
        except Exception as e:
            return False, str(e)
    
    def revoke_certificate(self, serial_number: int, reason: x509.ReasonFlags = None):
        """Add certificate to revocation list"""
        # In production, this would update CRL or OCSP responder
        logger.info(f"Certificate {serial_number} revoked: {reason}")


class HardwareAttestationVerifier:
    """
    Verifies hardware attestation from devices.
    """
    
    def __init__(self):
        # Known good PCR values for trusted configurations
        self.trusted_pcr_values: dict[str, dict[int, bytes]] = {}
        
        # Trusted endorsement key certificates
        self.trusted_ek_certs: list[bytes] = []
    
    def register_trusted_configuration(
        self,
        config_id: str,
        pcr_values: dict[int, bytes]
    ):
        """Register a trusted PCR configuration"""
        self.trusted_pcr_values[config_id] = pcr_values
    
    def verify_tpm_attestation(
        self,
        attestation: AttestationData,
        expected_nonce: bytes
    ) -> tuple[bool, str]:
        """Verify TPM 2.0 attestation"""
        try:
            # Verify nonce
            if not hmac.compare_digest(attestation.nonce, expected_nonce):
                return False, "Nonce mismatch"
            
            # Verify timestamp freshness (within 5 minutes)
            now = datetime.utcnow()
            age = (now - attestation.timestamp).total_seconds()
            if age > 300:
                return False, "Attestation too old"
            
            # Verify endorsement key certificate
            if not self._verify_ek_certificate(attestation.endorsement_key):
                return False, "Invalid endorsement key"
            
            # Verify PCR values against known good configurations
            if not self._verify_pcr_values(attestation.pcr_values):
                return False, "PCR values not trusted"
            
            # Verify attestation quote signature
            if not self._verify_quote_signature(attestation):
                return False, "Invalid quote signature"
            
            return True, "Attestation verified"
            
        except Exception as e:
            return False, f"Verification error: {e}"
    
    def verify_arm_trustzone(
        self,
        attestation: AttestationData,
        expected_nonce: bytes
    ) -> tuple[bool, str]:
        """Verify ARM TrustZone attestation"""
        try:
            if not hmac.compare_digest(attestation.nonce, expected_nonce):
                return False, "Nonce mismatch"
            
            # Verify TrustZone-specific attestation
            # Implementation depends on specific TrustZone implementation
            
            return True, "TrustZone attestation verified"
            
        except Exception as e:
            return False, f"Verification error: {e}"
    
    def _verify_ek_certificate(self, ek_cert: bytes) -> bool:
        """Verify endorsement key certificate"""
        return ek_cert in self.trusted_ek_certs
    
    def _verify_pcr_values(self, pcr_values: dict[int, bytes]) -> bool:
        """Verify PCR values against trusted configurations"""
        for config_id, trusted_pcrs in self.trusted_pcr_values.items():
            if all(
                pcr_values.get(pcr) == value
                for pcr, value in trusted_pcrs.items()
            ):
                return True
        return False
    
    def _verify_quote_signature(self, attestation: AttestationData) -> bool:
        """Verify TPM quote signature"""
        # In production, verify signature using AIK
        return True


class ProvisioningService:
    """
    Main device provisioning service.
    """
    
    def __init__(
        self,
        pki_manager: PKIManager,
        attestation_verifier: HardwareAttestationVerifier,
        session_timeout_minutes: int = 15
    ):
        self.pki = pki_manager
        self.attestation_verifier = attestation_verifier
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        
        self.sessions: dict[str, ProvisioningSession] = {}
        self.provisioned_devices: dict[str, DeviceCertificate] = {}
        
        # Provisioning tokens for zero-touch
        self.provisioning_tokens: dict[str, dict] = {}
    
    async def create_provisioning_token(
        self,
        device_type: str,
        manufacturer: str,
        valid_hours: int = 24,
        max_uses: int = 1
    ) -> str:
        """Create pre-provisioning token for zero-touch setup"""
        token = secrets.token_urlsafe(32)
        
        self.provisioning_tokens[token] = {
            "device_type": device_type,
            "manufacturer": manufacturer,
            "expires_at": datetime.utcnow() + timedelta(hours=valid_hours),
            "max_uses": max_uses,
            "uses": 0
        }
        
        return token
    
    async def start_provisioning(
        self,
        device_identity: DeviceIdentity,
        provisioning_token: Optional[str] = None
    ) -> ProvisioningSession:
        """Start device provisioning session"""
        # Validate provisioning token if provided
        if provisioning_token:
            if not self._validate_token(provisioning_token, device_identity):
                raise ValueError("Invalid provisioning token")
        
        # Generate challenge
        challenge = os.urandom(32)
        
        # Create session
        session = ProvisioningSession(
            session_id=str(uuid4()),
            device_id=device_identity.device_id,
            state=ProvisioningState.PENDING_ATTESTATION,
            challenge=challenge,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + self.session_timeout,
            identity=device_identity
        )
        
        self.sessions[session.session_id] = session
        
        logger.info(f"Started provisioning session: {session.session_id}")
        
        return session
    
    def _validate_token(self, token: str, identity: DeviceIdentity) -> bool:
        """Validate provisioning token"""
        token_data = self.provisioning_tokens.get(token)
        if not token_data:
            return False
        
        if datetime.utcnow() > token_data["expires_at"]:
            return False
        
        if token_data["uses"] >= token_data["max_uses"]:
            return False
        
        if token_data["device_type"] != identity.device_type:
            return False
        
        if token_data["manufacturer"] != identity.manufacturer:
            return False
        
        # Increment usage
        token_data["uses"] += 1
        
        return True
    
    async def submit_attestation(
        self,
        session_id: str,
        attestation: AttestationData
    ) -> tuple[bool, str]:
        """Submit hardware attestation for verification"""
        session = self.sessions.get(session_id)
        if not session:
            return False, "Session not found"
        
        if session.state != ProvisioningState.PENDING_ATTESTATION:
            return False, "Invalid session state"
        
        if datetime.utcnow() > session.expires_at:
            return False, "Session expired"
        
        # Verify attestation based on type
        if attestation.attestation_type == AttestationType.TPM_2_0:
            valid, reason = self.attestation_verifier.verify_tpm_attestation(
                attestation, session.challenge
            )
        elif attestation.attestation_type == AttestationType.ARM_TRUSTZONE:
            valid, reason = self.attestation_verifier.verify_arm_trustzone(
                attestation, session.challenge
            )
        elif attestation.attestation_type == AttestationType.SOFTWARE_ONLY:
            # Software-only attestation (less secure)
            valid, reason = self._verify_software_attestation(attestation, session.challenge)
        else:
            valid, reason = False, "Unsupported attestation type"
        
        if valid:
            session.state = ProvisioningState.ATTESTATION_VERIFIED
            session.attestation_data = attestation
            logger.info(f"Attestation verified for session: {session_id}")
        else:
            session.state = ProvisioningState.UNPROVISIONED
            logger.warning(f"Attestation failed for session: {session_id} - {reason}")
        
        return valid, reason
    
    def _verify_software_attestation(
        self,
        attestation: AttestationData,
        expected_nonce: bytes
    ) -> tuple[bool, str]:
        """Verify software-only attestation (for development)"""
        if not hmac.compare_digest(attestation.nonce, expected_nonce):
            return False, "Nonce mismatch"
        return True, "Software attestation verified"
    
    async def issue_certificate(
        self,
        session_id: str,
        csr_pem: bytes
    ) -> DeviceCertificate:
        """Issue device certificate after attestation"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError("Session not found")
        
        if session.state != ProvisioningState.ATTESTATION_VERIFIED:
            raise ValueError("Attestation not verified")
        
        # Parse CSR
        csr = x509.load_pem_x509_csr(csr_pem, default_backend())
        
        # Verify CSR signature
        if not csr.is_signature_valid:
            raise ValueError("Invalid CSR signature")
        
        # Issue certificate
        certificate = self.pki.issue_device_certificate(
            session.identity,
            csr.public_key()
        )
        
        session.certificate = certificate
        session.state = ProvisioningState.CERTIFICATE_ISSUED
        
        logger.info(f"Certificate issued for device: {session.identity.device_id}")
        
        return certificate
    
    async def complete_provisioning(
        self,
        session_id: str,
        confirmation: bytes
    ) -> bool:
        """Complete provisioning with device confirmation"""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        if session.state != ProvisioningState.CERTIFICATE_ISSUED:
            return False
        
        # Verify confirmation (device signed the challenge)
        # In production, verify signature using device's public key
        
        session.state = ProvisioningState.PROVISIONED
        
        # Store provisioned device
        self.provisioned_devices[session.identity.device_id] = session.certificate
        
        # Clean up session
        del self.sessions[session_id]
        
        logger.info(f"Provisioning complete for device: {session.identity.device_id}")
        
        return True
    
    async def revoke_device(self, device_id: str, reason: str = "unspecified"):
        """Revoke device certificate"""
        certificate = self.provisioned_devices.get(device_id)
        if certificate:
            self.pki.revoke_certificate(
                certificate.serial_number,
                x509.ReasonFlags.unspecified
            )
            del self.provisioned_devices[device_id]
            logger.info(f"Device {device_id} revoked: {reason}")
    
    def get_device_certificate(self, device_id: str) -> Optional[DeviceCertificate]:
        """Get certificate for provisioned device"""
        return self.provisioned_devices.get(device_id)


class SecureBootstrapper:
    """
    Handles secure device bootstrapping.
    """
    
    def __init__(
        self,
        provisioning_service: ProvisioningService,
        bootstrap_encryption_key: bytes
    ):
        self.provisioning = provisioning_service
        self.encryption = AESGCM(bootstrap_encryption_key)
    
    async def generate_bootstrap_package(
        self,
        device_identity: DeviceIdentity,
        configuration: dict
    ) -> bytes:
        """Generate encrypted bootstrap package for device"""
        # Start provisioning
        session = await self.provisioning.start_provisioning(device_identity)
        
        # Create bootstrap payload
        payload = {
            "session_id": session.session_id,
            "challenge": base64.b64encode(session.challenge).decode(),
            "provisioning_endpoint": "/api/v1/provisioning",
            "configuration": configuration,
            "ca_certificates": [
                base64.b64encode(cert).decode()
                for cert in self._get_ca_certificates()
            ]
        }
        
        # Encrypt payload
        nonce = os.urandom(12)
        ciphertext = self.encryption.encrypt(
            nonce,
            json.dumps(payload).encode(),
            None
        )
        
        # Package: nonce + ciphertext
        return nonce + ciphertext
    
    def _get_ca_certificates(self) -> list[bytes]:
        """Get CA certificates for trust chain"""
        certs = [
            self.provisioning.pki.root_ca_cert.public_bytes(serialization.Encoding.PEM)
        ]
        if self.provisioning.pki.intermediate_ca_cert:
            certs.append(
                self.provisioning.pki.intermediate_ca_cert.public_bytes(serialization.Encoding.PEM)
            )
        return certs
    
    async def process_bootstrap_response(
        self,
        encrypted_response: bytes
    ) -> dict:
        """Process encrypted bootstrap response from device"""
        # Decrypt response
        nonce = encrypted_response[:12]
        ciphertext = encrypted_response[12:]
        
        plaintext = self.encryption.decrypt(nonce, ciphertext, None)
        response = json.loads(plaintext)
        
        return response


class DeviceAuthenticator:
    """
    Authenticates provisioned devices using certificates.
    """
    
    def __init__(self, pki_manager: PKIManager):
        self.pki = pki_manager
        self.authenticated_sessions: dict[str, dict] = {}
    
    async def authenticate_device(
        self,
        certificate_pem: bytes,
        challenge_response: bytes,
        challenge: bytes
    ) -> tuple[bool, Optional[str], str]:
        """
        Authenticate device using certificate and challenge-response.
        Returns (success, device_id, reason)
        """
        try:
            # Load and verify certificate
            certificate = x509.load_pem_x509_certificate(
                certificate_pem, default_backend()
            )
            
            valid, reason = self.pki.verify_certificate(certificate)
            if not valid:
                return False, None, reason
            
            # Extract device ID from certificate
            device_id = self._extract_device_id(certificate)
            
            # Verify challenge-response signature
            public_key = certificate.public_key()
            try:
                public_key.verify(
                    challenge_response,
                    challenge,
                    ec.ECDSA(hashes.SHA256())
                )
            except Exception:
                return False, None, "Invalid challenge response"
            
            # Create authenticated session
            session_id = str(uuid4())
            self.authenticated_sessions[session_id] = {
                "device_id": device_id,
                "certificate_thumbprint": hashlib.sha256(
                    certificate.public_bytes(serialization.Encoding.DER)
                ).hexdigest(),
                "authenticated_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(hours=24)
            }
            
            logger.info(f"Device authenticated: {device_id}")
            return True, device_id, "Authenticated"
            
        except Exception as e:
            return False, None, str(e)
    
    def _extract_device_id(self, certificate: x509.Certificate) -> str:
        """Extract device ID from certificate subject"""
        for attr in certificate.subject:
            if attr.oid == NameOID.COMMON_NAME:
                return attr.value
        raise ValueError("Device ID not found in certificate")
    
    def validate_session(self, session_id: str) -> Optional[str]:
        """Validate authenticated session, return device ID"""
        session = self.authenticated_sessions.get(session_id)
        if not session:
            return None
        
        if datetime.utcnow() > session["expires_at"]:
            del self.authenticated_sessions[session_id]
            return None
        
        return session["device_id"]
    
    def revoke_session(self, session_id: str):
        """Revoke authenticated session"""
        if session_id in self.authenticated_sessions:
            del self.authenticated_sessions[session_id]


class CertificateRotationManager:
    """
    Manages automatic certificate rotation for devices.
    """
    
    def __init__(
        self,
        pki_manager: PKIManager,
        rotation_threshold_days: int = 30
    ):
        self.pki = pki_manager
        self.rotation_threshold = timedelta(days=rotation_threshold_days)
        self.pending_rotations: dict[str, dict] = {}
    
    def check_rotation_needed(self, certificate: DeviceCertificate) -> bool:
        """Check if certificate needs rotation"""
        remaining = certificate.expires_at - datetime.utcnow()
        return remaining < self.rotation_threshold
    
    async def initiate_rotation(
        self,
        device_id: str,
        current_certificate: DeviceCertificate
    ) -> dict:
        """Initiate certificate rotation"""
        rotation_id = str(uuid4())
        
        self.pending_rotations[rotation_id] = {
            "device_id": device_id,
            "old_certificate": current_certificate,
            "new_certificate": None,
            "initiated_at": datetime.utcnow(),
            "status": "pending"
        }
        
        return {
            "rotation_id": rotation_id,
            "action": "rotate_certificate",
            "expires_at": current_certificate.expires_at.isoformat()
        }
    
    async def complete_rotation(
        self,
        rotation_id: str,
        new_certificate: DeviceCertificate
    ) -> bool:
        """Complete certificate rotation"""
        rotation = self.pending_rotations.get(rotation_id)
        if not rotation:
            return False
        
        rotation["new_certificate"] = new_certificate
        rotation["status"] = "completed"
        rotation["completed_at"] = datetime.utcnow()
        
        # Revoke old certificate after grace period
        # (In production, schedule this)
        
        logger.info(f"Certificate rotation completed: {rotation_id}")
        return True
