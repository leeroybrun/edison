"""Vendor garbage collection.

Cleans up orphaned cache entries that are no longer
referenced by any vendor configuration.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from edison.core.vendors.cache import VendorMirrorCache
from edison.core.vendors.config import VendorConfig
from edison.core.vendors.models import GCResult


class VendorGarbageCollector:
    """Cleans up unreferenced vendor cache entries."""

    def __init__(self, repo_root: Path) -> None:
        """Initialize garbage collector.

        Args:
            repo_root: Path to repository root
        """
        self.repo_root = repo_root
        self.config = VendorConfig(repo_root)

    def collect(
        self,
        *,
        dry_run: bool = False,
        clean_all: bool = False,
    ) -> GCResult:
        """Run garbage collection.

        Args:
            dry_run: If True, report what would be removed without deleting
            clean_all: If True, remove all caches including active ones

        Returns:
            GCResult with removal statistics
        """
        cache_dir = self.config.get_cache_dir()
        if not cache_dir.exists():
            return GCResult()

        cache_dir_resolved = cache_dir.resolve()

        # Get URLs of all configured vendors
        sources = self.config.get_sources()
        cache = VendorMirrorCache(cache_dir)

        if clean_all:
            # Clean all mirrors
            referenced_paths: set[Path] = set()
        else:
            # Only clean unreferenced mirrors
            referenced_paths = {cache.get_mirror_path(s.url) for s in sources}

        # Find mirrors to remove
        mirrors_to_remove: list[Path] = []
        for path in cache_dir.iterdir():
            if path.is_symlink():
                continue
            if path.suffix == ".git" and path.is_dir() and (path / "HEAD").exists():
                if path not in referenced_paths:
                    mirrors_to_remove.append(path)

        # Find checkouts to remove (vendors/ directory)
        checkouts_to_remove: list[Path] = []
        vendor_base = self.repo_root / "vendors"
        vendor_base_resolved = vendor_base.resolve()
        if vendor_base.exists() and not vendor_base.is_symlink():
            configured_paths = {self.repo_root / s.path for s in sources}
            for path in vendor_base.iterdir():
                if path.is_symlink():
                    continue
                if path.is_dir() and path.resolve().is_relative_to(vendor_base_resolved):
                    if clean_all or path not in configured_paths:
                        checkouts_to_remove.append(path)

        if dry_run:
            bytes_estimate = self._estimate_size(mirrors_to_remove + checkouts_to_remove)
            return GCResult(
                removed_mirrors=tuple(str(p) for p in mirrors_to_remove),
                removed_checkouts=tuple(str(p) for p in checkouts_to_remove),
                bytes_freed=bytes_estimate,
            )

        # Remove orphaned caches
        removed_mirrors: list[str] = []
        removed_checkouts: list[str] = []
        bytes_freed = 0

        for path in mirrors_to_remove:
            try:
                bytes_freed += self._get_dir_size(path)
                if not path.resolve().is_relative_to(cache_dir_resolved):
                    continue
                shutil.rmtree(path)
                removed_mirrors.append(str(path))
            except OSError:
                pass  # Skip if removal fails

        for path in checkouts_to_remove:
            try:
                if not path.resolve().is_relative_to(vendor_base_resolved):
                    continue
                bytes_freed += self._get_dir_size(path)
                shutil.rmtree(path)
                removed_checkouts.append(str(path))
            except OSError:
                pass  # Skip if removal fails

        return GCResult(
            removed_mirrors=tuple(removed_mirrors),
            removed_checkouts=tuple(removed_checkouts),
            bytes_freed=bytes_freed,
        )

    def _get_dir_size(self, path: Path) -> int:
        """Get total size of directory in bytes.

        Args:
            path: Directory path

        Returns:
            Size in bytes
        """
        total = 0
        try:
            for entry in path.rglob("*"):
                if entry.is_file():
                    try:
                        total += entry.stat().st_size
                    except OSError:
                        pass
        except OSError:
            pass
        return total

    def _estimate_size(self, paths: list[Path]) -> int:
        """Estimate total size of paths.

        Args:
            paths: List of paths to measure

        Returns:
            Estimated size in bytes
        """
        total = 0
        for path in paths:
            total += self._get_dir_size(path)
        return total


__all__ = ["VendorGarbageCollector"]
