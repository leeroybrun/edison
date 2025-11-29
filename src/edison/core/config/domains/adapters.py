"""Domain-specific configuration for adapter paths.

Provides cached access to adapter-specific paths and settings.
All paths come from composition.yaml - NO hardcoded defaults.
"""
from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Optional

from ..base import BaseDomainConfig
from edison.data import get_data_path


class AdaptersConfig(BaseDomainConfig):
    """Domain-specific configuration accessor for adapter paths.

    Provides typed, cached access to adapter configuration including:
    - Client output paths (.claude, .cursor, .zen, etc.)
    - Sync paths for agents, validators, prompts
    - Template paths

    All configuration comes from composition.yaml outputs section.
    NO hardcoded fallback defaults - config MUST exist.

    Extends BaseDomainConfig for consistent caching and repo_root handling.

    Usage:
        adapters = AdaptersConfig(repo_root=Path("/path/to/project"))
        claude_dir = adapters.get_client_path("claude")
        agents_path = adapters.get_sync_path("claude", "agents_path")
    """

    def _config_section(self) -> str:
        return "composition"

    def _load_composition_yaml(self) -> dict:
        """Load composition.yaml with outputs configuration."""
        composition_yaml_path = get_data_path("config") / "composition.yaml"
        if not composition_yaml_path.exists():
            raise FileNotFoundError(
                f"composition.yaml not found at {composition_yaml_path}. "
                "This file is required for adapter configuration."
            )

        from ..manager import ConfigManager
        mgr = ConfigManager(self._repo_root)
        return mgr.load_yaml(composition_yaml_path)

    @cached_property
    def outputs(self) -> dict:
        """Get outputs configuration from composition.yaml.

        Returns:
            Dict with outputs configuration including clients and sync settings.
        """
        config = self._load_composition_yaml()
        outputs = config.get("outputs", {})
        if not outputs:
            raise ValueError(
                "outputs section missing from composition.yaml. "
                "This section is required for adapter paths."
            )
        return outputs

    def get_client_config(self, client_name: str) -> Optional[dict]:
        """Get client configuration by name.

        Args:
            client_name: Client name (e.g., "claude", "cursor", "zen")

        Returns:
            Client config dict or None if not found.
        """
        clients = self.outputs.get("clients", {})
        return clients.get(client_name)

    def get_client_path(self, client_name: str) -> Path:
        """Get client output directory path.

        Args:
            client_name: Client name (e.g., "claude", "cursor", "zen")

        Returns:
            Absolute path to client output directory.

        Raises:
            ValueError: If client not configured or output_path missing.
        """
        client_cfg = self.get_client_config(client_name)
        if not client_cfg:
            raise ValueError(
                f"Client '{client_name}' not configured in composition.yaml outputs.clients"
            )

        output_path = client_cfg.get("output_path")
        if not output_path:
            raise ValueError(
                f"output_path missing for client '{client_name}' in composition.yaml"
            )

        # Resolve relative to repo root
        path = Path(output_path)
        if not path.is_absolute():
            path = self._repo_root / path

        return path

    def get_sync_config(self, client_name: str) -> Optional[dict]:
        """Get sync configuration for a client.

        Args:
            client_name: Client name (e.g., "claude", "zen")

        Returns:
            Sync config dict or None if not found.
        """
        sync = self.outputs.get("sync", {})
        return sync.get(client_name)

    def get_sync_path(self, client_name: str, path_key: str) -> Optional[Path]:
        """Get sync path for a client.

        Args:
            client_name: Client name (e.g., "claude", "zen")
            path_key: Path key (e.g., "agents_path", "prompts_path")

        Returns:
            Absolute path if configured, None otherwise.
        """
        sync_cfg = self.get_sync_config(client_name)
        if not sync_cfg:
            return None

        path_str = sync_cfg.get(path_key)
        if not path_str:
            return None

        # Resolve relative to repo root
        path = Path(path_str)
        if not path.is_absolute():
            path = self._repo_root / path

        return path

    def get_template_path(self, client_name: str, relative_template: str) -> Path:
        """Get template path for a client.

        Args:
            client_name: Client name (e.g., "claude", "zen")
            relative_template: Relative path to template (e.g., "workflow-loop.txt")

        Returns:
            Absolute path to template file.
        """
        client_dir = self.get_client_path(client_name)
        return client_dir / "templates" / relative_template

    def is_client_enabled(self, client_name: str) -> bool:
        """Check if a client is enabled.

        Args:
            client_name: Client name (e.g., "claude", "cursor", "zen")

        Returns:
            True if client is enabled, False otherwise.
        """
        client_cfg = self.get_client_config(client_name)
        if not client_cfg:
            return False
        return bool(client_cfg.get("enabled", False))

    def is_sync_enabled(self, client_name: str) -> bool:
        """Check if sync is enabled for a client.

        Args:
            client_name: Client name (e.g., "claude", "zen")

        Returns:
            True if sync is enabled, False otherwise.
        """
        sync_cfg = self.get_sync_config(client_name)
        if not sync_cfg:
            return False
        return bool(sync_cfg.get("enabled", False))


__all__ = ["AdaptersConfig"]
