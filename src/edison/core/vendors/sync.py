"""Vendor sync manager.

High-level orchestration of vendor sync, update, and lock operations.
"""
from __future__ import annotations

from pathlib import Path

from edison.core.vendors.checkout import VendorCheckout
from edison.core.vendors.config import VendorConfig
from edison.core.vendors.exceptions import VendorNotFoundError
from edison.core.vendors.lock import VendorLock, VendorLockEntry
from edison.core.vendors.models import SyncResult, VendorSource


class VendorSyncManager:
    """Manages vendor synchronization operations.

    Coordinates config loading, checkout operations, and lock file updates.
    """

    def __init__(self, repo_root: Path) -> None:
        """Initialize sync manager.

        Args:
            repo_root: Path to repository root
        """
        self.repo_root = repo_root
        self.config = VendorConfig(repo_root)
        self.lock = VendorLock(repo_root)

    def sync_all(self, *, force: bool = False) -> list[SyncResult]:
        """Sync all configured vendors.

        Args:
            force: Force sync even if already at correct commit

        Returns:
            List of sync results for each vendor
        """
        sources = self.config.get_sources()
        cache_dir = self.config.get_cache_dir()
        checkout = VendorCheckout(self.repo_root, cache_dir)

        # Load existing lock entries
        self.lock.load()

        results: list[SyncResult] = []
        for source in sources:
            previous_entry = self.lock.get_entry(source.name)
            previous_commit = previous_entry.commit if previous_entry else None

            result = checkout.sync(source, force=force)
            # Enrich result with previous commit and changed flag
            changed = result.commit != previous_commit if result.commit else False
            enriched = SyncResult(
                vendor_name=result.vendor_name,
                success=result.success,
                commit=result.commit,
                previous_commit=previous_commit,
                changed=changed,
                error=result.error,
            )
            results.append(enriched)

            # Update lock file on success
            if result.success and result.commit:
                self.lock.add_entry(
                    VendorLockEntry(
                        name=source.name,
                        url=source.url,
                        ref=source.ref,
                        commit=result.commit,
                        path=source.path,
                    )
                )
                # Persist lock entry immediately so partial progress is not lost if the run is interrupted.
                self.lock.save()

        return results

    def sync_vendor(self, name: str, *, force: bool = False) -> SyncResult:
        """Sync a single vendor by name.

        Args:
            name: Vendor name to sync
            force: Force sync even if already at correct commit

        Returns:
            Sync result

        Raises:
            VendorNotFoundError: If vendor not found in config
        """
        source = self.config.get_source_by_name(name)
        if source is None:
            raise VendorNotFoundError(f"Vendor not found: {name}")

        cache_dir = self.config.get_cache_dir()
        checkout = VendorCheckout(self.repo_root, cache_dir)

        # Load existing lock entries
        self.lock.load()
        previous_entry = self.lock.get_entry(name)
        previous_commit = previous_entry.commit if previous_entry else None

        result = checkout.sync(source, force=force)

        # Enrich result with previous commit and changed flag
        changed = result.commit != previous_commit if result.commit else False
        enriched = SyncResult(
            vendor_name=result.vendor_name,
            success=result.success,
            commit=result.commit,
            previous_commit=previous_commit,
            changed=changed,
            error=result.error,
        )

        # Update lock file on success
        if result.success and result.commit:
            self.lock.add_entry(
                VendorLockEntry(
                    name=source.name,
                    url=source.url,
                    ref=source.ref,
                    commit=result.commit,
                    path=source.path,
                )
            )
            self.lock.save()

        return enriched

    def update_all(self) -> list[SyncResult]:
        """Update all vendors (fetch latest and re-checkout).

        Same as sync_all but explicitly fetches latest from remote.

        Returns:
            List of sync results for each vendor
        """
        # Update always forces a fresh fetch
        return self.sync_all(force=True)

    def update_vendor(self, name: str, *, ref: str | None = None) -> SyncResult:
        """Update a single vendor.

        Args:
            name: Vendor name to update
            ref: Optional ref override (branch/tag/commit)

        Returns:
            Sync result
        """
        source = self.config.get_source_by_name(name)
        if source is None:
            raise VendorNotFoundError(f"Vendor not found: {name}")

        # If ref override provided, create new source with that ref
        if ref:
            source = VendorSource(
                name=source.name,
                url=source.url,
                ref=ref,
                path=source.path,
                sparse=source.sparse,
            )

        cache_dir = self.config.get_cache_dir()
        checkout = VendorCheckout(self.repo_root, cache_dir)

        # Load existing lock entries
        self.lock.load()
        previous_entry = self.lock.get_entry(name)
        previous_commit = previous_entry.commit if previous_entry else None

        result = checkout.sync(source, force=True)

        # Enrich result with previous commit and changed flag
        changed = result.commit != previous_commit if result.commit else False
        enriched = SyncResult(
            vendor_name=result.vendor_name,
            success=result.success,
            commit=result.commit,
            previous_commit=previous_commit,
            changed=changed,
            error=result.error,
        )

        # Update lock file on success
        if result.success and result.commit:
            self.lock.add_entry(
                VendorLockEntry(
                    name=source.name,
                    url=source.url,
                    ref=source.ref,
                    commit=result.commit,
                    path=source.path,
                )
            )
            self.lock.save()

        return enriched


__all__ = ["VendorSyncManager"]
