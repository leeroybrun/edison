"""Domain-specific configuration for QA.

Provides cached access to QA-related configuration including
delegation settings, validation config, and concurrency limits.
"""
from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Any, Dict, Optional

from ..base import BaseDomainConfig


class QAConfig(BaseDomainConfig):
    """QA configuration access following the DomainConfig pattern.

    Provides structured access to QA-related configuration with repo_root exposure.
    Extends BaseDomainConfig for consistent caching and repo_root handling.
    """

    def _config_section(self) -> str:
        return "qa"

    @cached_property
    def delegation_config(self) -> Dict[str, Any]:
        """Return the ``delegation`` section from configuration."""
        section = self._config.get("delegation", {}) or {}
        return section if isinstance(section, dict) else {}

    @cached_property
    def validation_config(self) -> Dict[str, Any]:
        """Return the ``validation`` section from configuration."""
        section = self._config.get("validation", {}) or {}
        return section if isinstance(section, dict) else {}

    def get_delegation_config(self) -> Dict[str, Any]:
        """Return the ``delegation`` section from configuration."""
        return self.delegation_config

    def get_validation_config(self) -> Dict[str, Any]:
        """Return the ``validation`` section from configuration."""
        return self.validation_config

    def get_max_concurrent_validators(self) -> int:
        """Return the global validator concurrency cap from configuration."""
        orchestration = self._config.get("orchestration", {}) or {}
        value = orchestration.get("maxConcurrentAgents")
        if value is None:
            raise RuntimeError(
                "orchestration.maxConcurrentAgents missing in configuration; "
                "define it in .edison/config/*.yml or bundled defaults."
            )
        return int(value)

    # Alias for consistency with module-level function
    def max_concurrent_validators(self) -> int:
        """Alias for get_max_concurrent_validators."""
        return self.get_max_concurrent_validators()


# ---------------------------------------------------------------------------
# Module-level helper functions (backward compatibility)
# ---------------------------------------------------------------------------


def load_config(repo_root: Optional[Path] = None, *, validate: bool = False) -> Dict[str, Any]:
    """Load merged Edison configuration for the given repository root."""
    from ..cache import get_cached_config
    return get_cached_config(repo_root=repo_root)


def load_delegation_config(repo_root: Optional[Path] = None) -> Dict[str, Any]:
    """Return the ``delegation`` section from YAML configuration."""
    return QAConfig(repo_root=repo_root).delegation_config


def load_validation_config(repo_root: Optional[Path] = None) -> Dict[str, Any]:
    """Return the ``validation`` section from YAML configuration."""
    return QAConfig(repo_root=repo_root).validation_config


def max_concurrent_validators(repo_root: Optional[Path] = None) -> int:
    """Return the global validator concurrency cap from YAML configuration."""
    return QAConfig(repo_root=repo_root).get_max_concurrent_validators()


__all__ = [
    "QAConfig",
    "load_config",
    "load_delegation_config",
    "load_validation_config",
    "max_concurrent_validators",
]
