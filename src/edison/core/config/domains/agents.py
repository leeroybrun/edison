"""Domain-specific configuration for agent enable/disable behavior."""

from __future__ import annotations

from functools import cached_property

from ..base import BaseDomainConfig


def _as_str_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return []


class AgentsConfig(BaseDomainConfig):
    """Agent enablement configuration.

    Semantics:
    - `agents.enabled` (allowlist): when non-empty, only these agents are available.
    - `agents.disabled` (denylist): excluded agents when allowlist is empty.
    """

    def _config_section(self) -> str:
        return "agents"

    @cached_property
    def enabled_allowlist(self) -> list[str]:
        return _as_str_list(self.section.get("enabled"))

    @cached_property
    def disabled(self) -> list[str]:
        return _as_str_list(self.section.get("disabled"))


__all__ = ["AgentsConfig"]
