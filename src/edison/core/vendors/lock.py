"""Vendor lock file management.

Provides deterministic lock file generation and parsing for
tracking resolved commit SHAs.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from edison.core.vendors.redaction import redact_url_credentials


@dataclass(frozen=True, slots=True)
class VendorLockEntry:
    """Entry in the vendor lock file.

    Attributes:
        name: Vendor name
        url: Repository URL
        ref: Original ref (branch/tag)
        commit: Resolved commit SHA
        path: Local checkout path
    """

    name: str
    url: str
    ref: str
    commit: str
    path: str

    def __post_init__(self) -> None:
        # Ensure lock entries never retain credential-bearing URLs in memory or on disk.
        object.__setattr__(self, "url", redact_url_credentials(self.url))

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "url": self.url,
            "ref": self.ref,
            "commit": self.commit,
            "path": self.path,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VendorLockEntry:
        """Create from dictionary."""
        required_keys = {"name", "url", "ref", "commit", "path"}
        missing = required_keys - set(data.keys())
        if missing:
            raise ValueError(f"Missing required keys: {sorted(missing)}")
        return cls(
            name=data["name"],
            url=data["url"],
            ref=data["ref"],
            commit=data["commit"],
            path=data["path"],
        )


class VendorLock:
    """Manages vendor lock file.

    Lock file is stored at .edison/config/vendors.lock.yaml
    and records resolved commit SHAs for deterministic builds.
    """

    def __init__(self, repo_root: Path) -> None:
        """Initialize vendor lock.

        Args:
            repo_root: Path to repository root
        """
        self.repo_root = repo_root
        self._entries: dict[str, VendorLockEntry] = {}

    @property
    def lock_path(self) -> Path:
        """Path to vendors.lock.yaml file."""
        return self.repo_root / ".edison" / "config" / "vendors.lock.yaml"

    def load(self) -> None:
        """Load existing lock file."""
        if not self.lock_path.exists():
            return

        content = self.lock_path.read_text(encoding="utf-8")
        data = yaml.safe_load(content) or {}

        vendors = data.get("vendors", [])
        for item in vendors:
            entry = VendorLockEntry.from_dict(item)
            self._entries[entry.name] = entry

    def add_entry(self, entry: VendorLockEntry) -> None:
        """Add or update a lock entry.

        Args:
            entry: Lock entry to add
        """
        self._entries[entry.name] = entry

    def get_entry(self, name: str) -> VendorLockEntry | None:
        """Get lock entry by vendor name.

        Args:
            name: Vendor name

        Returns:
            Lock entry if found, None otherwise
        """
        return self._entries.get(name)

    def get_entries(self) -> list[VendorLockEntry]:
        """Get all lock entries.

        Returns:
            List of all lock entries
        """
        return list(self._entries.values())

    def save(self) -> None:
        """Save lock file.

        Entries are sorted by name for deterministic output.
        """
        # Ensure directory exists
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)

        # Sort entries by name for deterministic output
        sorted_entries = sorted(self._entries.values(), key=lambda e: e.name)

        data = {
            "vendors": [entry.to_dict() for entry in sorted_entries],
        }

        content = yaml.dump(data, default_flow_style=False, sort_keys=False)
        self.lock_path.write_text(content, encoding="utf-8")


__all__ = ["VendorLock", "VendorLockEntry"]
