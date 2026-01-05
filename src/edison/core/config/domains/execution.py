"""Domain-specific configuration for execution settings.

Provides access to non-interactive environment guardrails configuration
for safe command execution in LLM/agent environments.
"""

from __future__ import annotations

import re
from functools import cached_property
from typing import Literal

from ..base import BaseDomainConfig


class ExecutionConfig(BaseDomainConfig):
    """Execution configuration accessor.

    Reads the top-level `execution` section from merged config.
    Provides access to non-interactive environment guardrails settings.
    """

    def _config_section(self) -> str:
        return "execution"

    @cached_property
    def _non_interactive(self) -> dict:
        """Return the nonInteractive section."""
        return self.section.get("nonInteractive") or {}

    @cached_property
    def non_interactive_enabled(self) -> bool:
        """Check if non-interactive guardrails are enabled."""
        return bool(self._non_interactive.get("enabled", False))

    @cached_property
    def non_interactive_env(self) -> dict[str, str]:
        """Return environment variables to inject for non-interactive execution.

        Returns a dict of environment variable names to their string values.
        """
        raw = self._non_interactive.get("env")
        if not isinstance(raw, dict):
            return {}
        out: dict[str, str] = {}
        for k, v in raw.items():
            key = str(k).strip()
            if not key:
                continue
            val = str(v) if v is not None else ""
            out[key] = val
        return out

    @cached_property
    def banned_command_patterns(self) -> list[str]:
        """Return list of banned command patterns.

        Patterns are strings that may be:
        - Simple substrings to match
        - Regex patterns (prefixed with ^)
        """
        raw = self._non_interactive.get("bannedCommandPatterns")
        if not isinstance(raw, list):
            return []
        return [str(p).strip() for p in raw if p]

    @cached_property
    def on_match(self) -> Literal["warn", "block"]:
        """Return behavior when a banned command is detected.

        Returns 'warn' or 'block'. Defaults to 'warn' (conservative).
        """
        raw = self._non_interactive.get("onMatch", "warn")
        if raw in ("warn", "block"):
            return raw
        return "warn"

    @cached_property
    def _compiled_patterns(self) -> list[tuple[str, re.Pattern]]:
        """Compile banned patterns for efficient matching."""
        patterns: list[tuple[str, re.Pattern]] = []
        for p in self.banned_command_patterns:
            if not p:
                continue
            try:
                # Patterns starting with ^ are treated as regex
                if p.startswith("^"):
                    patterns.append((p, re.compile(p)))
                else:
                    # Plain substring: escape and match anywhere
                    patterns.append((p, re.compile(re.escape(p))))
            except re.error:
                # Skip invalid patterns
                continue
        return patterns

    def is_command_banned(self, command: str) -> bool:
        """Check if a command matches any banned pattern.

        Args:
            command: The command string to check.

        Returns:
            True if the command matches any banned pattern, False otherwise.
        """
        if not self.non_interactive_enabled:
            return False
        if not command:
            return False
        cmd = command.strip()
        for _, pattern in self._compiled_patterns:
            if pattern.search(cmd):
                return True
        return False

    def get_matching_pattern(self, command: str) -> str | None:
        """Return the first banned pattern that matches the command.

        Args:
            command: The command string to check.

        Returns:
            The pattern string that matched, or None if no match.
        """
        if not self.non_interactive_enabled:
            return None
        if not command:
            return None
        cmd = command.strip()
        for pattern_str, pattern in self._compiled_patterns:
            if pattern.search(cmd):
                return pattern_str
        return None


__all__ = ["ExecutionConfig"]
