"""Pal composer mixin for role/model prompt composition.

This module provides PalComposerMixin which handles composing
prompts for different Pal roles and models.
"""
from __future__ import annotations
from typing import List, TYPE_CHECKING

from edison.core.composition.output.formatting import compose_for_role
from .discovery import _canonical_role

if TYPE_CHECKING:
    from .adapter import PalAdapter


def _canonical_model(model: str) -> str:
    """Normalize model identifier to codex|claude|gemini."""
    low = (model or "").strip().lower()
    if low.startswith("codex"):
        return "codex"
    if low.startswith("claude"):
        return "claude"
    if low.startswith("gemini"):
        return "gemini"
    return low or "codex"


class PalComposerMixin:
    """Mixin for composing Pal prompts."""

    def compose_pal_prompt(self: "PalAdapter", role: str, model: str, packs: List[str]) -> str:
        """Generate prompt text for a given role/model combination.

        The prompt includes:
          - Role header (model-agnostic; prompts are shared across CLI clients)
          - Base Edison context (via composition registries)
          - Role-specific guideline excerpts
          - Role-specific rules summary

        Args:
            role: Pal role identifier
            model: Model identifier (codex/claude/gemini)
            packs: List of active packs

        Returns:
            Composed prompt text for the role/model combination
        """
        model_key = _canonical_model(model)
        canonical_role = _canonical_role(role)

        # Base content derives from the model-specific role used for validators.
        base_content = compose_for_role(self, model_key)

        guideline_names = self.get_applicable_guidelines(role)
        guideline_sections: List[str] = []
        for name in guideline_names:
            text = self.guideline_registry.compose(name, packs) or ""
            guideline_sections.append(f"## Guideline: {name}\n\n{text.strip()}")
        guidelines_block = "\n\n".join(guideline_sections)

        rules = self.get_applicable_rules(role)
        rule_lines: List[str] = []
        if rules:
            rule_lines.append("## Role-Specific Rules")
            for rule_obj in rules:
                rid = rule_obj.get("id") or ""
                title = rule_obj.get("title") or rid
                category = rule_obj.get("category") or ""
                blocking = bool(rule_obj.get("blocking"))
                level = "BLOCKING" if blocking else "NON-BLOCKING"
                label = f"[{level}] {title}"
                if category:
                    label = f"{label} (category: {category})"
                rule_lines.append(f"- {label}")
        rules_block = "\n".join(rule_lines)

        header_lines: List[str] = [
            "=== Edison / Pal MCP Prompt ===",
            f"Model: {model_key}",
            f"Role: {canonical_role}",
            "Context window: Be concise and stay within the model limit.",
        ]

        header = "\n".join(header_lines)

        sections: List[str] = [header, base_content]
        if guidelines_block:
            sections.append("=== Role-Specific Guidelines ===\n\n" + guidelines_block)
        if rules_block:
            sections.append(rules_block)

        return "\n\n".join([section for section in sections if section]).rstrip() + "\n"


__all__ = ["PalComposerMixin", "_canonical_model"]
