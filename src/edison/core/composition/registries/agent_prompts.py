"""Agent prompt composition registry.

Extends the generic composition behavior by injecting the same constitution
context variables that the ConstitutionRegistry provides (optionalReads, rules).

This enables agent prompt templates to embed role constitutions via:
  {{include-section:constitutions/agents.md#embedded}}
without leaving unresolved loop variables.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from ._base import ComposableRegistry


class AgentPromptRegistry(ComposableRegistry[str]):
    """Compose agent prompts with constitution context_vars available."""

    content_type: ClassVar[str] = "agents"
    file_pattern: ClassVar[str] = "*.md"

    def discover_all_unfiltered(self, packs: list[str] | None = None) -> dict[str, Path]:
        """Discover agents without applying enable/disable filters."""
        return super().discover_all(packs)

    def discover_all(self, packs: list[str] | None = None) -> dict[str, Path]:
        discovered = self.discover_all_unfiltered(packs)
        try:
            from edison.core.config.domains.agents import AgentsConfig

            cfg = AgentsConfig(repo_root=self.project_root)
            allow = set(cfg.enabled_allowlist)
            deny = set(cfg.disabled)
            if allow:
                return {k: v for k, v in discovered.items() if k in allow}
            if deny:
                return {k: v for k, v in discovered.items() if k not in deny}
        except Exception:
            pass
        return discovered

    def get_context_vars(self, name: str, packs: list[str]) -> dict[str, Any]:
        context = super().get_context_vars(name, packs)

        # Mirror ConstitutionRegistry behavior for "agents" role.
        role_cfg = self.config.get("constitutions", {}).get("agents", {}) or {}
        if isinstance(role_cfg, dict):
            context["mandatoryReads"] = role_cfg.get("mandatoryReads", [])
            context["optionalReads"] = role_cfg.get("optionalReads", [])
        else:
            context["mandatoryReads"] = []
            context["optionalReads"] = []

        rules: list[dict[str, Any]] = []
        try:
            from edison.core.rules import get_rules_for_role

            rules = get_rules_for_role("agent", packs=packs)
        except (ValueError, ImportError):
            pass

        context["rules"] = rules
        return context


__all__ = ["AgentPromptRegistry"]
