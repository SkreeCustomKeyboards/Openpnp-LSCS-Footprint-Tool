"""Backup management for OpenPnP configuration files.

Handles creating, restoring, and managing backups of configuration files.
"""

import shutil
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, field


class BackupError(Exception):
    """Error during backup operations."""
    pass


@dataclass
class BackupManifest:
    """Manifest tracking backup contents and metadata.
    
    Attributes:
        timestamp: When the backup was created
        files: Dict mapping filename to file hash
        description: Optional description of backup
    """
    timestamp: str
    files: dict[str, str] = field(default_factory=dict)
    description: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert manifest to dictionary."""
        return {
            "timestamp": self.timestamp,
            "files": self.files,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "BackupManifest":
        """Create manifest from dictionary."""
        return cls(
            timestamp=data.get("timestamp", ""),
            files=data.get("files", {}),
            description=data.get("description")
        )


@dataclass
class Backup:
    """Represents a single backup.
    
    Attributes:
        path: Path to backup directory
        manifest: Backup manifest with metadata
    """
    path: Path
    manifest: BackupManifest
    
    @property
    def timestamp(self) -> str:
        """Backup timestamp."""
        return self.manifest.timestamp
    
    @property
    def datetime(self) -> datetime:
        """Backup datetime object."""
        return datetime.strptime(self.manifest.timestamp, "%Y%m%d_%H%M%S")


def compute_file_hash(filepath: Path) -> str:
    """Compute SHA256 hash of a file.
    
    Args:
        filepath: Path to file
        
    Returns:
        Hex digest of file hash
    """
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


class BackupManager:
    """Manages backups of OpenPnP configuration files.
    
    Creates timestamped backups before modifications and provides
    restoration capability.
    """
    
    def __init__(self, backup_dir: Path, source_dir: Path):
        """Initialize backup manager.
        
        Args:
            backup_dir: Directory to store backups
            source_dir: Source directory containing files to backup
        """
        self._backup_dir = backup_dir
        self._source_dir = source_dir
        self._current_backup: Optional[Backup] = None
    
    @property
    def backup_dir(self) -> Path:
        """Path to backup directory."""
        return self._backup_dir
    
    def list_backups(self) -> List[Backup]:
        """List all available backups, newest first.
        
        Returns:
            List of Backup objects
        """
        backups = []
        
        if not self._backup_dir.exists():
            return backups
        
        for backup_path in self._backup_dir.iterdir():
            if not backup_path.is_dir():
                continue
            
            manifest_path = backup_path / "manifest.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path) as f:
                        manifest_data = json.load(f)
                    manifest = BackupManifest.from_dict(manifest_data)
                    backups.append(Backup(path=backup_path, manifest=manifest))
                except (json.JSONDecodeError, KeyError):
                    continue
        
        # Sort by timestamp, newest first
        backups.sort(key=lambda b: b.timestamp, reverse=True)
        return backups
    
    def create_backup(self, description: Optional[str] = None) -> Backup:
        """Create a backup of current configuration files.
        
        Args:
            description: Optional description for this backup
            
        Returns:
            Backup object representing the created backup
            
        Raises:
            BackupError: If backup creation fails
        """
        # Create timestamp-based backup directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self._backup_dir / timestamp
        
        try:
            backup_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise BackupError(f"Failed to create backup directory: {e}")
        
        # Files to backup
        files_to_backup = ["packages.xml", "parts.xml"]
        file_hashes = {}
        
        for filename in files_to_backup:
            source_file = self._source_dir / filename
            if source_file.exists():
                try:
                    dest_file = backup_path / filename
                    shutil.copy2(source_file, dest_file)
                    file_hashes[filename] = compute_file_hash(dest_file)
                except IOError as e:
                    # Cleanup on failure
                    shutil.rmtree(backup_path, ignore_errors=True)
                    raise BackupError(f"Failed to backup {filename}: {e}")
        
        # Create manifest
        manifest = BackupManifest(
            timestamp=timestamp,
            files=file_hashes,
            description=description
        )
        
        manifest_path = backup_path / "manifest.json"
        try:
            with open(manifest_path, "w") as f:
                json.dump(manifest.to_dict(), f, indent=2)
        except IOError as e:
            raise BackupError(f"Failed to write manifest: {e}")
        
        backup = Backup(path=backup_path, manifest=manifest)
        self._current_backup = backup
        
        return backup
    
    def restore_backup(self, backup: Backup) -> None:
        """Restore files from a backup.
        
        Args:
            backup: Backup to restore from
            
        Raises:
            BackupError: If restoration fails
        """
        if not backup.path.exists():
            raise BackupError(f"Backup directory not found: {backup.path}")
        
        for filename in backup.manifest.files:
            backup_file = backup.path / filename
            dest_file = self._source_dir / filename
            
            if not backup_file.exists():
                raise BackupError(f"Backup file missing: {backup_file}")
            
            try:
                shutil.copy2(backup_file, dest_file)
            except IOError as e:
                raise BackupError(f"Failed to restore {filename}: {e}")
    
    def delete_backup(self, backup: Backup) -> None:
        """Delete a backup.
        
        Args:
            backup: Backup to delete
            
        Raises:
            BackupError: If deletion fails
        """
        try:
            shutil.rmtree(backup.path)
        except OSError as e:
            raise BackupError(f"Failed to delete backup: {e}")
    
    def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """Remove old backups, keeping the most recent ones.
        
        Args:
            keep_count: Number of backups to keep
            
        Returns:
            Number of backups deleted
        """
        backups = self.list_backups()
        deleted = 0
        
        if len(backups) > keep_count:
            for backup in backups[keep_count:]:
                try:
                    self.delete_backup(backup)
                    deleted += 1
                except BackupError:
                    pass
        
        return deleted
    
    def verify_backup(self, backup: Backup) -> bool:
        """Verify backup integrity by checking file hashes.
        
        Args:
            backup: Backup to verify
            
        Returns:
            True if backup is valid, False otherwise
        """
        for filename, expected_hash in backup.manifest.files.items():
            filepath = backup.path / filename
            if not filepath.exists():
                return False
            
            actual_hash = compute_file_hash(filepath)
            if actual_hash != expected_hash:
                return False
        
        return True
    
    @property
    def current_backup(self) -> Optional[Backup]:
        """Get the most recently created backup in this session."""
        return self._current_backup
