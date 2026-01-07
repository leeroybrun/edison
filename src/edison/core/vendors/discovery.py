"""Vendor mount discovery.

High-level interface for discovering mount points from all vendors.
"""
from __future__ import annotations

from pathlib import Path

from edison.core.vendors.adapters import get_adapter_for_vendor
from edison.core.vendors.config import VendorConfig
from edison.core.vendors.exceptions import VendorNotFoundError
from edison.core.vendors.models import VendorMount


class VendorMountDiscovery:
    """Discovers mount points from configured vendors."""

    def __init__(self, repo_root: Path) -> None:
        """Initialize mount discovery.

        Args:
            repo_root: Path to repository root
        """
        self.repo_root = repo_root
        self.config = VendorConfig(repo_root)

    def discover_all(self) -> list[VendorMount]:
        """Discover mounts from all configured vendors.

        Returns:
            Combined list of mounts from all vendors
        """
        mounts: list[VendorMount] = []

        for source in self.config.get_sources():
            vendor_path = self.repo_root / source.path
            if not vendor_path.exists():
                continue

            adapter_class = get_adapter_for_vendor(source.name)
            adapter = adapter_class(vendor_path=vendor_path)
            mounts.extend(adapter.discover_mounts())

        return mounts

    def discover_for_vendor(self, name: str) -> list[VendorMount]:
        """Discover mounts for a specific vendor.

        Args:
            name: Vendor name

        Returns:
            List of mounts for the vendor

        Raises:
            VendorNotFoundError: If vendor not found
        """
        source = self.config.get_source_by_name(name)
        if source is None:
            raise VendorNotFoundError(f"Vendor not found: {name}")

        vendor_path = self.repo_root / source.path
        if not vendor_path.exists():
            return []

        adapter_class = get_adapter_for_vendor(name)
        adapter = adapter_class(vendor_path=vendor_path)
        return adapter.discover_mounts()


__all__ = ["VendorMountDiscovery"]
