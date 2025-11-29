"""File-based repository mixin.

This module provides a mixin class that adds file-based persistence
to repositories. It handles:

- Reading/writing JSON files
- File locking for concurrent access
- Atomic writes for data safety
- State-based directory organization
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar

from .base import EntityId
from .protocols import Entity
from .exceptions import PersistenceError, LockError
import fcntl

T = TypeVar("T", bound=Entity)


class FileRepositoryMixin(Generic[T]):
    """Mixin providing file-based persistence for repositories.
    
    This mixin adds methods for reading/writing entities to JSON files
    with proper locking and atomic operations.
    
    The mixin expects the repository to define:
    - entity_type: str - The entity type name
    - project_root: Optional[Path] - Project root directory
    
    And optionally:
    - _get_state_dir(state: str) -> Path - Get directory for a state
    """
    
    # Override in subclass to specify file extension
    file_extension: str = ".json"
    
    def _get_entity_filename(self, entity_id: EntityId) -> str:
        """Generate filename for an entity.
        
        Override in subclass for custom naming.
        
        Args:
            entity_id: Entity identifier
            
        Returns:
            Filename (without path)
        """
        return f"{entity_id}{self.file_extension}"
    
    def _resolve_entity_path(
        self, 
        entity_id: EntityId, 
        state: Optional[str] = None,
    ) -> Path:
        """Resolve the file path for an entity.
        
        Must be implemented by subclass to define path structure.
        
        Args:
            entity_id: Entity identifier
            state: Entity state (for state-based directories)
            
        Returns:
            Full path to entity file
        """
        raise NotImplementedError("Subclass must implement _resolve_entity_path")
    
    def _get_states_to_search(self) -> List[str]:
        """Get list of states to search when finding entities.

        Subclasses should override this method to provide domain-specific states
        from configuration. The default implementation requires override.

        Returns:
            List of state names

        Raises:
            NotImplementedError: If subclass doesn't override this method
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must override _get_states_to_search() "
            "to provide domain-specific states from configuration"
        )
    
    def _find_entity_path(self, entity_id: EntityId) -> Optional[Path]:
        """Find an entity file by searching state directories.

        Args:
            entity_id: Entity identifier

        Returns:
            Path to entity file if found, None otherwise
        """
        for state in self._get_states_to_search():
            path = self._resolve_entity_path(entity_id, state)
            if path.exists():
                return path
        return None

    def get_path(self, entity_id: EntityId) -> Path:
        """Get the file path for an entity.

        This is the public API for finding entity paths.
        Unlike _find_entity_path, this raises FileNotFoundError if not found.

        Args:
            entity_id: Entity identifier

        Returns:
            Path to entity file

        Raises:
            FileNotFoundError: If entity not found
        """
        path = self._find_entity_path(entity_id)
        if path is None:
            entity_type = getattr(self, "entity_type", "entity")
            raise FileNotFoundError(f"{entity_type.title()} {entity_id} not found")
        return path
    
    def _read_file(self, path: Path) -> Dict[str, Any]:
        """Read and parse a JSON file.
        
        Args:
            path: Path to JSON file
            
        Returns:
            Parsed JSON data
            
        Raises:
            PersistenceError: If read fails
        """
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise PersistenceError(f"Invalid JSON in {path}: {e}")
        except OSError as e:
            raise PersistenceError(f"Cannot read {path}: {e}")
    
    def _write_file(
        self, 
        path: Path, 
        data: Dict[str, Any],
        *,
        atomic: bool = True,
    ) -> None:
        """Write data to a JSON file.
        
        Args:
            path: Path to write to
            data: Data to serialize
            atomic: If True, use atomic write (write to temp then rename)
            
        Raises:
            PersistenceError: If write fails
        """
        try:
            # Ensure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)
            
            content = json.dumps(data, indent=2, ensure_ascii=False)
            
            if atomic:
                # Write to temp file then rename for atomicity
                temp_path = path.with_suffix(f"{path.suffix}.tmp")
                temp_path.write_text(content, encoding="utf-8")
                temp_path.rename(path)
            else:
                path.write_text(content, encoding="utf-8")
        except OSError as e:
            raise PersistenceError(f"Cannot write {path}: {e}")
    
    def _move_to_state(
        self,
        entity_id: EntityId,
        from_state: str,
        to_state: str,
    ) -> Path:
        """Move an entity file from one state directory to another.
        
        Args:
            entity_id: Entity identifier
            from_state: Current state (source directory)
            to_state: Target state (destination directory)
            
        Returns:
            New path after move
            
        Raises:
            PersistenceError: If move fails
        """
        source = self._resolve_entity_path(entity_id, from_state)
        dest = self._resolve_entity_path(entity_id, to_state)
        
        if not source.exists():
            raise PersistenceError(f"Source file not found: {source}")
        
        try:
            # Ensure destination directory exists
            dest.parent.mkdir(parents=True, exist_ok=True)
            
            # Move file
            source.rename(dest)
            
            return dest
        except OSError as e:
            raise PersistenceError(f"Cannot move {source} to {dest}: {e}")
    
    def _safe_move_file(
        self,
        source: Path,
        dest: Path,
        *,
        create_parents: bool = True,
    ) -> Path:
        """Safely move a file with directory creation.
        
        Args:
            source: Source path
            dest: Destination path
            create_parents: Create parent directories if needed
            
        Returns:
            Destination path
            
        Raises:
            PersistenceError: If move fails
        """
        try:
            if create_parents:
                dest.parent.mkdir(parents=True, exist_ok=True)
            source.rename(dest)
            return dest
        except OSError as e:
            raise PersistenceError(f"Cannot move {source} to {dest}: {e}")
    
    def _list_files_in_state(self, state: str) -> List[Path]:
        """List all entity files in a state directory.
        
        Args:
            state: State name
            
        Returns:
            List of file paths
        """
        # Get state directory - subclass should implement
        if hasattr(self, "_get_state_dir"):
            state_dir = self._get_state_dir(state)  # type: ignore
        else:
            # Fallback - try to construct from project_root
            project_root = getattr(self, "project_root", None)
            entity_type = getattr(self, "entity_type", "entity")
            if project_root:
                state_dir = Path(project_root) / ".project" / f"{entity_type}s" / state
            else:
                return []
        
        if not state_dir.exists():
            return []
        
        pattern = f"*{self.file_extension}"
        return list(state_dir.glob(pattern))
    
    def _list_all_files(self) -> List[Path]:
        """List all entity files across all states.
        
        Returns:
            List of file paths
        """
        files: List[Path] = []
        for state in self._get_states_to_search():
            files.extend(self._list_files_in_state(state))
        return files


class FileLockMixin:
    """Mixin providing file locking for repositories.
    
    Uses fcntl for POSIX file locking to prevent concurrent access.
    """
    
    def _acquire_lock(
        self,
        path: Path,
        *,
        timeout: float = 10.0,
        exclusive: bool = True,
    ) -> Any:
        """Acquire a file lock.

        Args:
            path: File to lock
            timeout: Lock timeout in seconds
            exclusive: If True, acquire exclusive lock

        Returns:
            Lock handle (file object)

        Raises:
            LockError: If lock cannot be acquired
        """
        import fcntl
        import time
        from edison.core.utils.io.locking import get_file_locking_config

        lock_path = path.with_suffix(f"{path.suffix}.lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)

        # Get poll interval from config
        config = get_file_locking_config()
        poll_interval = config.get("poll_interval_seconds", 0.1)

        start = time.time()
        while True:
            try:
                lock_file = open(lock_path, "w")
                flags = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
                flags |= fcntl.LOCK_NB
                fcntl.flock(lock_file.fileno(), flags)
                return lock_file
            except (IOError, OSError):
                if time.time() - start > timeout:
                    raise LockError(f"Cannot acquire lock on {path} after {timeout}s")
                time.sleep(poll_interval)
    
    def _release_lock(self, lock_handle: Any) -> None:
        """Release a file lock.
        
        Args:
            lock_handle: Lock handle from _acquire_lock
        """
        
        if lock_handle:
            try:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
                lock_handle.close()
            except Exception:
                pass


__all__ = [
    "FileRepositoryMixin",
    "FileLockMixin",
]


