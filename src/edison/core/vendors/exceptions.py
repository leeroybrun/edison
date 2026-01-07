"""Vendor subsystem exceptions.

Provides custom exceptions for vendor operations to enable
proper error handling and user-friendly error messages.
"""
from __future__ import annotations

from edison.core.exceptions import EdisonError


class VendorError(EdisonError):
    """Base exception for vendor subsystem errors."""


class VendorConfigError(VendorError):
    """Raised when vendor configuration is invalid or missing required fields."""


class VendorSyncError(VendorError):
    """Raised when vendor sync operation fails."""


class VendorNotFoundError(VendorError):
    """Raised when a vendor is not found in configuration."""


class VendorLockError(VendorError):
    """Raised when lock file operations fail."""


class VendorCacheError(VendorError):
    """Raised when cache operations fail."""


class VendorCheckoutError(VendorError):
    """Raised when checkout/worktree operations fail."""


class VendorMountError(VendorError):
    """Raised when mount operations fail."""


__all__ = [
    "VendorError",
    "VendorConfigError",
    "VendorSyncError",
    "VendorNotFoundError",
    "VendorLockError",
    "VendorCacheError",
    "VendorCheckoutError",
    "VendorMountError",
]
