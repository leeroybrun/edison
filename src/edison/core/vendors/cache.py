"""Vendor mirror cache management.

Manages shared bare git repositories that serve as local mirrors
for vendor sources. This enables efficient fetching and reduces
network usage across multiple checkouts.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path


class VendorMirrorCache:
    """Manages bare git repository mirrors for vendor sources.

    Uses content-addressable storage based on URL hashes to
    enable sharing mirrors across projects.
    """

    def __init__(self, cache_dir: Path) -> None:
        """Initialize mirror cache.

        Args:
            cache_dir: Directory for storing mirror repositories
        """
        self.cache_dir = cache_dir

    def get_mirror_path(self, url: str) -> Path:
        """Get path to mirror repository for a URL.

        Uses SHA256 hash of URL to create deterministic,
        filesystem-safe path.

        Args:
            url: Git repository URL

        Returns:
            Path to bare mirror repository
        """
        # Create deterministic hash from URL
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]

        # Extract repo name for readability
        normalized = url.rstrip("/")
        # Support SSH scp-style URLs like git@github.com:user/repo.git.
        if "://" not in normalized and ":" in normalized and "@" in normalized:
            normalized = normalized.rsplit(":", 1)[-1]
        name = normalized.split("/")[-1]
        if name.endswith(".git"):
            name = name[:-4]

        # Ensure filesystem-safe name (no path separators).
        for sep in ("/", os.sep, os.altsep or ""):
            if sep:
                name = name.replace(sep, "_")

        if not name:
            name = "mirror"

        # Combine for unique, readable path
        mirror_name = f"{name}-{url_hash}.git"

        return self.cache_dir / mirror_name

    def mirror_exists(self, url: str) -> bool:
        """Check if mirror exists for URL.

        Args:
            url: Git repository URL

        Returns:
            True if mirror exists and is valid
        """
        mirror_path = self.get_mirror_path(url)
        return mirror_path.exists() and (mirror_path / "HEAD").exists()

    def ensure_cache_dir(self) -> None:
        """Ensure cache directory exists."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)


__all__ = ["VendorMirrorCache"]
