"""OpenCode vendor adapter.

Provides mount discovery for the OpenCode project.
"""
from __future__ import annotations

from edison.core.vendors.adapters import BaseVendorAdapter
from edison.core.vendors.models import VendorMount


class OpencodeAdapter(BaseVendorAdapter):
    """Adapter for OpenCode vendor.

    Discovers standard mount points for OpenCode:
    - prompts/ -> .codex/prompts/vendor/
    - config/ -> .opencode/vendor-config/
    """

    vendor_name = "opencode"

    def discover_mounts(self) -> list[VendorMount]:
        """Discover OpenCode mount points.

        Returns:
            List of mount configurations
        """
        mounts: list[VendorMount] = []

        # Check for prompts directory
        prompts_dir = self.vendor_path / "prompts"
        if prompts_dir.exists() and prompts_dir.is_dir():
            mounts.append(
                VendorMount(
                    source_path="prompts/",
                    target_path=".codex/prompts/vendor/",
                    mount_type="symlink",
                )
            )

        # Check for config directory
        config_dir = self.vendor_path / "config"
        if config_dir.exists() and config_dir.is_dir():
            mounts.append(
                VendorMount(
                    source_path="config/",
                    target_path=".opencode/vendor-config/",
                    mount_type="symlink",
                )
            )

        return mounts


__all__ = ["OpencodeAdapter"]
