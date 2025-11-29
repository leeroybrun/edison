"""Domain-specific configuration for operation timeouts.

Provides cached access to timeout settings for various operations.
"""
from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Dict, Optional

from ..base import BaseDomainConfig

_REQUIRED_TIMEOUT_KEYS = (
    "git_operations_seconds",
    "db_operations_seconds",
    "json_io_lock_seconds",
)


class TimeoutsConfig(BaseDomainConfig):
    """Domain-specific configuration accessor for operation timeouts.

    Provides typed, cached access to timeout configuration.
    Extends BaseDomainConfig for consistent caching and repo_root handling.
    """

    def _config_section(self) -> str:
        return "timeouts"

    def _validate_required_keys(self) -> None:
        """Validate that all required timeout keys are present."""
        if not self.section:
            raise RuntimeError("timeouts section missing from configuration")

        for key in _REQUIRED_TIMEOUT_KEYS:
            if key not in self.section:
                raise RuntimeError(f"timeouts.{key} missing from configuration")

    @cached_property
    def git_operations_seconds(self) -> float:
        """Get timeout for git operations in seconds."""
        self._validate_required_keys()
        return float(self.section["git_operations_seconds"])

    @cached_property
    def db_operations_seconds(self) -> float:
        """Get timeout for database operations in seconds."""
        self._validate_required_keys()
        return float(self.section["db_operations_seconds"])

    @cached_property
    def json_io_lock_seconds(self) -> float:
        """Get timeout for JSON I/O lock operations in seconds."""
        self._validate_required_keys()
        return float(self.section["json_io_lock_seconds"])

    def get_all_settings(self) -> Dict[str, float]:
        """Get all timeout settings as a dict.

        Returns:
            Dict with all timeout values.
        """
        self._validate_required_keys()
        return {
            "git_operations_seconds": float(self.section["git_operations_seconds"]),
            "db_operations_seconds": float(self.section["db_operations_seconds"]),
            "json_io_lock_seconds": float(self.section["json_io_lock_seconds"]),
        }


__all__ = [
    "TimeoutsConfig",
]



