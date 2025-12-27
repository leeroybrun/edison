"""Pal MCP platform adapter.

Handles:
- Syncing Pal MCP prompts for different roles and models
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

from .discovery import PalDiscoveryMixin
from .composer import PalComposerMixin
from .sync import PalSyncMixin

if TYPE_CHECKING:
    from edison.core.config.domains.composition import AdapterConfig


class PalAdapterError(RuntimeError):
    """Error in Pal adapter operations."""


class PalAdapter(PalDiscoveryMixin, PalComposerMixin, PalSyncMixin, PlatformAdapter):
    """Platform adapter for Pal MCP.

    This adapter:
    - Composes prompts for different Pal roles and models
    - Discovers role-specific guidelines and rules
    - Syncs prompts to Pal MCP directory structure
    - Manages workflow loop sections
    - Verifies CLI client configurations

    Inherits from:
    - PalDiscoveryMixin: Role-specific guideline/rule discovery
    - PalComposerMixin: Prompt composition for roles/models
    - PalSyncMixin: Prompt syncing and verification
    - PlatformAdapter: Base adapter functionality
    """

    _pal_roles_config: Dict[str, Any]
    _role_config_validated: bool

    def __init__(
        self,
        project_root: Optional[Path] = None,
        adapter_config: Optional["AdapterConfig"] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize Pal adapter.

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

        # Pal-specific state
        self._pal_roles_config = {}
        self._role_config_validated = False

    # =========================================================================
    # Platform Properties
    # =========================================================================

    @property
    def platform_name(self) -> str:
        """Return platform identifier."""
        return "pal"

    @property
    def pal_conf_dir(self) -> Path:
        """Path to .pal/conf/ directory."""
        return self.get_output_path()

    # =========================================================================
    # Role Configuration
    # =========================================================================

    def _load_pal_roles_config(self) -> Dict[str, Any]:
        """Return raw pal.roles config as a mapping.

        Requires pal.roles to be a dict/mapping (no legacy list form).

        Returns:
            Pal roles configuration dictionary

        Raises:
            ValueError: If pal.roles is not a dict
        """
        if self._pal_roles_config:
            return self._pal_roles_config

        pal_cfg = self.config.get("pal") or {}
        roles_cfg = pal_cfg.get("roles") or {}
        if not isinstance(roles_cfg, dict):
            raise ValueError(
                f"pal.roles must be a mapping/dict, not {type(roles_cfg).__name__}. "
                "Legacy list form is no longer supported."
            )
        self._pal_roles_config = roles_cfg
        return self._pal_roles_config

    def _validate_role_config(self) -> None:
        """Lightweight structural validation for pal.roles config."""
        if self._role_config_validated:
            return

        roles_cfg = self._load_pal_roles_config()
        for role_name, spec in roles_cfg.items():
            if not isinstance(spec, dict):
                raise ValueError(
                    f"pal.roles.{role_name} must be a dict, not {type(spec).__name__}"
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
        roles_cfg = self._load_pal_roles_config()
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
        result: Dict[str, Any] = {"prompts": [], "cli_clients": []}

        prompts: List[Path] = []
        synced_agents: List[Path] = []
        synced_validators: List[Path] = []

        # Sync agents + validators (if configured)
        if self.is_sync_enabled("agents"):
            synced_agents = self.sync_from_config("agents")
            prompts.extend(synced_agents)
        if self.is_sync_enabled("validators"):
            synced_validators = self.sync_from_config("validators")
            prompts.extend(synced_validators)

            # If validator prompt filenames include the configured validator prefix (e.g. `validator-*.txt`),
            # delete legacy unprefixed prompt files (e.g. `security.txt`) to avoid ambiguity.
            pal_cfg = self.config.get("pal") or {}
            cli_cfg = (pal_cfg.get("cli_clients") or {}) if isinstance(pal_cfg, dict) else {}
            roles_spec = (cli_cfg.get("roles") or {}) if isinstance(cli_cfg, dict) else {}
            prefixes = (roles_spec.get("prefixes") or {}) if isinstance(roles_spec, dict) else {}
            validator_prefix = str(prefixes.get("validator") or "").strip()
            if not validator_prefix:
                raise ValueError("pal.cli_clients.roles.prefixes.validator must be configured (non-empty).")
            for p in synced_validators:
                try:
                    if p.is_file() and p.name.startswith(validator_prefix) and p.suffix == ".txt":
                        legacy = p.parent / p.name[len(validator_prefix) :]
                        if legacy.exists() and legacy.is_file():
                            legacy.unlink()
                except Exception:
                    # Best-effort cleanup; never fail sync due to deletion issues.
                    pass
        if self.is_sync_enabled("prompts"):
            prompts.extend(self.sync_from_config("prompts"))

        # Clean up legacy unprefixed agent prompt files (e.g. `api-builder.txt`) when the
        # new prefixed form exists (e.g. `agent-api-builder.txt`).
        pal_cfg = self.config.get("pal") or {}
        cli_cfg = (pal_cfg.get("cli_clients") or {}) if isinstance(pal_cfg, dict) else {}
        roles_spec = (cli_cfg.get("roles") or {}) if isinstance(cli_cfg, dict) else {}
        prefixes = (roles_spec.get("prefixes") or {}) if isinstance(roles_spec, dict) else {}
        agent_prefix = str(prefixes.get("agent") or "").strip()
        if not agent_prefix:
            raise ValueError("pal.cli_clients.roles.prefixes.agent must be configured (non-empty).")
        for p in synced_agents:
            try:
                if p.is_file() and p.name.startswith(agent_prefix) and p.suffix == ".txt":
                    legacy = p.parent / p.name[len(agent_prefix) :]
                    if legacy.exists() and legacy.is_file():
                        legacy.unlink()
            except Exception:
                # Best-effort cleanup; never fail sync due to deletion issues.
                pass

        # Produce shared Pal builtin prompts (default/planner/codereviewer).
        pal_cfg = self.config.get("pal") or {}
        base_model = None
        if isinstance(pal_cfg, dict):
            base_model = pal_cfg.get("prompt_base_model")
        if not isinstance(base_model, str) or not base_model.strip():
            raise ValueError("pal.prompt_base_model must be configured (non-empty string).")

        builtin_roles = ["default", "codereviewer", "planner"]
        out = self.sync_role_prompts(model=base_model.strip(), roles=builtin_roles)
        prompts.extend(sorted(set(out.values())))

        # Clean up legacy per-client builtin prompt files (e.g. `codex_default.txt`) now that
        # builtin prompts are shared (`default.txt`, `planner.txt`, `codereviewer.txt`).
        try:
            prompts_dir = next(iter(out.values())).parent if out else None
            if prompts_dir is not None:
                clients = []
                if isinstance(cli_cfg, dict):
                    raw_clients = cli_cfg.get("clients") or {}
                    if isinstance(raw_clients, dict):
                        clients = [str(k).strip() for k in raw_clients.keys() if str(k).strip()]
                for client in clients:
                    legacy_model_prompt = prompts_dir / f"{client}.txt"
                    if legacy_model_prompt.exists() and legacy_model_prompt.is_file():
                        legacy_model_prompt.unlink()
                    for r in builtin_roles:
                        legacy = prompts_dir / f"{client}_{r}.txt"
                        if legacy.exists() and legacy.is_file():
                            legacy.unlink()
        except Exception:
            # Best-effort cleanup only.
            pass

        # Generate Pal clink CLI client config files so Pal can discover our roles.
        pal_cfg = self.config.get("pal") or {}
        cli_cfg = (pal_cfg.get("cli_clients") or {}) if isinstance(pal_cfg, dict) else {}
        if isinstance(cli_cfg, dict) and bool(cli_cfg.get("enabled", True)):
            clients_spec = cli_cfg.get("clients") or {}
            roles_spec = cli_cfg.get("roles") or {}

            # Output directory is `<project>/.pal/conf/cli_clients` because adapter output_path is `.pal/conf`.
            cli_clients_dir = self.get_output_path() / "cli_clients"
            cli_clients_dir.mkdir(parents=True, exist_ok=True)

            prefixes = (roles_spec.get("prefixes") or {}) if isinstance(roles_spec, dict) else {}
            agent_prefix = str(prefixes.get("agent") or "").strip()
            validator_prefix = str(prefixes.get("validator") or "").strip()
            if not agent_prefix:
                raise ValueError("pal.cli_clients.roles.prefixes.agent must be configured (non-empty).")
            if not validator_prefix:
                raise ValueError("pal.cli_clients.roles.prefixes.validator must be configured (non-empty).")
            include_agents = bool(roles_spec.get("include_generated_agents", True))
            include_validators = bool(roles_spec.get("include_generated_validators", True))
            configured_builtin_roles = roles_spec.get("builtin")
            if isinstance(configured_builtin_roles, list) and configured_builtin_roles:
                builtin_roles = [str(r) for r in configured_builtin_roles if str(r).strip()]

            agent_roles: List[tuple[str, str]] = []
            if include_agents:
                for p in synced_agents:
                    if not p.stem.startswith(agent_prefix):
                        raise ValueError(
                            f"Generated agent prompt '{p.name}' must be prefixed with '{agent_prefix}'. "
                            "Update pal adapter filename_pattern to include the agent prefix."
                        )
                    agent_roles.append((p.stem, f"../systemprompts/clink/project/{p.name}"))

            validator_roles: List[tuple[str, str]] = []
            if include_validators:
                for p in synced_validators:
                    if not p.stem.startswith(validator_prefix):
                        raise ValueError(
                            f"Generated validator prompt '{p.name}' must be prefixed with '{validator_prefix}'. "
                            "Update pal adapter filename_pattern to include the validator prefix."
                        )
                    validator_roles.append((p.stem, f"../systemprompts/clink/project/{p.name}"))

            if isinstance(clients_spec, dict):
                for client_name, spec in clients_spec.items():
                    if not isinstance(spec, dict):
                        continue
                    command = str(spec.get("command") or "").strip()
                    if not command:
                        continue
                    additional_args = spec.get("additional_args") or []
                    env = spec.get("env") or {}

                    roles: Dict[str, Any] = {}
                    # Builtin roles map to Edison-generated shared prompt files `<role>.txt`.
                    for r in builtin_roles:
                        r_key = str(r).strip()
                        if not r_key:
                            continue
                        roles[r_key] = {
                            "prompt_path": f"../systemprompts/clink/project/{r_key}.txt",
                            "role_args": [],
                        }
                    # Project agent + validator roles
                    for role_name, prompt_path in [*agent_roles, *validator_roles]:
                        roles[role_name] = {"prompt_path": prompt_path, "role_args": []}

                    payload = {
                        "name": str(client_name),
                        "command": command,
                        "additional_args": [str(a) for a in additional_args],
                        "env": {str(k): str(v) for k, v in (env or {}).items()},
                        "roles": roles,
                    }
                    written = self.writer.write_json(
                        cli_clients_dir / f"{client_name}.json",
                        payload,
                        indent=2,
                        sort_keys=True,
                    )
                    result["cli_clients"].append(str(written))

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


__all__ = ["PalAdapter", "PalAdapterError"]
