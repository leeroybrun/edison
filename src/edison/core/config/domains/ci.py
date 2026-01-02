"""Domain-specific configuration for CI commands.

Provides cached access to project CI commands used for evidence capture and
workflow documentation.
"""

from __future__ import annotations

from functools import cached_property
from typing import Any

from ..base import BaseDomainConfig


class CIConfig(BaseDomainConfig):
    """CI configuration accessor.

    Reads the top-level `ci` section from merged config.
    """

    def _config_section(self) -> str:
        return "ci"

    @cached_property
    def commands(self) -> dict[str, str]:
        """Return configured CI commands (name -> command string)."""
        raw = self.section.get("commands") if isinstance(self.section, dict) else None
        if not isinstance(raw, dict):
            return {}
        out: dict[str, str] = {}
        for k, v in raw.items():
            key = str(k).strip()
            if not key:
                continue
            cmd = str(v).strip() if v is not None else ""
            if not cmd:
                continue
            out[key] = cmd
        return out

    def get_command(self, name: str) -> str | None:
        """Return a specific CI command by name."""
        return self.commands.get(str(name).strip())


__all__ = ["CIConfig"]

