"""Pal composer mixin for role/model prompt composition.

This module provides PalComposerMixin which handles composing
prompts for different Pal roles and models.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, TYPE_CHECKING

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

    _EMBEDDED_CWAM_BLOCK_RE = re.compile(
        r"<!-- SECTION: embedded -->.*?<!-- /SECTION: embedded -->\n*",
        flags=re.DOTALL,
    )

    def _get_cwam_continuation_section(self: "PalAdapter") -> str:
        """Get CWAM and continuation guidance section from rules.

        Reads config to determine if injection is enabled, then fetches
        guidance from rules with context_window and continuation contexts.

        Returns:
            Composed CWAM/continuation section, or empty string if disabled.
        """
        cfg = self.config

        # Check if CWAM injection is enabled
        context_window_cfg = cfg.get("context_window") or {}
        cwam_enabled = bool(context_window_cfg.get("enabled", True))
        cwam_prompts_cfg = context_window_cfg.get("prompts") or {}
        cwam_inject = bool(cwam_prompts_cfg.get("inject", cwam_enabled))

        # Check if continuation injection is enabled
        continuation_cfg = cfg.get("continuation") or {}
        continuation_enabled = bool(continuation_cfg.get("enabled", True))
        continuation_prompts_cfg = continuation_cfg.get("prompts") or {}
        continuation_inject = bool(continuation_prompts_cfg.get("inject", continuation_enabled))

        if not cwam_inject and not continuation_inject:
            return ""

        section_lines: List[str] = []

        # Fetch CWAM rules
        if cwam_inject:
            cwam_rules = [
                r
                for r in self.rules_registry.load_composed_rules()
                if "context_window" in (r.get("contexts") or [])
            ]
            for rule in cwam_rules:
                guidance = str(rule.get("guidance") or "").strip()
                if guidance:
                    if section_lines:
                        section_lines.append("")
                    section_lines.append(guidance)
                    break  # Only take first matching rule to keep it minimal

        # Fetch continuation rules
        if continuation_inject:
            continuation_rules = [
                r
                for r in self.rules_registry.load_composed_rules()
                if "continuation" in (r.get("contexts") or [])
            ]
            for rule in continuation_rules:
                guidance = str(rule.get("guidance") or "").strip()
                if guidance:
                    if section_lines:
                        section_lines.append("")
                    section_lines.append(guidance)
                    break  # Only take first matching rule to keep it minimal

        if not section_lines:
            # No guidance found
            return ""

        return "\n".join(section_lines)

    def compose_pal_prompt(self: "PalAdapter", role: str, model: str, packs: List[str]) -> str:
        """Generate prompt text for a given role/model combination.

        The prompt includes:
          - Role header (model-agnostic; prompts are shared across CLI clients)
          - Base Edison context (via composition registries)
          - Role-specific guideline excerpts
          - Role-specific rules summary
          - CWAM and continuation guidance (config-controlled)

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
        # Avoid duplicating CWAM/continuation guidance: Pal composes that section explicitly
        # based on config injection flags, so strip any embedded CWAM block that may appear
        # in shared validator/agent templates.
        base_content = self._EMBEDDED_CWAM_BLOCK_RE.sub("", base_content).rstrip()

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

        # Get CWAM and continuation guidance section
        cwam_continuation_block = self._get_cwam_continuation_section()

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
        if cwam_continuation_block:
            sections.append("=== Context & Continuation ===\n\n" + cwam_continuation_block)

        prompt = "\n\n".join([section for section in sections if section]).rstrip() + "\n"
        prompt = self._EMBEDDED_CWAM_BLOCK_RE.sub("", prompt)
        return prompt.rstrip() + "\n"


__all__ = ["PalComposerMixin", "_canonical_model"]
