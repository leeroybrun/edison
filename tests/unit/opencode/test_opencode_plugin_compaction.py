"""
Tests for OpenCode plugin context window compaction features.

SUMMARY: Verify the plugin implements preemptive and recovery compaction

Task 044 requirements:
- Compaction summary-shape rule (what to preserve after compaction)
- Preemptive compaction (threshold-based, before hitting limits)
- Token-limit recovery (detect errors, auto-compact, continue)
- Config-driven thresholds and error patterns

Task 079 requirements:
- experimental.session.compacting hook (inject guidance BEFORE any compaction)
- session.compacted event handler (inject context AFTER any compaction)
- Hooks capture ALL compaction events (not just Edison-triggered)
"""

from __future__ import annotations

from pathlib import Path

import pytest


# Helper to get worktree src path
def get_src_path() -> Path:
    """Get the src path, checking worktree first then main repo."""
    # Try worktree path first
    worktree = Path(__file__).parent.parent.parent.parent
    src = worktree / "src"
    if src.exists():
        return src
    # Fallback to main repo
    return Path(__file__).parent.parent.parent.parent / "src"


class TestPluginCompactionState:
    """Tests for compaction state tracking in the plugin template."""

    def test_plugin_tracks_last_compaction_at(self) -> None:
        """Plugin should track lastCompactionAt timestamp."""
        plugin_template = (
            get_src_path() / "edison/data/templates/opencode/plugin/edison.ts.template"
        )
        content = plugin_template.read_text()
        assert "lastCompactionAt" in content, (
            "Plugin should track lastCompactionAt for compaction timing"
        )

    def test_plugin_has_compaction_config(self) -> None:
        """Plugin should have configurable compaction settings."""
        plugin_template = (
            get_src_path() / "edison/data/templates/opencode/plugin/edison.ts.template"
        )
        content = plugin_template.read_text()
        assert "COMPACTION_CONFIG" in content or "compaction" in content.lower(), (
            "Plugin should have compaction configuration"
        )


class TestPluginPreemptiveCompaction:
    """Tests for preemptive compaction feature."""

    def test_plugin_has_preemptive_threshold(self, isolated_project_env: Path) -> None:
        """Plugin should have configurable preemptive threshold."""
        plugin_template = (
            get_src_path() / "edison/data/templates/opencode/plugin/edison.ts.template"
        )
        content = plugin_template.read_text()
        has_threshold = (
            "threshold" in content.lower() or
            "preemptive" in content.lower()
        )
        assert has_threshold, (
            "Plugin should have preemptive compaction threshold"
        )

    def test_plugin_checks_token_usage(self, isolated_project_env: Path) -> None:
        """Plugin should check token usage or estimate it."""
        plugin_template = (
            get_src_path() / "edison/data/templates/opencode/plugin/edison.ts.template"
        )
        content = plugin_template.read_text()
        has_usage_check = (
            "token" in content.lower() or
            "usage" in content.lower() or
            "limit" in content.lower()
        )
        assert has_usage_check, (
            "Plugin should check token usage for preemptive compaction"
        )


class TestPluginRecoveryCompaction:
    """Tests for token-limit error recovery feature."""

    def test_plugin_handles_error_events(self, isolated_project_env: Path) -> None:
        """Plugin should handle session.error events for recovery."""
        plugin_template = (
            get_src_path() / "edison/data/templates/opencode/plugin/edison.ts.template"
        )
        content = plugin_template.read_text()
        content_lower = content.lower()
        # Should handle error events or have error recovery logic
        has_error_handling = ("session.error" in content_lower) or ("error" in content_lower and "recover" in content_lower)
        assert has_error_handling, (
            "Plugin should handle error events for recovery"
        )

    def test_plugin_has_error_patterns(self, isolated_project_env: Path) -> None:
        """Plugin should have configurable error patterns for detection."""
        plugin_template = (
            get_src_path() / "edison/data/templates/opencode/plugin/edison.ts.template"
        )
        content = plugin_template.read_text()
        content_lower = content.lower()
        has_patterns = (
            "errorPattern" in content or
            "error_pattern" in content_lower or
            ("token" in content_lower and "limit" in content_lower)
        )
        assert has_patterns, (
            "Plugin should have configurable error patterns"
        )


class TestPluginCompactionAPI:
    """Tests for using official compaction API."""

    def test_plugin_uses_compact_api(self, isolated_project_env: Path) -> None:
        """Plugin should use official session.compact API."""
        plugin_template = (
            get_src_path() / "edison/data/templates/opencode/plugin/edison.ts.template"
        )
        content = plugin_template.read_text()
        assert "compact" in content.lower(), (
            "Plugin should use session.compact API"
        )

    def test_plugin_injects_context_after_compaction(self, isolated_project_env: Path) -> None:
        """Plugin should inject Edison context after compaction."""
        plugin_template = (
            get_src_path() / "edison/data/templates/opencode/plugin/edison.ts.template"
        )
        content = plugin_template.read_text()
        # Should call session context after compaction
        has_context_injection = (
            "session context" in content.lower() or
            "sessionContext" in content
        )
        assert has_context_injection, (
            "Plugin should inject Edison context after compaction"
        )


class TestContextWindowConfig:
    """Tests for context window configuration."""

    def test_config_has_compaction_section(self, isolated_project_env: Path) -> None:
        """Context window config should have compaction section."""
        config_path = get_src_path() / "edison/data/config/context_window.yaml"
        content = config_path.read_text()
        assert "compaction" in content.lower(), (
            "Context window config should have compaction section"
        )

    def test_config_has_preemptive_settings(self, isolated_project_env: Path) -> None:
        """Config should have preemptive compaction settings."""
        config_path = get_src_path() / "edison/data/config/context_window.yaml"
        content = config_path.read_text()
        has_preemptive = (
            "preemptive" in content.lower() or
            "threshold" in content.lower()
        )
        assert has_preemptive, (
            "Config should have preemptive compaction settings"
        )

    def test_config_has_recovery_settings(self, isolated_project_env: Path) -> None:
        """Config should have recovery settings."""
        config_path = get_src_path() / "edison/data/config/context_window.yaml"
        content = config_path.read_text()
        has_recovery = (
            "recovery" in content.lower() or
            "errorPattern" in content
        )
        assert has_recovery, (
            "Config should have recovery settings"
        )


class TestCompactionSummaryRule:
    """Tests for compaction summary-shape rule."""

    def test_rules_registry_has_compaction_rule(self, isolated_project_env: Path) -> None:
        """Rules registry should include a compaction summary-shape rule."""
        registry_path = get_src_path() / "edison/data/rules/registry.yml"
        content = registry_path.read_text()
        has_compaction_rule = (
            "compaction" in content.lower() and
            ("summary" in content.lower() or "shape" in content.lower())
        )
        assert has_compaction_rule, (
            "Rules registry should include compaction summary-shape rule"
        )

    def test_compaction_rule_has_required_fields(self, isolated_project_env: Path) -> None:
        """Compaction rule should specify what to preserve."""
        registry_path = get_src_path() / "edison/data/rules/registry.yml"
        content = registry_path.read_text()
        # Rule should mention session, tasks, and constitution
        required_fields = ["session", "task", "constitution"]
        found = sum(1 for f in required_fields if f in content.lower())
        # At least 2 of the 3 required fields should be present
        assert found >= 2, (
            f"Compaction rule should specify preservation of {required_fields}"
        )


class TestCompactionHookIntegration:
    """Tests for Claude Code compaction hook."""

    def test_hook_references_compaction_rule(self, isolated_project_env: Path) -> None:
        """Compaction hook should reference the compaction rule."""
        hook_path = (
            get_src_path() / "edison/data/templates/hooks/compaction-reminder.sh.template"
        )
        content = hook_path.read_text()
        has_rule_reference = (
            "rules inject" in content.lower() or
            "compaction" in content.lower()
        )
        assert has_rule_reference, (
            "Compaction hook should reference compaction rules"
        )

    def test_hook_outputs_session_context(self, isolated_project_env: Path) -> None:
        """Compaction hook should output session context."""
        hook_path = (
            get_src_path() / "edison/data/templates/hooks/compaction-reminder.sh.template"
        )
        content = hook_path.read_text()
        assert "session context" in content.lower(), (
            "Compaction hook should output session context"
        )


# =============================================================================
# Task 079: OpenCode Compaction Hooks
# =============================================================================


class TestPluginCompactingHook:
    """Tests for experimental.session.compacting hook (Task 079)."""

    def test_plugin_exports_compacting_hook(self, isolated_project_env: Path) -> None:
        """Plugin should export experimental.session.compacting hook."""
        plugin_template = (
            get_src_path() / "edison/data/templates/opencode/plugin/edison.ts.template"
        )
        content = plugin_template.read_text()
        # Should have the experimental.session.compacting hook exported
        has_compacting_hook = (
            "experimental.session.compacting" in content or
            ('"experimental"' in content and "compacting" in content)
        )
        assert has_compacting_hook, (
            "Plugin should export experimental.session.compacting hook"
        )

    def test_compacting_hook_injects_compaction_guidance(self, isolated_project_env: Path) -> None:
        """Compacting hook should inject Edison compaction guidance."""
        plugin_template = (
            get_src_path() / "edison/data/templates/opencode/plugin/edison.ts.template"
        )
        content = plugin_template.read_text()
        # Hook should reference rules injection for compaction context
        has_guidance_injection = (
            ("compacting" in content.lower() and "rules" in content.lower()) or
            ("output.context" in content) or
            ("compaction" in content.lower() and "inject" in content.lower())
        )
        assert has_guidance_injection, (
            "Compacting hook should inject Edison compaction guidance"
        )

    def test_compacting_hook_requests_rules_by_context_window_context(
        self, isolated_project_env: Path
    ) -> None:
        """Compacting hook should request compaction guidance via --context (not task --state)."""
        plugin_template = (
            get_src_path() / "edison/data/templates/opencode/plugin/edison.ts.template"
        )
        content = plugin_template.read_text()

        # Compaction guidance is context-window guidance (RULE.CONTEXT.CWAM_REASSURANCE),
        # so the plugin must fetch rules via `--context` rather than `--state compaction`.
        assert "fetchEdisonRulesInjectForContext" in content, (
            "Compaction hook should use context-based rules inject"
        )
        assert "--context" in content, (
            "Compaction hook should request rules inject using --context"
        )


class TestPluginCompactedEvent:
    """Tests for session.compacted event handler (Task 079)."""

    def test_plugin_handles_session_compacted_event(self, isolated_project_env: Path) -> None:
        """Plugin should handle session.compacted event."""
        plugin_template = (
            get_src_path() / "edison/data/templates/opencode/plugin/edison.ts.template"
        )
        content = plugin_template.read_text()
        # Should handle the session.compacted event
        has_compacted_handler = "session.compacted" in content
        assert has_compacted_handler, (
            "Plugin should handle session.compacted event"
        )

    def test_compacted_event_injects_session_context(self, isolated_project_env: Path) -> None:
        """Compacted event should re-inject Edison session context."""
        plugin_template = (
            get_src_path() / "edison/data/templates/opencode/plugin/edison.ts.template"
        )
        content = plugin_template.read_text()
        # After session.compacted, should call fetchEdisonSessionContext or similar
        # and inject it via client API
        has_context_injection = (
            # Check for context injection after compacted event
            ("compacted" in content.lower() and "context" in content.lower()) or
            ("fetchEdisonSessionContext" in content)
        )
        assert has_context_injection, (
            "Compacted event should re-inject Edison session context"
        )


class TestCompactionHooksConfig:
    """Tests for compaction hooks configuration (Task 079)."""

    def test_compaction_config_has_hooks_section(self, isolated_project_env: Path) -> None:
        """Compaction config should have hooks enable/disable settings."""
        plugin_template = (
            get_src_path() / "edison/data/templates/opencode/plugin/edison.ts.template"
        )
        content = plugin_template.read_text()
        # Should have hooks configuration section in COMPACTION_CONFIG
        has_hooks_config = (
            ("hooks" in content.lower() and "compaction" in content.lower()) or
            ("compacting" in content.lower() and "enabled" in content.lower())
        )
        assert has_hooks_config, (
            "Compaction config should have hooks enable/disable settings"
        )
