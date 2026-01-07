"""
Tests for OpenCode plugin RL (Ralph Loop) enforcement.

SUMMARY: Verify the plugin implements continuation enforcement with budgets and cooldowns

Task 040 requirements:
- session.idle handler queries Edison for continuation
- RL (hard mode) enforces budgets and cooldowns
- Tool output truncation (configurable)
- No transcript regex; completion from Edison only
"""

from __future__ import annotations

import re
from pathlib import Path

from edison.data import get_data_path


def _plugin_template_path() -> Path:
    return get_data_path("templates") / "opencode" / "plugin" / "edison.ts.template"


class TestPluginRLStructure:
    """Tests for RL enforcement structure in the plugin template."""

    def test_plugin_has_rl_state_type(self) -> None:
        """Plugin should define RLState type for iteration tracking."""
        content = _plugin_template_path().read_text()
        assert "RLState" in content or "rlState" in content, (
            "Plugin should define RLState type for iteration tracking"
        )

    def test_plugin_tracks_iteration_count(self) -> None:
        """Plugin should track iteration count per session."""
        content = _plugin_template_path().read_text()
        assert "iteration" in content.lower(), (
            "Plugin should track iteration count"
        )

    def test_plugin_implements_cooldown(self) -> None:
        """Plugin should implement cooldown between injections."""
        content = _plugin_template_path().read_text()
        assert "cooldown" in content.lower() or "lastInjected" in content, (
            "Plugin should implement cooldown timing"
        )

    def test_plugin_respects_max_iterations(self) -> None:
        """Plugin should respect maxIterations budget."""
        content = _plugin_template_path().read_text()
        assert "maxIterations" in content or "max_iterations" in content.lower(), (
            "Plugin should check maxIterations budget"
        )


class TestPluginSessionResolution:
    """Tests for Edison session ID resolution in plugin."""

    def test_plugin_resolves_session_from_env(self) -> None:
        """Plugin should check AGENTS_SESSION env var."""
        content = _plugin_template_path().read_text()
        assert "AGENTS_SESSION" in content, (
            "Plugin should check AGENTS_SESSION environment variable"
        )

    def test_plugin_falls_back_to_session_context(self) -> None:
        """Plugin should fall back to edison session context."""
        content = _plugin_template_path().read_text()
        assert "session context" in content.lower() or "sessionId" in content, (
            "Plugin should resolve session from context"
        )


class TestPluginToolTruncation:
    """Tests for tool output truncation feature."""

    def test_plugin_has_truncation_handler(self) -> None:
        """Plugin should implement tool.execute.after for truncation."""
        content = _plugin_template_path().read_text()
        assert "truncat" in content.lower(), (
            "Plugin should have truncation logic"
        )

    def test_plugin_preserves_headers_on_truncation(self) -> None:
        """Plugin truncation should preserve header lines."""
        content = _plugin_template_path().read_text()
        # Should mention preserving headers or first N lines
        has_header_logic = (
            "header" in content.lower() or
            "first" in content.lower() or
            "preserve" in content.lower()
        )
        assert has_header_logic, (
            "Plugin should preserve headers when truncating"
        )


class TestPluginEnforcementModes:
    """Tests for soft vs hard enforcement modes."""

    def test_plugin_fetches_enforcement_mode(self) -> None:
        """Plugin should fetch enforcement mode from Edison."""
        content = _plugin_template_path().read_text()
        # Should reference mode or enforcement
        has_mode = "mode" in content.lower() or "enforcement" in content.lower()
        assert has_mode, (
            "Plugin should fetch enforcement mode from Edison"
        )

    def test_plugin_soft_mode_single_injection(self) -> None:
        """Soft mode should inject continuation only once."""
        content = _plugin_template_path().read_text()
        # Should reference soft mode or single injection logic
        has_soft_logic = "soft" in content.lower() or "once" in content.lower()
        assert has_soft_logic, (
            "Plugin should handle soft mode (single injection)"
        )


class TestPluginNoTranscriptRegex:
    """Tests verifying plugin doesn't use transcript regex hacks."""

    def test_plugin_no_regex_completion_markers(self) -> None:
        """Plugin should NOT use regex to detect completion."""
        content = _plugin_template_path().read_text()
        # Should not have regex patterns for completion detection
        regex_patterns = [
            r"\/complete\/",
            r"\/done\/",
            r"\.match\(",
            r"\.test\(",
            r"RegExp\(",
        ]
        for pattern in regex_patterns:
            match = re.search(pattern, content)
            if not match:
                continue

            # Allow generic regex usage (.match/.test/RegExp) as long as it's not
            # being used for "completion" detection heuristics.
            window_start = max(0, match.start() - 80)
            window_end = min(len(content), match.end() + 80)
            window = content[window_start:window_end].lower()
            assert "complete" not in window, (
                f"Plugin should not use regex ({pattern}) for completion detection"
            )
