"""QA configuration accessors.

This module provides thin wrappers around :class:`lib.config.ConfigManager`
to expose QA-specific sections without any legacy JSON fallbacks. All values
come from YAML and are resolved relative to the project root determined by
``PathResolver`` or an explicit ``repo_root`` parameter.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from ..legacy_guard import enforce_no_legacy_project_root
from ..config import ConfigManager
from ..paths.resolver import PathResolver


# Fail fast when imported from a pre-Edison repository
enforce_no_legacy_project_root("lib.qa.config")


class QAConfig:
    """QA configuration access following the DomainConfig pattern.

    Provides structured access to QA-related configuration with repo_root exposure.
    """

    def __init__(self, repo_root: Optional[Path] = None):
        self._mgr = ConfigManager(repo_root=repo_root)
        self.repo_root = self._mgr.repo_root if hasattr(self._mgr, 'repo_root') else repo_root
        self._config = self._mgr.load_config(validate=False)

    def get_delegation_config(self) -> Dict[str, Any]:
        """Return the ``delegation`` section from configuration."""
        section = self._config.get("delegation", {}) or {}
        return section if isinstance(section, dict) else {}

    def get_validation_config(self) -> Dict[str, Any]:
        """Return the ``validation`` section from configuration."""
        section = self._config.get("validation", {}) or {}
        return section if isinstance(section, dict) else {}

    def get_max_concurrent_validators(self) -> int:
        """Return the global validator concurrency cap from configuration."""
        orchestration = self._config.get("orchestration", {}) or {}
        value = orchestration.get("maxConcurrentAgents")
        if value is None:
            raise RuntimeError(
                "orchestration.maxConcurrentAgents missing in configuration; "
                "define it in .edison/core/config/defaults.yaml or project overlays."
            )
        return int(value)

    # Alias for consistency with module-level function
    def max_concurrent_validators(self) -> int:
        """Alias for get_max_concurrent_validators."""
        return self.get_max_concurrent_validators()


def load_config(repo_root: Optional[Path] = None, *, validate: bool = False) -> Dict[str, Any]:
    """Load merged Edison configuration for the given repository root."""
    root = repo_root or PathResolver.resolve_project_root()
    return ConfigManager(root).load_config(validate=validate)


def load_delegation_config(repo_root: Optional[Path] = None) -> Dict[str, Any]:
    """Return the ``delegation`` section from YAML configuration."""
    cfg = load_config(repo_root, validate=False)
    section = cfg.get("delegation", {}) or {}
    return section if isinstance(section, dict) else {}


def load_validation_config(repo_root: Optional[Path] = None) -> Dict[str, Any]:
    """Return the ``validation`` section from YAML configuration."""
    cfg = load_config(repo_root, validate=False)
    section = cfg.get("validation", {}) or {}
    return section if isinstance(section, dict) else {}


def max_concurrent_validators(repo_root: Optional[Path] = None) -> int:
    """Return the global validator concurrency cap from YAML configuration."""
    cfg = load_config(repo_root, validate=False)
    orchestration = cfg.get("orchestration", {}) or {}
    value = orchestration.get("maxConcurrentAgents")
    if value is None:
        raise RuntimeError(
            "orchestration.maxConcurrentAgents missing in configuration; "
            "define it in .edison/core/config/defaults.yaml or project overlays."
        )
    return int(value)


__all__ = [
    "QAConfig",
    "load_config",
    "load_delegation_config",
    "load_validation_config",
    "max_concurrent_validators",
]

