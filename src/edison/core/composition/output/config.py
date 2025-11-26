from __future__ import annotations

"""Output configuration loader for composition.

Loads output path configuration from composition.yaml and provides
utilities to resolve output paths for all composable content types.

All paths are configurable via YAML - NO hardcoded paths in Python code.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Any

from edison.core.utils.io import read_yaml
from edison.core.utils.merge import deep_merge
from edison.data import get_data_path


@dataclass
class OutputConfig:
    """Configuration for a single output type."""
    enabled: bool
    output_path: str
    filename: str
    template: Optional[str] = None
    filename_pattern: Optional[str] = None
    preserve_structure: bool = False


@dataclass
class ClientOutputConfig:
    """Configuration for a client output (Claude, Zen, etc.)."""
    enabled: bool
    output_path: str
    filename: str
    template: str


@dataclass
class SyncConfig:
    """Configuration for client sync outputs."""
    enabled: bool
    agents_path: Optional[str] = None
    agents_filename_pattern: Optional[str] = None
    prompts_path: Optional[str] = None
    prompts_filename_pattern: Optional[str] = None


class OutputConfigLoader:
    """Loads and resolves output configuration from composition.yaml."""

    def __init__(self, repo_root: Optional[Path] = None, project_config_dir: Optional[Path] = None):
        from edison.core.utils.paths import get_project_config_dir
        from edison.core.utils.paths import PathResolver
        
        self.repo_root = repo_root or PathResolver.resolve_project_root()
        self.project_config_dir = project_config_dir or get_project_config_dir(self.repo_root)
        self._config: Optional[Dict[str, Any]] = None

    def _load_config(self) -> Dict[str, Any]:
        """Load composition.yaml configuration."""
        if self._config is not None:
            return self._config
        
        # Load core defaults
        core_config_path = get_data_path("config", "composition.yaml")
        core_config = read_yaml(core_config_path, default={})
        
        # Load project overrides if they exist
        project_config_path = self.project_config_dir / "composition.yaml"
        if project_config_path.exists():
            project_config = read_yaml(project_config_path, default={})
            # Deep merge project config over core config
            self._config = deep_merge(core_config, project_config)
        else:
            self._config = core_config
        
        return self._config

    def _resolve_path(self, path_template: str) -> Path:
        """Resolve path template with placeholders."""
        resolved = path_template.replace(
            "{{PROJECT_EDISON_DIR}}",
            str(self.project_config_dir)
        )
        path = Path(resolved)
        if not path.is_absolute():
            path = self.repo_root / path
        return path

    def get_outputs_config(self) -> Dict[str, Any]:
        """Get the full outputs configuration."""
        config = self._load_config()
        return config.get("outputs", {})

    # -------------------------------------------------------------------------
    # Canonical Entry
    # -------------------------------------------------------------------------
    def get_canonical_entry_config(self) -> OutputConfig:
        """Get canonical entry (AGENTS.md) output configuration."""
        outputs = self.get_outputs_config()
        cfg = outputs.get("canonical_entry", {})
        return OutputConfig(
            enabled=cfg.get("enabled", True),
            output_path=cfg.get("output_path", "."),
            filename=cfg.get("filename", "AGENTS.md"),
            template=cfg.get("template", "canonical/AGENTS.md"),
        )

    def get_canonical_entry_path(self) -> Optional[Path]:
        """Get resolved path for canonical entry file."""
        cfg = self.get_canonical_entry_config()
        if not cfg.enabled:
            return None
        output_dir = self._resolve_path(cfg.output_path)
        return output_dir / cfg.filename

    # -------------------------------------------------------------------------
    # Clients
    # -------------------------------------------------------------------------
    def get_client_config(self, client_name: str) -> Optional[ClientOutputConfig]:
        """Get output configuration for a specific client."""
        outputs = self.get_outputs_config()
        clients = outputs.get("clients", {})
        cfg = clients.get(client_name)
        if cfg is None:
            return None
        return ClientOutputConfig(
            enabled=cfg.get("enabled", False),
            output_path=cfg.get("output_path", f".{client_name}"),
            filename=cfg.get("filename", f"{client_name.upper()}.md"),
            template=cfg.get("template", f"clients/{client_name}.md"),
        )

    def get_client_path(self, client_name: str) -> Optional[Path]:
        """Get resolved path for a client output file."""
        cfg = self.get_client_config(client_name)
        if cfg is None or not cfg.enabled:
            return None
        output_dir = self._resolve_path(cfg.output_path)
        return output_dir / cfg.filename

    def get_enabled_clients(self) -> Dict[str, ClientOutputConfig]:
        """Get all enabled client configurations."""
        outputs = self.get_outputs_config()
        clients = outputs.get("clients", {})
        result = {}
        for name, cfg in clients.items():
            if cfg.get("enabled", False):
                result[name] = ClientOutputConfig(
                    enabled=True,
                    output_path=cfg.get("output_path", f".{name}"),
                    filename=cfg.get("filename", f"{name.upper()}.md"),
                    template=cfg.get("template", f"clients/{name}.md"),
                )
        return result

    # -------------------------------------------------------------------------
    # Constitutions
    # -------------------------------------------------------------------------
    def get_constitutions_config(self) -> Dict[str, Any]:
        """Get constitutions output configuration."""
        outputs = self.get_outputs_config()
        return outputs.get("constitutions", {})

    def get_constitution_path(self, role: str) -> Optional[Path]:
        """Get resolved path for a constitution file."""
        cfg = self.get_constitutions_config()
        if not cfg.get("enabled", True):
            return None
        
        files = cfg.get("files", {})
        role_cfg = files.get(role, {})
        if not role_cfg.get("enabled", True):
            return None
        
        output_dir = self._resolve_path(cfg.get("output_path", "{{PROJECT_EDISON_DIR}}/_generated/constitutions"))
        filename = role_cfg.get("filename", f"{role.upper()}.md")
        return output_dir / filename

    # -------------------------------------------------------------------------
    # Agents
    # -------------------------------------------------------------------------
    def get_agents_config(self) -> OutputConfig:
        """Get agents output configuration."""
        outputs = self.get_outputs_config()
        cfg = outputs.get("agents", {})
        return OutputConfig(
            enabled=cfg.get("enabled", True),
            output_path=cfg.get("output_path", "{{PROJECT_EDISON_DIR}}/_generated/agents"),
            filename="",  # Not used for agents (pattern-based)
            filename_pattern=cfg.get("filename_pattern", "{name}.md"),
        )

    def get_agents_dir(self) -> Optional[Path]:
        """Get resolved directory for agent files."""
        cfg = self.get_agents_config()
        if not cfg.enabled:
            return None
        return self._resolve_path(cfg.output_path)

    def get_agent_path(self, agent_name: str) -> Optional[Path]:
        """Get resolved path for a specific agent file."""
        cfg = self.get_agents_config()
        if not cfg.enabled:
            return None
        output_dir = self._resolve_path(cfg.output_path)
        filename = (cfg.filename_pattern or "{name}.md").format(name=agent_name)
        return output_dir / filename

    # -------------------------------------------------------------------------
    # Validators
    # -------------------------------------------------------------------------
    def get_validators_config(self) -> OutputConfig:
        """Get validators output configuration."""
        outputs = self.get_outputs_config()
        cfg = outputs.get("validators", {})
        return OutputConfig(
            enabled=cfg.get("enabled", True),
            output_path=cfg.get("output_path", "{{PROJECT_EDISON_DIR}}/_generated/validators"),
            filename="",
            filename_pattern=cfg.get("filename_pattern", "{name}.md"),
        )

    def get_validators_dir(self) -> Optional[Path]:
        """Get resolved directory for validator files."""
        cfg = self.get_validators_config()
        if not cfg.enabled:
            return None
        return self._resolve_path(cfg.output_path)

    def get_validator_path(self, validator_name: str) -> Optional[Path]:
        """Get resolved path for a specific validator file."""
        cfg = self.get_validators_config()
        if not cfg.enabled:
            return None
        output_dir = self._resolve_path(cfg.output_path)
        filename = (cfg.filename_pattern or "{name}.md").format(name=validator_name)
        return output_dir / filename

    # -------------------------------------------------------------------------
    # Guidelines
    # -------------------------------------------------------------------------
    def get_guidelines_config(self) -> OutputConfig:
        """Get guidelines output configuration."""
        outputs = self.get_outputs_config()
        cfg = outputs.get("guidelines", {})
        return OutputConfig(
            enabled=cfg.get("enabled", True),
            output_path=cfg.get("output_path", "{{PROJECT_EDISON_DIR}}/_generated/guidelines"),
            filename="",
            filename_pattern=cfg.get("filename_pattern", "{name}.md"),
            preserve_structure=cfg.get("preserve_structure", True),
        )

    def get_guidelines_dir(self) -> Optional[Path]:
        """Get resolved directory for guideline files."""
        cfg = self.get_guidelines_config()
        if not cfg.enabled:
            return None
        return self._resolve_path(cfg.output_path)

    # -------------------------------------------------------------------------
    # Sync Configuration
    # -------------------------------------------------------------------------
    def get_sync_config(self, client_name: str) -> Optional[SyncConfig]:
        """Get sync configuration for a client."""
        outputs = self.get_outputs_config()
        sync = outputs.get("sync", {})
        cfg = sync.get(client_name)
        if cfg is None:
            return None
        return SyncConfig(
            enabled=cfg.get("enabled", False),
            agents_path=cfg.get("agents_path"),
            agents_filename_pattern=cfg.get("agents_filename_pattern"),
            prompts_path=cfg.get("prompts_path"),
            prompts_filename_pattern=cfg.get("prompts_filename_pattern"),
        )

    def get_sync_agents_dir(self, client_name: str) -> Optional[Path]:
        """Get resolved directory for synced agent files."""
        cfg = self.get_sync_config(client_name)
        if cfg is None or not cfg.enabled or not cfg.agents_path:
            return None
        return self._resolve_path(cfg.agents_path)


# Convenience function for quick access
def get_output_config(repo_root: Optional[Path] = None) -> OutputConfigLoader:
    """Get an OutputConfigLoader instance."""
    return OutputConfigLoader(repo_root=repo_root)


__all__ = [
    "OutputConfig",
    "ClientOutputConfig",
    "SyncConfig",
    "OutputConfigLoader",
    "get_output_config",
]
