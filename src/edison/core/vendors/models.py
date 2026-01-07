"""Vendor data models.

Provides immutable dataclasses for vendor configuration and state.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class VendorSource:
    """Represents a vendor source configuration.

    Attributes:
        name: Unique vendor identifier
        url: Git repository URL
        ref: Git ref (branch, tag, or commit)
        path: Local checkout path relative to repo root
        sparse: Optional list of sparse checkout paths
    """

    name: str
    url: str
    ref: str
    path: str
    sparse: list[str] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VendorSource:
        """Create VendorSource from dictionary.

        Args:
            data: Dictionary with vendor source fields

        Returns:
            VendorSource instance
        """
        return cls(
            name=data["name"],
            url=data["url"],
            ref=data["ref"],
            path=data["path"],
            sparse=data.get("sparse"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation
        """
        result: dict[str, Any] = {
            "name": self.name,
            "url": self.url,
            "ref": self.ref,
            "path": self.path,
        }
        if self.sparse is not None:
            result["sparse"] = self.sparse
        return result


@dataclass(frozen=True, slots=True)
class VendorMount:
    """Represents a mount point from vendor to project.

    Attributes:
        source_path: Path within vendor directory
        target_path: Path in project root
        mount_type: Either 'symlink' or 'copy'
    """

    source_path: str
    target_path: str
    mount_type: str = "symlink"  # 'symlink' or 'copy'

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "source_path": self.source_path,
            "target_path": self.target_path,
            "mount_type": self.mount_type,
        }


@dataclass(frozen=True, slots=True)
class SyncResult:
    """Result of a vendor sync operation.

    Attributes:
        vendor_name: Vendor name
        success: Whether sync succeeded
        commit: Resolved commit SHA (40 hex chars)
        previous_commit: Previous commit SHA before update
        changed: Whether the vendor changed
        error: Error message if failed
    """

    vendor_name: str
    success: bool
    commit: str | None = None
    previous_commit: str | None = None
    changed: bool = False
    error: str | None = None


@dataclass(frozen=True, slots=True)
class MountResult:
    """Result of a mount operation.

    Attributes:
        success: Whether mount succeeded
        path: Target path that was created
        would_create: In dry-run mode, whether it would create
        error: Error message if failed
    """

    success: bool
    path: str | None = None
    would_create: bool = False
    error: str | None = None


@dataclass(frozen=True, slots=True)
class GCResult:
    """Result of garbage collection operation.

    Attributes:
        removed_mirrors: List of removed mirror paths
        removed_checkouts: List of removed checkout paths
        bytes_freed: Bytes freed by cleanup
    """

    removed_mirrors: tuple[str, ...] = ()
    removed_checkouts: tuple[str, ...] = ()
    bytes_freed: int = 0


__all__ = [
    "VendorSource",
    "VendorMount",
    "SyncResult",
    "MountResult",
    "GCResult",
]
