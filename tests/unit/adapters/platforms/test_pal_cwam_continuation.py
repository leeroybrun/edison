"""Tests for Pal prompt CWAM + continuation guidance injection.

Following STRICT TDD:
1. Write failing test FIRST (RED)
2. Implement minimum code to pass (GREEN)
3. Refactor

These tests verify that Pal prompts include CWAM (Context Window Anxiety Management)
and continuation guidance when enabled via config.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.adapters.platforms.pal import PalAdapter


class TestPalCwamContinuationGuidanceSection:
    """Tests for CWAM and continuation guidance in Pal prompts."""

    def test_pal_prompt_includes_cwam_guidance_when_enabled(self, tmp_path: Path) -> None:
        """Pal prompt should include CWAM guidance when context_window.enabled is True."""
        project_root = tmp_path
        (project_root / ".edison").mkdir(parents=True, exist_ok=True)

        adapter = PalAdapter(project_root=project_root)
        prompt = adapter.compose_pal_prompt(role="default", model="codex", packs=[])

        # Should include CWAM-related guidance
        assert "context" in prompt.lower() or "methodically" in prompt.lower(), (
            "Pal prompt should include context window guidance when CWAM is enabled"
        )

    def test_pal_prompt_includes_continuation_guidance_when_enabled(
        self, tmp_path: Path
    ) -> None:
        """Pal prompt should include continuation guidance when continuation.enabled is True."""
        project_root = tmp_path
        (project_root / ".edison").mkdir(parents=True, exist_ok=True)

        adapter = PalAdapter(project_root=project_root)
        prompt = adapter.compose_pal_prompt(role="default", model="codex", packs=[])

        # Should include continuation-related guidance
        assert "continue" in prompt.lower() or "session" in prompt.lower(), (
            "Pal prompt should include continuation guidance when enabled"
        )

    def test_pal_prompt_guidance_sourced_from_rules(self, tmp_path: Path) -> None:
        """CWAM and continuation guidance should be sourced from rules, not hardcoded."""
        project_root = tmp_path
        (project_root / ".edison").mkdir(parents=True, exist_ok=True)

        adapter = PalAdapter(project_root=project_root)

        # Get rules for context_window context
        cwam_rules = [
            r
            for r in adapter.rules_registry.load_composed_rules()
            if "context_window" in (r.get("contexts") or [])
        ]
        assert cwam_rules, "Should have CWAM rules with context_window context"

        # Get rules for continuation context
        continuation_rules = [
            r
            for r in adapter.rules_registry.load_composed_rules()
            if "continuation" in (r.get("contexts") or [])
        ]
        assert continuation_rules, "Should have continuation rules with continuation context"

    def test_pal_prompt_cwam_section_not_present_when_disabled(self, tmp_path: Path) -> None:
        """The dedicated CWAM section should not appear when context_window.prompts.inject is False."""
        project_root = tmp_path
        (project_root / ".edison").mkdir(parents=True, exist_ok=True)

        # Create config that disables CWAM prompt injection
        config_dir = project_root / ".edison" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "context_window.yaml").write_text(
            "context_window:\n  enabled: false\n  prompts:\n    inject: false\n",
            encoding="utf-8",
        )
        # Also disable continuation to fully test the section removal
        (config_dir / "continuation.yaml").write_text(
            "continuation:\n  enabled: false\n  prompts:\n    inject: false\n",
            encoding="utf-8",
        )

        adapter = PalAdapter(project_root=project_root)
        prompt = adapter.compose_pal_prompt(role="default", model="codex", packs=[])

        # The dedicated CWAM/Continuation section header should NOT appear
        assert "=== Context & Continuation ===" not in prompt, (
            "CWAM/Continuation section header should not appear when disabled"
        )
        # The section content header should also not appear
        assert "## Context & Continuation" not in prompt, (
            "CWAM/Continuation section should not be injected when disabled"
        )

    def test_pal_prompt_continuation_section_not_present_when_disabled(
        self, tmp_path: Path
    ) -> None:
        """The dedicated continuation section should not appear when continuation.prompts.inject is False."""
        project_root = tmp_path
        (project_root / ".edison").mkdir(parents=True, exist_ok=True)

        # Create config that disables continuation and CWAM prompt injection
        config_dir = project_root / ".edison" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "continuation.yaml").write_text(
            "continuation:\n  enabled: false\n  prompts:\n    inject: false\n",
            encoding="utf-8",
        )
        (config_dir / "context_window.yaml").write_text(
            "context_window:\n  enabled: false\n  prompts:\n    inject: false\n",
            encoding="utf-8",
        )

        adapter = PalAdapter(project_root=project_root)
        prompt = adapter.compose_pal_prompt(role="default", model="codex", packs=[])

        # The dedicated CWAM/Continuation section header should NOT appear
        assert "=== Context & Continuation ===" not in prompt, (
            "CWAM/Continuation section header should not appear when disabled"
        )

    def test_pal_prompt_has_cwam_continuation_section(self, tmp_path: Path) -> None:
        """Pal prompt should have a dedicated CWAM/continuation section from rules."""
        project_root = tmp_path
        (project_root / ".edison").mkdir(parents=True, exist_ok=True)

        adapter = PalAdapter(project_root=project_root)
        prompt = adapter.compose_pal_prompt(role="default", model="codex", packs=[])

        # The CWAM rule should contribute guidance about methodical work
        cwam_rules = [
            r
            for r in adapter.rules_registry.load_composed_rules()
            if "context_window" in (r.get("contexts") or [])
        ]
        assert cwam_rules, "Should have CWAM rules"

        # The continuation rule should contribute guidance about not stopping early
        continuation_rules = [
            r
            for r in adapter.rules_registry.load_composed_rules()
            if "continuation" in (r.get("contexts") or [])
        ]
        assert continuation_rules, "Should have continuation rules"

        # The injected section should be concise - check rules themselves are short
        for rule in cwam_rules:
            guidance = rule.get("guidance", "")
            lines = [ln for ln in guidance.strip().split("\n") if ln.strip()]
            assert len(lines) <= 6, (
                f"CWAM rule guidance should be concise, got {len(lines)} lines"
            )

        for rule in continuation_rules:
            guidance = rule.get("guidance", "")
            lines = [ln for ln in guidance.strip().split("\n") if ln.strip()]
            assert len(lines) <= 6, (
                f"Continuation rule guidance should be concise, got {len(lines)} lines"
            )


class TestPalCwamContinuationInjection:
    """Tests for explicit CWAM/continuation section injection."""

    def test_pal_prompt_injects_cwam_section_header(self, tmp_path: Path) -> None:
        """Pal prompt should inject a clearly marked CWAM/continuation section."""
        project_root = tmp_path
        (project_root / ".edison").mkdir(parents=True, exist_ok=True)

        adapter = PalAdapter(project_root=project_root)
        prompt = adapter.compose_pal_prompt(role="default", model="codex", packs=[])

        # Should have a dedicated section for CWAM/continuation guidance
        # The header should be clear and identifiable
        assert (
            "## Context & Continuation" in prompt
            or "## Session Guidance" in prompt
            or "=== Context & Continuation ===" in prompt
        ), (
            "Pal prompt should have a dedicated CWAM/continuation section header"
        )

    def test_pal_prompt_injects_rule_guidance_text(self, tmp_path: Path) -> None:
        """Pal prompt should inject actual rule guidance text for CWAM/continuation."""
        project_root = tmp_path
        (project_root / ".edison").mkdir(parents=True, exist_ok=True)

        adapter = PalAdapter(project_root=project_root)
        prompt = adapter.compose_pal_prompt(role="default", model="codex", packs=[])
        normalized_prompt = " ".join(prompt.split())

        # Get the CWAM rule guidance
        cwam_rules = [
            r
            for r in adapter.rules_registry.load_composed_rules()
            if "context_window" in (r.get("contexts") or [])
        ]

        # At least one CWAM rule's guidance should appear in the prompt
        cwam_found = False
        for rule in cwam_rules:
            guidance = rule.get("guidance", "").strip()
            normalized_guidance = " ".join(guidance.split())
            if normalized_guidance and normalized_guidance in normalized_prompt:
                cwam_found = True
                break

        assert cwam_found, (
            "Pal prompt should include CWAM rule guidance text"
        )

        # Get the continuation rule guidance
        continuation_rules = [
            r
            for r in adapter.rules_registry.load_composed_rules()
            if "continuation" in (r.get("contexts") or [])
        ]

        # At least one continuation rule's guidance should appear in the prompt
        continuation_found = False
        for rule in continuation_rules:
            guidance = rule.get("guidance", "").strip()
            normalized_guidance = " ".join(guidance.split())
            if normalized_guidance and normalized_guidance in normalized_prompt:
                continuation_found = True
                break

        assert continuation_found, (
            "Pal prompt should include continuation rule guidance text"
        )

    def test_pal_prompt_uses_config_for_injection(self, tmp_path: Path) -> None:
        """Pal composer should read from config to determine injection behavior."""
        project_root = tmp_path
        (project_root / ".edison").mkdir(parents=True, exist_ok=True)

        # Create config that enables prompt injection explicitly
        config_dir = project_root / ".edison" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "context_window.yaml").write_text(
            "context_window:\n  enabled: true\n  prompts:\n    inject: true\n",
            encoding="utf-8",
        )
        (config_dir / "continuation.yaml").write_text(
            "continuation:\n  enabled: true\n  prompts:\n    inject: true\n",
            encoding="utf-8",
        )

        adapter = PalAdapter(project_root=project_root)
        prompt = adapter.compose_pal_prompt(role="default", model="codex", packs=[])

        # With injection enabled, should have the dedicated section
        assert (
            "## Context & Continuation" in prompt
            or "## Session Guidance" in prompt
            or "=== Context & Continuation ===" in prompt
        ), (
            "Pal prompt should inject section when config enables it"
        )
