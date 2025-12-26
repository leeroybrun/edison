"""Zen MCP platform adapter.

This adapter is based on:
- adapters/sync/zen/client.py (ZenSync)
- adapters/sync/zen/composer.py (ZenComposerMixin)
- adapters/sync/zen/discovery.py (ZenDiscoveryMixin)
- adapters/sync/zen/sync.py (ZenSyncMixin)

Handles:
- Syncing Zen MCP prompts for different roles and models
- Role-specific guideline and rule discovery
- Workflow loop attachment
- CLI client verification
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from edison.core.adapters.base import PlatformAdapter
from edison.core.composition.registries.generic import GenericRegistry
from edison.core.rules import RulesRegistry

from .discovery import ZenDiscoveryMixin
from .composer import ZenComposerMixin
from .sync import ZenSyncMixin

if TYPE_CHECKING:
    from edison.core.config.domains.composition import AdapterConfig


class ZenAdapterError(RuntimeError):
    """Error in Zen adapter operations."""


class ZenAdapter(ZenDiscoveryMixin, ZenComposerMixin, ZenSyncMixin, PlatformAdapter):
    """Platform adapter for Zen MCP.

    This adapter:
    - Composes prompts for different Zen roles and models
    - Discovers role-specific guidelines and rules
    - Syncs prompts to Zen MCP directory structure
    - Manages workflow loop sections
    - Verifies CLI client configurations

    Inherits from:
    - ZenDiscoveryMixin: Role-specific guideline/rule discovery
    - ZenComposerMixin: Prompt composition for roles/models
    - ZenSyncMixin: Prompt syncing and verification
    - PlatformAdapter: Base adapter functionality
    """

    _zen_roles_config: Dict[str, Any]
    _role_config_validated: bool

    def __init__(
        self,
        project_root: Optional[Path] = None,
        adapter_config: Optional["AdapterConfig"] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize Zen adapter.

        Args:
            project_root: Project root directory.
            adapter_config: Adapter configuration from loader.
            config: Optional config override (merged with loaded config).
        """
        # Initialize PlatformAdapter
        super().__init__(project_root=project_root, adapter_config=adapter_config)

        # Merge any passed config with loaded config
        if config:
            from edison.core.config import ConfigManager
            self._cached_config = ConfigManager(self.project_root).deep_merge(
                self.config, config
            )

        # Initialize registries
        from edison.core.composition.registries.generic import GenericRegistry
        self.guideline_registry = GenericRegistry("guidelines", project_root=self.project_root)
        self.rules_registry = RulesRegistry(project_root=self.project_root)

        # Zen-specific state
        self._zen_roles_config = {}
        self._role_config_validated = False

    # =========================================================================
    # Platform Properties
    # =========================================================================

    @property
    def platform_name(self) -> str:
        """Return platform identifier."""
        return "zen"

    @property
    def zen_dir(self) -> Path:
        """Path to .zen/conf/ directory."""
        return self.get_output_path()

    # =========================================================================
    # Role Configuration
    # =========================================================================

    def _load_zen_roles_config(self) -> Dict[str, Any]:
        """Return raw zen.roles config as a mapping.

        Requires zen.roles to be a dict/mapping (no legacy list form).

        Returns:
            Zen roles configuration dictionary

        Raises:
            ValueError: If zen.roles is not a dict
        """
        if self._zen_roles_config:
            return self._zen_roles_config

        zen_cfg = self.config.get("zen") or {}
        roles_cfg = zen_cfg.get("roles") or {}
        if not isinstance(roles_cfg, dict):
            raise ValueError(
                f"zen.roles must be a mapping/dict, not {type(roles_cfg).__name__}. "
                "Legacy list form is no longer supported."
            )
        self._zen_roles_config = roles_cfg
        return self._zen_roles_config

    def _validate_role_config(self) -> None:
        """Lightweight structural validation for zen.roles config."""
        if self._role_config_validated:
            return

        roles_cfg = self._load_zen_roles_config()
        for role_name, spec in roles_cfg.items():
            if not isinstance(spec, dict):
                raise ValueError(
                    f"zen.roles.{role_name} must be a dict, not {type(spec).__name__}"
                )

        self._role_config_validated = True

    def _get_role_spec(self, role: str) -> Optional[Dict[str, Any]]:
        """Get role specification from config.

        Args:
            role: Role identifier

        Returns:
            Role specification dict, or None if not found
        """
        self._validate_role_config()
        roles_cfg = self._load_zen_roles_config()
        return roles_cfg.get(role)

    # =========================================================================
    # Sync Methods
    # =========================================================================

    def sync_all(self) -> Dict[str, Any]:
        """Execute complete synchronization workflow.

        Syncs prompts using configuration from CompositionConfig.

        Returns:
            Dictionary containing sync results.
        """
        result: Dict[str, Any] = {
            "prompts": [],
        }

        prompts: List[Path] = []

        # Sync agents + validators (if configured)
        for sync_name in ("agents", "validators", "prompts"):
            if self.is_sync_enabled(sync_name):
                prompts.extend(self.sync_from_config(sync_name))

        # Also produce generic model-level prompts (codex/claude/gemini) used by Zen CLI clients.
        zen_cfg = self.config.get("zen") or {}
        models = []
        if isinstance(zen_cfg, dict):
            raw_models = zen_cfg.get("prompt_models")
            if isinstance(raw_models, list):
                models = [str(m).strip() for m in raw_models if str(m).strip()]
        if not models:
            models = ["codex", "claude", "gemini"]

        for model in models:
            # Include all generic roles in the single `<model>.txt` file.
            out = self.sync_role_prompts(model=model, roles=["default", "codereviewer", "planner"])
            prompts.extend(sorted(set(out.values())))

        if prompts:
            # De-dupe and keep stable ordering for CLI output
            seen: set[Path] = set()
            unique: List[str] = []
            for p in prompts:
                if p in seen:
                    continue
                seen.add(p)
                unique.append(str(p))
            result["prompts"] = unique

        return result


__all__ = ["ZenAdapter", "ZenAdapterError"]
