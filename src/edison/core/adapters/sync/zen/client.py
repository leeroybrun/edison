from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any

from edison.core.utils.paths import PathResolver
from ....config import ConfigManager
from ....config.domains import PacksConfig
from ....composition import GuidelineRegistry
from ....rules import RulesRegistry

from .discovery import ZenDiscoveryMixin
from .composer import ZenComposerMixin
from .sync import ZenSyncMixin


@dataclass
class ZenSync(ZenDiscoveryMixin, ZenComposerMixin, ZenSyncMixin):
    """Full-featured adapter between Edison composition and Zen MCP prompts."""

    repo_root: Path
    config: Dict[str, Any]
    guideline_registry: GuidelineRegistry
    rules_registry: RulesRegistry
    _zen_roles_config: Dict[str, Any]
    _role_config_validated: bool

    def __init__(self, repo_root: Optional[Path] = None, config: Optional[Dict[str, Any]] = None) -> None:
        root = repo_root.resolve() if repo_root else PathResolver.resolve_project_root()
        cfg_mgr = ConfigManager(root)
        self.repo_root = root
        self.config = config or cfg_mgr.load_config(validate=False)
        self.guideline_registry = GuidelineRegistry(repo_root=root)
        self.rules_registry = RulesRegistry(project_root=root)
        self._zen_roles_config = {}
        self._role_config_validated = False

    # ------------------------------------------------------------------
    # Public API: role-aware discovery
    # ------------------------------------------------------------------
    @property
    def _packs_config(self) -> PacksConfig:
        """Lazy PacksConfig accessor."""
        return PacksConfig(repo_root=self.repo_root)

    def _active_packs(self) -> List[str]:
        """Get active packs via PacksConfig."""
        return self._packs_config.active_packs

    # ---------- Role configuration helpers ----------
    def _load_zen_roles_config(self) -> Dict[str, Any]:
        """Return raw zen.roles config as a mapping (or empty dict).

        Supports both legacy list form (ignored here) and new mapping form.
        """
        if self._zen_roles_config:
            return self._zen_roles_config

        zen_cfg = self.config.get("zen") or {}
        roles_cfg = zen_cfg.get("roles") or {}
        if isinstance(roles_cfg, dict):
            self._zen_roles_config = roles_cfg
        else:
            # Legacy form: list of model ids; no per-role config available.
            self._zen_roles_config = {}
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
