"""Zen MCP sync client.

Full-featured adapter between Edison composition and Zen MCP prompts.
Inherits from SyncAdapter for unified config loading.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base import SyncAdapter
from ....composition import GuidelineRegistry
from ....composition.output.writer import CompositionFileWriter
from ....rules import RulesRegistry

from .discovery import ZenDiscoveryMixin
from .composer import ZenComposerMixin
from .sync import ZenSyncMixin


class ZenSync(ZenDiscoveryMixin, ZenComposerMixin, ZenSyncMixin, SyncAdapter):
    """Full-featured adapter between Edison composition and Zen MCP prompts.

    Inherits from SyncAdapter which provides:
    - repo_root resolution via PathResolver
    - config property via ConfigMixin
    - active_packs property via ConfigMixin
    - packs_config property via ConfigMixin
    """

    _zen_roles_config: Dict[str, Any]
    _role_config_validated: bool

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        # Initialize SyncAdapter (handles repo_root, config via ConfigMixin)
        super().__init__(repo_root=repo_root)

        # Merge any passed config with loaded config
        if config:
            from edison.core.config import ConfigManager
            self._cached_config = ConfigManager(self.repo_root).deep_merge(
                self.config, config
            )

        # Initialize registries
        self.guideline_registry = GuidelineRegistry(repo_root=self.repo_root)
        self.rules_registry = RulesRegistry(project_root=self.repo_root)

        # Zen-specific state
        self._zen_roles_config = {}
        self._role_config_validated = False

        # Lazy writer initialization
        self._writer: Optional[CompositionFileWriter] = None

    @property
    def writer(self) -> CompositionFileWriter:
        """Lazy-initialized file writer for composition outputs."""
        if self._writer is None:
            self._writer = CompositionFileWriter(base_dir=self.repo_root)
        return self._writer

    # ------------------------------------------------------------------
    # Public API: role-aware discovery
    # ------------------------------------------------------------------
    def _get_active_packs(self) -> List[str]:
        """Get active packs via ConfigMixin."""
        return self.active_packs

    # Alias for backward compatibility with mixins
    def _active_packs(self) -> List[str]:
        """Get active packs via ConfigMixin."""
        return self.active_packs

    # ---------- Role configuration helpers ----------
    def _load_zen_roles_config(self) -> Dict[str, Any]:
        """Return raw zen.roles config as a mapping.

        Requires zen.roles to be a dict/mapping (no legacy list form).
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
                raise ValueError(f"zen.roles.{role_name} must be a mapping")
            for key in ("guidelines", "rules", "packs"):
                if key in spec and not isinstance(spec[key], list):
                    raise ValueError(f"zen.roles.{role_name}.{key} must be a list when present")
        self._role_config_validated = True

    def _get_role_spec(self, role: str) -> Optional[Dict[str, Any]]:
        """Fetch config spec for a role (case-insensitive).

        Supports both concrete project roles (e.g. ``project-api-builder``)
        and their generic counterparts (e.g. ``api-builder``) via
        delegation.roleMapping.
        """
        roles_cfg = self._load_zen_roles_config()
        if not roles_cfg:
            return None

        self._validate_role_config()

        # Case-insensitive lookup by exact key match.
        lowered: Dict[str, str] = {k.lower(): k for k in roles_cfg.keys()}
        key = (role or "").strip().lower()

        # Direct hit
        if key in lowered:
            return roles_cfg[lowered[key]]

        # For project-prefixed roles, also try generic name via delegation.roleMapping
        delegation_cfg = self.config.get("delegation") or {}
        role_mapping: Dict[str, str] = (delegation_cfg.get("roleMapping") or {})  # type: ignore[assignment]

        if key.startswith("project-"):
            concrete = key
            inverse_map: Dict[str, str] = {v.lower(): k for k, v in role_mapping.items()}
            generic = inverse_map.get(concrete)
            if generic and generic in lowered:
                return roles_cfg[lowered[generic]]

        return None

    def sync_all(self) -> Dict[str, Any]:
        """Execute complete synchronization workflow.

        Syncs role prompts for all discovered roles and models.

        Returns:
            Dictionary containing sync results.
        """
        result: Dict[str, Any] = {
            "prompts": {},
            "verification": {},
        }

        # Verify and sync CLI prompts
        verification = self.verify_cli_prompts(sync=True)
        result["verification"] = verification

        return result
