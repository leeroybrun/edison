"""Small templating helpers shared by config-driven systems.

This module must not import high-level components (orchestrator, CLI, etc.)
to avoid circular imports during config initialization.
"""

from __future__ import annotations


class SafeDict(dict):
    """dict that preserves unknown `{placeholders}` instead of raising."""

    def __missing__(self, key: str) -> str:  # pragma: no cover
        return "{" + key + "}"


__all__ = ["SafeDict"]

