"""
Firmware Over-The-Air (OTA) Update System

Provides secure firmware distribution and update management for IoT devices.

Features:
- Signed firmware images with Ed25519 signatures
- Delta/differential updates for bandwidth efficiency
- Rollback mechanism for failed updates
- Staged rollout with canary deployments
- Update scheduling and maintenance windows
- Firmware version management
"""

import asyncio
import hashlib
import hmac
import logging
import os
import struct
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, BinaryIO, Optional

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class UpdateStatus(Enum):
    """Firmware update status"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    VERIFYING = "verifying"
    INSTALLING = "installing"
    REBOOTING = "rebooting"
    COMPLETE = "complete"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class UpdatePriority(Enum):
    """Update priority levels"""
    CRITICAL = 1  # Security patches - immediate
    HIGH = 2      # Bug fixes - within 24h
    NORMAL = 3    # Feature updates - scheduled
    LOW = 4       # Optional updates - user initiated


class RolloutStrategy(Enum):
    """Firmware rollout strategies"""
    IMMEDIATE = "immediate"
    STAGED = "staged"
    CANARY = "canary"
    SCHEDULED = "scheduled"


@dataclass
class FirmwareVersion:
    """Firmware version information"""
    major: int
    minor: int
    patch: int
    build: int = 0
    prerelease: str = ""
    
    def __str__(self) -> str:
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.build:
            version += f"+{self.build}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        return version
    
    def __lt__(self, other: 'FirmwareVersion') -> bool:
        return (self.major, self.minor, self.patch, self.build) < \
               (other.major, other.minor, other.patch, other.build)
    
    @classmethod
    def parse(cls, version_str: str) -> 'FirmwareVersion':
        """Parse version string"""
        parts = version_str.replace('+', '.').replace('-', '.').split('.')
        return cls(
            major=int(parts[0]) if len(parts) > 0 else 0,
            minor=int(parts[1]) if len(parts) > 1 else 0,
            patch=int(parts[2]) if len(parts) > 2 else 0,
            build=int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0
        )


@dataclass
class FirmwareManifest:
    """Firmware image manifest"""
    firmware_id: str
    version: FirmwareVersion
    device_type: str
    file_size: int
    sha256_hash: str
    signature: bytes
    created_at: datetime
    download_url: str
    delta_base_version: Optional[FirmwareVersion] = None
    is_delta: bool = False
    min_battery_level: int = 30
    requires_power: bool = False
    changelog: str = ""
    priority: UpdatePriority = UpdatePriority.NORMAL
    metadata: dict = field(default_factory=dict)


@dataclass
class UpdateJob:
    """OTA update job"""
    job_id: str
    device_id: str
    firmware: FirmwareManifest
    status: UpdateStatus = UpdateStatus.PENDING
    progress: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


class FirmwareSigner:
    """
    Signs firmware images using Ed25519.
    """
    
    def __init__(self, private_key_path: Optional[str] = None):
        self._private_key: Optional[ed25519.Ed25519PrivateKey] = None
        self._public_key: Optional[ed25519.Ed25519PublicKey] = None
        
        if private_key_path:
            self.load_private_key(private_key_path)
    
    def generate_keypair(self) -> tuple[bytes, bytes]:
        """Generate new Ed25519 keypair"""
        self._private_key = ed25519.Ed25519PrivateKey.generate()
        self._public_key = self._private_key.public_key()
        
        private_bytes = self._private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_bytes = self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        return private_bytes, public_bytes
    
    def load_private_key(self, path: str):
        """Load private key from file"""
        with open(path, 'rb') as f:
            key_data = f.read()
        
        if len(key_data) == 32:
            # Raw key
            self._private_key = ed25519.Ed25519PrivateKey.from_private_bytes(key_data)
        else:
            # PEM encoded
            self._private_key = serialization.load_pem_private_key(
                key_data, password=None, backend=default_backend()
            )
        
        self._public_key = self._private_key.public_key()
    
    def sign_firmware(self, firmware_data: bytes) -> bytes:
        """Sign firmware image"""
        if not self._private_key:
            raise ValueError("Private key not loaded")
        
        return self._private_key.sign(firmware_data)
    
    def sign_file(self, file_path: str) -> bytes:
        """Sign firmware file"""
        with open(file_path, 'rb') as f:
            data = f.read()
        return self.sign_firmware(data)
    
    def get_public_key(self) -> bytes:
        """Get public key bytes"""
        if not self._public_key:
            raise ValueError("No key loaded")
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )


class FirmwareVerifier:
    """
    Verifies firmware signatures using Ed25519.
    """
    
    def __init__(self, public_keys: list[bytes]):
        self._public_keys = [
            ed25519.Ed25519PublicKey.from_public_bytes(k) if isinstance(k, bytes)
            else k
            for k in public_keys
        ]
    
    def verify_signature(self, firmware_data: bytes, signature: bytes) -> bool:
        """Verify firmware signature against any trusted public key"""
        for public_key in self._public_keys:
            try:
                public_key.verify(signature, firmware_data)
                return True
            except Exception:
                continue
        return False
    
    def verify_hash(self, firmware_data: bytes, expected_hash: str) -> bool:
        """Verify firmware SHA-256 hash"""
        actual_hash = hashlib.sha256(firmware_data).hexdigest()
        return hmac.compare_digest(actual_hash, expected_hash)


class DeltaUpdateGenerator:
    """
    Generates delta/differential updates between firmware versions.
    Uses bsdiff-style binary diffing.
    """
    
    @staticmethod
    def generate_delta(old_firmware: bytes, new_firmware: bytes) -> bytes:
        """
        Generate delta update from old to new firmware.
        Uses a simple block-based approach for demonstration.
        In production, use bsdiff/bspatch.
        """
        block_size = 4096
        delta_data = bytearray()
        
        # Header: magic, old_size, new_size
        delta_data.extend(b'DELT')  # Magic
        delta_data.extend(struct.pack('<Q', len(old_firmware)))
        delta_data.extend(struct.pack('<Q', len(new_firmware)))
        
        # Simple block comparison
        old_blocks = [old_firmware[i:i+block_size] 
                      for i in range(0, len(old_firmware), block_size)]
        new_blocks = [new_firmware[i:i+block_size] 
                      for i in range(0, len(new_firmware), block_size)]
        
        old_hashes = {hashlib.md5(b).digest(): i for i, b in enumerate(old_blocks)}
        
        for i, new_block in enumerate(new_blocks):
            block_hash = hashlib.md5(new_block).digest()
            
            if block_hash in old_hashes:
                # Block exists in old firmware - reference it
                delta_data.append(0x00)  # Copy command
                delta_data.extend(struct.pack('<I', old_hashes[block_hash]))
            else:
                # New block - include raw data
                delta_data.append(0x01)  # Insert command
                delta_data.extend(struct.pack('<I', len(new_block)))
                delta_data.extend(new_block)
        
        return bytes(delta_data)
    
    @staticmethod
    def apply_delta(old_firmware: bytes, delta: bytes) -> bytes:
        """Apply delta update to old firmware"""
        if delta[:4] != b'DELT':
            raise ValueError("Invalid delta format")
        
        old_size = struct.unpack('<Q', delta[4:12])[0]
        new_size = struct.unpack('<Q', delta[12:20])[0]
        
        if len(old_firmware) != old_size:
            raise ValueError("Old firmware size mismatch")
        
        block_size = 4096
        old_blocks = [old_firmware[i:i+block_size] 
                      for i in range(0, len(old_firmware), block_size)]
        
        new_firmware = bytearray()
        offset = 20
        
        while offset < len(delta):
            command = delta[offset]
            offset += 1
            
            if command == 0x00:  # Copy
                block_idx = struct.unpack('<I', delta[offset:offset+4])[0]
                offset += 4
                new_firmware.extend(old_blocks[block_idx])
            elif command == 0x01:  # Insert
                block_len = struct.unpack('<I', delta[offset:offset+4])[0]
                offset += 4
                new_firmware.extend(delta[offset:offset+block_len])
                offset += block_len
            else:
                raise ValueError(f"Unknown delta command: {command}")
        
        if len(new_firmware) != new_size:
            raise ValueError("New firmware size mismatch after delta apply")
        
        return bytes(new_firmware)


class RollbackManager:
    """
    Manages firmware rollback for failed updates.
    """
    
    def __init__(self, storage_path: str, max_backups: int = 2):
        self.storage_path = Path(storage_path)
        self.max_backups = max_backups
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def backup_current_firmware(self, device_id: str, firmware_data: bytes, 
                                version: FirmwareVersion) -> str:
        """Backup current firmware before update"""
        backup_id = f"{device_id}_{version}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        backup_path = self.storage_path / f"{backup_id}.bin"
        
        with open(backup_path, 'wb') as f:
            f.write(firmware_data)
        
        # Maintain max backups
        self._cleanup_old_backups(device_id)
        
        logger.info(f"Created firmware backup: {backup_id}")
        return backup_id
    
    def _cleanup_old_backups(self, device_id: str):
        """Remove old backups exceeding max_backups"""
        backups = sorted(
            self.storage_path.glob(f"{device_id}_*.bin"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        for old_backup in backups[self.max_backups:]:
            old_backup.unlink()
            logger.info(f"Removed old backup: {old_backup.name}")
    
    def get_rollback_firmware(self, device_id: str) -> Optional[tuple[bytes, str]]:
        """Get most recent backup for rollback"""
        backups = sorted(
            self.storage_path.glob(f"{device_id}_*.bin"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        if backups:
            with open(backups[0], 'rb') as f:
                return f.read(), backups[0].stem
        return None
    
    def list_backups(self, device_id: str) -> list[dict]:
        """List available backups for device"""
        backups = []
        for backup in self.storage_path.glob(f"{device_id}_*.bin"):
            stat = backup.stat()
            backups.append({
                "backup_id": backup.stem,
                "size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime)
            })
        return sorted(backups, key=lambda b: b["created_at"], reverse=True)


class OTAServer:
    """
    OTA Update Server for managing firmware distribution.
    """
    
    def __init__(
        self,
        firmware_storage: str,
        signer: FirmwareSigner,
        verifier: FirmwareVerifier
    ):
        self.firmware_storage = Path(firmware_storage)
        self.firmware_storage.mkdir(parents=True, exist_ok=True)
        self.signer = signer
        self.verifier = verifier
        self.manifests: dict[str, FirmwareManifest] = {}
        self.update_jobs: dict[str, UpdateJob] = {}
        self.rollback_manager = RollbackManager(str(self.firmware_storage / "backups"))
    
    async def upload_firmware(
        self,
        firmware_data: bytes,
        version: FirmwareVersion,
        device_type: str,
        priority: UpdatePriority = UpdatePriority.NORMAL,
        changelog: str = ""
    ) -> FirmwareManifest:
        """Upload and register new firmware"""
        # Calculate hash
        sha256_hash = hashlib.sha256(firmware_data).hexdigest()
        
        # Sign firmware
        signature = self.signer.sign_firmware(firmware_data)
        
        # Generate firmware ID
        firmware_id = f"{device_type}_{version}_{sha256_hash[:8]}"
        
        # Store firmware
        firmware_path = self.firmware_storage / f"{firmware_id}.bin"
        with open(firmware_path, 'wb') as f:
            f.write(firmware_data)
        
        # Create manifest
        manifest = FirmwareManifest(
            firmware_id=firmware_id,
            version=version,
            device_type=device_type,
            file_size=len(firmware_data),
            sha256_hash=sha256_hash,
            signature=signature,
            created_at=datetime.now(),
            download_url=f"/firmware/{firmware_id}",
            priority=priority,
            changelog=changelog
        )
        
        self.manifests[firmware_id] = manifest
        logger.info(f"Uploaded firmware: {firmware_id}")
        
        return manifest
    
    async def create_delta_update(
        self,
        base_firmware_id: str,
        target_firmware_id: str
    ) -> FirmwareManifest:
        """Create delta update between two firmware versions"""
        base_manifest = self.manifests.get(base_firmware_id)
        target_manifest = self.manifests.get(target_firmware_id)
        
        if not base_manifest or not target_manifest:
            raise ValueError("Firmware not found")
        
        # Load firmware data
        base_path = self.firmware_storage / f"{base_firmware_id}.bin"
        target_path = self.firmware_storage / f"{target_firmware_id}.bin"
        
        with open(base_path, 'rb') as f:
            base_data = f.read()
        with open(target_path, 'rb') as f:
            target_data = f.read()
        
        # Generate delta
        delta_data = DeltaUpdateGenerator.generate_delta(base_data, target_data)
        
        # Sign delta
        signature = self.signer.sign_firmware(delta_data)
        sha256_hash = hashlib.sha256(delta_data).hexdigest()
        
        # Store delta
        delta_id = f"delta_{base_firmware_id}_to_{target_firmware_id}"
        delta_path = self.firmware_storage / f"{delta_id}.delta"
        with open(delta_path, 'wb') as f:
            f.write(delta_data)
        
        # Create delta manifest
        delta_manifest = FirmwareManifest(
            firmware_id=delta_id,
            version=target_manifest.version,
            device_type=target_manifest.device_type,
            file_size=len(delta_data),
            sha256_hash=sha256_hash,
            signature=signature,
            created_at=datetime.now(),
            download_url=f"/firmware/{delta_id}",
            delta_base_version=base_manifest.version,
            is_delta=True,
            priority=target_manifest.priority
        )
        
        self.manifests[delta_id] = delta_manifest
        
        compression_ratio = len(delta_data) / len(target_data) * 100
        logger.info(f"Created delta update: {delta_id} ({compression_ratio:.1f}% of full size)")
        
        return delta_manifest
    
    async def check_for_updates(
        self,
        device_id: str,
        device_type: str,
        current_version: FirmwareVersion
    ) -> Optional[FirmwareManifest]:
        """Check if update is available for device"""
        # Find latest firmware for device type
        latest = None
        for manifest in self.manifests.values():
            if manifest.device_type != device_type:
                continue
            if manifest.is_delta:
                continue
            if manifest.version <= current_version:
                continue
            if latest is None or manifest.version > latest.version:
                latest = manifest
        
        if latest:
            # Check if delta update is available
            delta_id = f"delta_{device_type}_{current_version}_to_{latest.version}"
            delta = self.manifests.get(delta_id)
            if delta:
                return delta
        
        return latest
    
    async def create_update_job(
        self,
        device_id: str,
        firmware_id: str
    ) -> UpdateJob:
        """Create update job for device"""
        manifest = self.manifests.get(firmware_id)
        if not manifest:
            raise ValueError(f"Firmware not found: {firmware_id}")
        
        job = UpdateJob(
            job_id=f"{device_id}_{firmware_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            device_id=device_id,
            firmware=manifest
        )
        
        self.update_jobs[job.job_id] = job
        logger.info(f"Created update job: {job.job_id}")
        
        return job
    
    async def update_job_status(
        self,
        job_id: str,
        status: UpdateStatus,
        progress: float = 0.0,
        error_message: Optional[str] = None
    ):
        """Update job status"""
        job = self.update_jobs.get(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")
        
        job.status = status
        job.progress = progress
        
        if status == UpdateStatus.DOWNLOADING and not job.started_at:
            job.started_at = datetime.now()
        
        if status in [UpdateStatus.COMPLETE, UpdateStatus.FAILED, UpdateStatus.ROLLED_BACK]:
            job.completed_at = datetime.now()
        
        if error_message:
            job.error_message = error_message
        
        logger.info(f"Job {job_id}: {status.value} ({progress:.1f}%)")
    
    def get_firmware_data(self, firmware_id: str) -> bytes:
        """Get firmware binary data"""
        if firmware_id not in self.manifests:
            raise ValueError(f"Firmware not found: {firmware_id}")
        
        manifest = self.manifests[firmware_id]
        
        if manifest.is_delta:
            firmware_path = self.firmware_storage / f"{firmware_id}.delta"
        else:
            firmware_path = self.firmware_storage / f"{firmware_id}.bin"
        
        with open(firmware_path, 'rb') as f:
            return f.read()


class OTAClient:
    """
    OTA Client for device-side update management.
    """
    
    def __init__(
        self,
        device_id: str,
        device_type: str,
        current_version: FirmwareVersion,
        verifier: FirmwareVerifier,
        firmware_partition_path: str,
        backup_partition_path: str
    ):
        self.device_id = device_id
        self.device_type = device_type
        self.current_version = current_version
        self.verifier = verifier
        self.firmware_partition = Path(firmware_partition_path)
        self.backup_partition = Path(backup_partition_path)
        
        self._current_job: Optional[UpdateJob] = None
        self._download_buffer: bytearray = bytearray()
    
    async def check_preconditions(self, manifest: FirmwareManifest) -> tuple[bool, str]:
        """Check if device meets update preconditions"""
        # Check battery level
        battery_level = await self._get_battery_level()
        if battery_level < manifest.min_battery_level:
            return False, f"Battery too low: {battery_level}% (need {manifest.min_battery_level}%)"
        
        # Check power connection if required
        if manifest.requires_power and not await self._is_charging():
            return False, "Device must be connected to power"
        
        # Check storage space
        available_space = await self._get_available_space()
        required_space = manifest.file_size * 2  # Need space for download + install
        if available_space < required_space:
            return False, f"Insufficient storage: {available_space} bytes (need {required_space})"
        
        return True, "OK"
    
    async def download_firmware(
        self,
        manifest: FirmwareManifest,
        data_stream: asyncio.StreamReader,
        progress_callback: callable = None
    ) -> bytes:
        """Download firmware with progress tracking"""
        self._download_buffer.clear()
        downloaded = 0
        
        while True:
            chunk = await data_stream.read(8192)
            if not chunk:
                break
            
            self._download_buffer.extend(chunk)
            downloaded += len(chunk)
            
            if progress_callback:
                progress = downloaded / manifest.file_size * 100
                await progress_callback(progress)
        
        return bytes(self._download_buffer)
    
    async def verify_firmware(self, firmware_data: bytes, manifest: FirmwareManifest) -> bool:
        """Verify downloaded firmware"""
        # Verify hash
        if not self.verifier.verify_hash(firmware_data, manifest.sha256_hash):
            logger.error("Firmware hash verification failed")
            return False
        
        # Verify signature
        if not self.verifier.verify_signature(firmware_data, manifest.signature):
            logger.error("Firmware signature verification failed")
            return False
        
        logger.info("Firmware verification successful")
        return True
    
    async def install_firmware(
        self,
        firmware_data: bytes,
        manifest: FirmwareManifest,
        progress_callback: callable = None
    ) -> bool:
        """Install firmware to device"""
        try:
            # Backup current firmware
            if self.firmware_partition.exists():
                with open(self.firmware_partition, 'rb') as f:
                    current_data = f.read()
                with open(self.backup_partition, 'wb') as f:
                    f.write(current_data)
                logger.info("Current firmware backed up")
            
            # Apply delta if needed
            if manifest.is_delta:
                with open(self.firmware_partition, 'rb') as f:
                    old_data = f.read()
                firmware_data = DeltaUpdateGenerator.apply_delta(old_data, firmware_data)
                logger.info("Delta update applied")
            
            # Write new firmware
            with open(self.firmware_partition, 'wb') as f:
                written = 0
                chunk_size = 4096
                while written < len(firmware_data):
                    chunk = firmware_data[written:written + chunk_size]
                    f.write(chunk)
                    written += len(chunk)
                    
                    if progress_callback:
                        await progress_callback(written / len(firmware_data) * 100)
            
            logger.info("Firmware installed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Firmware installation failed: {e}")
            await self._rollback()
            return False
    
    async def _rollback(self) -> bool:
        """Rollback to previous firmware"""
        try:
            if self.backup_partition.exists():
                with open(self.backup_partition, 'rb') as f:
                    backup_data = f.read()
                with open(self.firmware_partition, 'wb') as f:
                    f.write(backup_data)
                logger.info("Firmware rolled back successfully")
                return True
            else:
                logger.error("No backup available for rollback")
                return False
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False
    
    async def perform_update(
        self,
        manifest: FirmwareManifest,
        firmware_data: bytes,
        reboot_callback: callable = None
    ) -> bool:
        """Perform complete update process"""
        # Verify
        if not await self.verify_firmware(firmware_data, manifest):
            return False
        
        # Install
        if not await self.install_firmware(firmware_data, manifest):
            return False
        
        # Update version
        self.current_version = manifest.version
        
        # Trigger reboot if callback provided
        if reboot_callback:
            await reboot_callback()
        
        return True
    
    # Device-specific methods (to be implemented per device)
    async def _get_battery_level(self) -> int:
        return 100  # Placeholder
    
    async def _is_charging(self) -> bool:
        return True  # Placeholder
    
    async def _get_available_space(self) -> int:
        return 100 * 1024 * 1024  # 100MB placeholder


class StagedRolloutManager:
    """
    Manages staged/canary firmware rollouts.
    """
    
    def __init__(self):
        self.rollouts: dict[str, dict] = {}
    
    def create_staged_rollout(
        self,
        firmware_id: str,
        stages: list[dict],
        rollback_threshold: float = 0.05  # 5% failure rate triggers rollback
    ) -> str:
        """Create staged rollout configuration"""
        rollout_id = f"rollout_{firmware_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        self.rollouts[rollout_id] = {
            "firmware_id": firmware_id,
            "stages": stages,  # [{"percentage": 5, "duration_hours": 24}, ...]
            "current_stage": 0,
            "rollback_threshold": rollback_threshold,
            "status": "active",
            "stats": {
                "total_devices": 0,
                "updated_devices": 0,
                "failed_devices": 0,
                "rolled_back_devices": 0
            },
            "created_at": datetime.now()
        }
        
        return rollout_id
    
    def should_update_device(self, rollout_id: str, device_id: str) -> bool:
        """Check if device should receive update in current stage"""
        rollout = self.rollouts.get(rollout_id)
        if not rollout or rollout["status"] != "active":
            return False
        
        current_stage = rollout["current_stage"]
        if current_stage >= len(rollout["stages"]):
            return True  # All stages complete
        
        stage_config = rollout["stages"][current_stage]
        target_percentage = stage_config["percentage"]
        
        # Use device ID hash for consistent selection
        device_hash = int(hashlib.md5(device_id.encode()).hexdigest()[:8], 16)
        device_percentile = (device_hash % 100) + 1
        
        return device_percentile <= target_percentage
    
    def record_update_result(self, rollout_id: str, success: bool):
        """Record update result for rollout statistics"""
        rollout = self.rollouts.get(rollout_id)
        if not rollout:
            return
        
        rollout["stats"]["total_devices"] += 1
        
        if success:
            rollout["stats"]["updated_devices"] += 1
        else:
            rollout["stats"]["failed_devices"] += 1
        
        # Check rollback threshold
        total = rollout["stats"]["total_devices"]
        failed = rollout["stats"]["failed_devices"]
        
        if total >= 10 and (failed / total) > rollout["rollback_threshold"]:
            rollout["status"] = "paused"
            logger.warning(f"Rollout {rollout_id} paused due to high failure rate")
    
    def advance_stage(self, rollout_id: str) -> bool:
        """Advance rollout to next stage"""
        rollout = self.rollouts.get(rollout_id)
        if not rollout:
            return False
        
        rollout["current_stage"] += 1
        
        if rollout["current_stage"] >= len(rollout["stages"]):
            rollout["status"] = "complete"
            logger.info(f"Rollout {rollout_id} complete")
        
        return True
