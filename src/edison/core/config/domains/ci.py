"""Domain-specific configuration for CI commands.

Provides cached access to CI-related configuration including
configured commands for type-check, lint, test, build, etc.
"""
from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Any

from ..base import BaseDomainConfig


class CIConfig(BaseDomainConfig):
    """CI configuration access following the DomainConfig pattern.

    Provides structured access to CI command configuration.
    Extends BaseDomainConfig for consistent caching and repo_root handling.

    This domain reads the ``ci`` configuration section which contains
    command definitions for various CI operations.
    """

    def _config_section(self) -> str:
        return "ci"

    @cached_property
    def commands(self) -> dict[str, str]:
        """Return the configured CI commands.

        Filters out null/empty values to allow overriding defaults with null.

        Returns:
            Dictionary of command_name -> command_string (non-null values only)
        """
        commands = self.section.get("commands", {})
        if not isinstance(commands, dict):
            return {}
        # Filter out null/None/empty values - allows overriding defaults with null
        return {k: str(v) for k, v in commands.items() if v}

    def get_command(self, name: str) -> str | None:
        """Get a specific CI command by name.

        Args:
            name: Command name (e.g., 'type-check', 'lint', 'test', 'build')

        Returns:
            Command string or None if not configured
        """
        return self.commands.get(name)

    def get_command_required(self, name: str) -> str:
        """Get a CI command, raising if not configured.

        Args:
            name: Command name

        Returns:
            Command string

        Raises:
            RuntimeError: If command is not configured
        """
        cmd = self.get_command(name)
        if not cmd:
            raise RuntimeError(
                f"CI command '{name}' not configured. "
                f"Define ci.commands.{name} in ci.yaml"
            )
        return cmd

    def list_commands(self) -> list[str]:
        """List all configured command names.

        Returns:
            List of command names
        """
        return list(self.commands.keys())

    def get_evidence_commands(self) -> dict[str, str]:
        """Get commands that should generate evidence files.

        Returns the subset of CI commands that are used for evidence generation.
        This reads from validation.evidence.files mapping to determine which
        commands are evidence-producing.

        Returns:
            Dictionary of command_name -> command_string for evidence commands
        """
        from edison.core.config.domains.qa import QAConfig

        qa_config = QAConfig(repo_root=self.repo_root)
        evidence_cfg = qa_config.validation_config.get("evidence", {}) or {}
        evidence_files = evidence_cfg.get("files", {}) or {}

        # evidence_files maps: type-check -> command-type-check.txt
        # We want commands that have an entry in this mapping
        evidence_commands: dict[str, str] = {}
        for cmd_name in evidence_files.keys():
            cmd = self.get_command(cmd_name)
            if cmd:
                evidence_commands[cmd_name] = cmd

        return evidence_commands


def load_config(repo_root: Path | None = None) -> CIConfig:
    """Load and return a CIConfig instance.

    Args:
        repo_root: Optional repository root path. Uses auto-detection if None.

    Returns:
        Configured CIConfig instance.
    """
    return CIConfig(repo_root=repo_root)


__all__ = [
    "CIConfig",
    "load_config",
]
