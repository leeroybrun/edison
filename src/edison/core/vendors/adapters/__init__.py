"""Vendor adapter interface and registry.

Adapters provide vendor-specific mount discovery logic.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from pathlib import Path
from typing import Protocol, runtime_checkable

from edison.core.vendors.models import VendorMount

logger = logging.getLogger(__name__)


@runtime_checkable
class VendorAdapter(Protocol):
    """Protocol for vendor adapters.

    Adapters discover mount points specific to a vendor type.
    """

    vendor_name: str

    def discover_mounts(self) -> list[VendorMount]:
        """Discover mount points for this vendor.

        Returns:
            List of mount configurations
        """
        ...


class BaseVendorAdapter(ABC):
    """Base class for vendor adapters."""

    vendor_name: str = ""

    def __init__(self, vendor_path: Path) -> None:
        """Initialize adapter.

        Args:
            vendor_path: Path to vendor checkout
        """
        self.vendor_path = vendor_path

    @abstractmethod
    def discover_mounts(self) -> list[VendorMount]:
        """Discover mount points for this vendor.

        Returns:
            List of mount configurations
        """
        ...


class GenericVendorAdapter(BaseVendorAdapter):
    """Generic adapter for unknown vendors.

    Returns empty mount list by default.
    """

    vendor_name = "generic"

    def discover_mounts(self) -> list[VendorMount]:
        """Return empty mount list for generic vendors."""
        return []


# Registry of vendor adapters
_ADAPTER_REGISTRY: dict[str, type[BaseVendorAdapter]] = {}


def register_adapter(adapter_class: type[BaseVendorAdapter]) -> None:
    """Register a vendor adapter.

    Args:
        adapter_class: Adapter class to register
    """
    raw_name = getattr(adapter_class, "vendor_name", "")
    name = raw_name.strip() if isinstance(raw_name, str) else ""
    if not name:
        raise ValueError(
            f"Cannot register adapter {adapter_class.__name__} with empty vendor_name"
        )
    _ADAPTER_REGISTRY[name] = adapter_class


def get_adapter_for_vendor(vendor_name: str) -> type[BaseVendorAdapter]:
    """Get adapter class for a vendor.

    Args:
        vendor_name: Name of the vendor

    Returns:
        Adapter class, or GenericVendorAdapter if not found
    """
    return _ADAPTER_REGISTRY.get(str(vendor_name or "").strip(), GenericVendorAdapter)


# Register built-in adapters
def _register_builtin_adapters() -> None:
    """Register built-in vendor adapters."""
    try:
        from edison.core.vendors.adapters.opencode import OpencodeAdapter

        register_adapter(OpencodeAdapter)
    except Exception as exc:
        logger.warning("Failed to register built-in OpencodeAdapter: %s", exc)


# Auto-register on import
_register_builtin_adapters()


__all__ = [
    "VendorAdapter",
    "BaseVendorAdapter",
    "GenericVendorAdapter",
    "register_adapter",
    "get_adapter_for_vendor",
]
