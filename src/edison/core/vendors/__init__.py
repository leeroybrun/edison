"""Edison vendor subsystem.

Provides management of external vendor sources (git repositories)
that can be synced and mounted into projects.

Key components:
- VendorConfig: Load vendor configuration from .edison/config/vendors.yaml
- VendorLock: Manage deterministic lock file with resolved commits
- VendorSyncManager: Orchestrate sync/update operations
- VendorMountDiscovery: Discover mount points from vendor adapters
"""
from __future__ import annotations

from edison.core.vendors.config import VendorConfig
from edison.core.vendors.discovery import VendorMountDiscovery
from edison.core.vendors.exceptions import (
    VendorCacheError,
    VendorCheckoutError,
    VendorConfigError,
    VendorError,
    VendorLockError,
    VendorMountError,
    VendorNotFoundError,
    VendorSyncError,
)
from edison.core.vendors.lock import VendorLock, VendorLockEntry
from edison.core.vendors.models import (
    GCResult,
    MountResult,
    SyncResult,
    VendorMount,
    VendorSource,
)
from edison.core.vendors.sync import VendorSyncManager

__all__ = [
    # Config
    "VendorConfig",
    # Lock
    "VendorLock",
    "VendorLockEntry",
    # Sync
    "VendorSyncManager",
    # Discovery
    "VendorMountDiscovery",
    # Models
    "VendorSource",
    "VendorMount",
    "SyncResult",
    "MountResult",
    "GCResult",
    # Exceptions
    "VendorError",
    "VendorConfigError",
    "VendorSyncError",
    "VendorNotFoundError",
    "VendorLockError",
    "VendorCacheError",
    "VendorCheckoutError",
    "VendorMountError",
]
