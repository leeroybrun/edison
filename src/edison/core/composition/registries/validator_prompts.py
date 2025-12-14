"""Validator prompt composition registry.

Injects constitution context variables (optionalReads, rules) so validator prompt
templates can embed the validator constitution section without unresolved loops.
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List

from ._base import ComposableRegistry


class ValidatorPromptRegistry(ComposableRegistry[str]):
    """Compose validator prompts with constitution context_vars available."""

    content_type: ClassVar[str] = "validators"
    file_pattern: ClassVar[str] = "*.md"

    def get_context_vars(self, name: str, packs: List[str]) -> Dict[str, Any]:
        context = super().get_context_vars(name, packs)

        role_cfg = self.config.get("constitutions", {}).get("validators", {}) or {}
        if isinstance(role_cfg, dict):
            context["mandatoryReads"] = role_cfg.get("mandatoryReads", [])
            context["optionalReads"] = role_cfg.get("optionalReads", [])
        else:
            context["mandatoryReads"] = []
            context["optionalReads"] = []

        rules: List[Dict[str, Any]] = []
        try:
            from edison.core.rules.registry import get_rules_for_role

            rules = get_rules_for_role("validator", packs=packs)
        except (ValueError, ImportError):
            pass

        context["rules"] = rules
        return context


__all__ = ["ValidatorPromptRegistry"]

