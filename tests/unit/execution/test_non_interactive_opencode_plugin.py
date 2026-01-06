"""Tests for non-interactive environment injection in OpenCode plugin.

RED phase: These tests define the expected behavior for non-interactive
environment injection in the OpenCode plugin.

Task 045 requirements:
- OpenCode plugin: inject env vars for Bash tool
- Detect banned commands and attach warning
- Config-driven behavior (no hardcoded values)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from edison.data import get_data_path


def _plugin_template_path() -> Path:
    return Path(get_data_path("templates")) / "opencode" / "plugin" / "edison.ts.template"


class TestOpenCodePluginNonInteractiveEnv:
    """Test OpenCode plugin injects non-interactive environment variables."""

    def test_plugin_has_tool_execute_before_handler(self) -> None:
        """Plugin should implement tool.execute.before for env injection."""
        content = _plugin_template_path().read_text()
        # Should have toolExecuteBefore or tool.execute.before
        assert "toolExecuteBefore" in content or "tool.execute.before" in content, (
            "Plugin should implement tool.execute.before handler"
        )

    def test_plugin_injects_non_interactive_env_for_bash(self) -> None:
        """Plugin should inject non-interactive env vars for Bash tool."""
        content = _plugin_template_path().read_text()
        # Should reference env injection or nonInteractive
        assert "nonInteractive" in content or "non_interactive" in content.lower(), (
            "Plugin should reference non-interactive config"
        )

    def test_plugin_fetches_non_interactive_config_from_edison(self) -> None:
        """Plugin should fetch non-interactive config from Edison."""
        content = _plugin_template_path().read_text()
        # Should call Edison config or have config fetching
        assert "edison" in content.lower() and ("config" in content.lower() or "execution" in content.lower()), (
            "Plugin should fetch config from Edison"
        )

    def test_plugin_parses_execution_config_show_json_shape(self) -> None:
        """Plugin should parse `edison config show execution --json` output shape.

        `edison config show execution --json` returns JSON like:

            {"execution": {"nonInteractive": {...}}}

        so the plugin must read `data.execution.nonInteractive` (or equivalent),
        not `data.nonInteractive`.
        """
        content = _plugin_template_path().read_text()
        assert "config\", \"show\", \"execution\"" in content, (
            "Plugin should call `edison config show execution --json`"
        )
        assert ("data?.execution" in content or "data.execution" in content) and "nonInteractive" in content, (
            "Plugin should access `execution.nonInteractive` when parsing config output"
        )


class TestOpenCodePluginBannedCommandDetection:
    """Test OpenCode plugin detects banned commands."""

    def test_plugin_checks_banned_commands(self) -> None:
        """Plugin should check commands against banned patterns."""
        content = _plugin_template_path().read_text()
        # Should reference banned patterns or command checking
        assert "isCommandBanned" in content or "bannedCommandPatterns" in content, (
            "Plugin should check banned command patterns"
        )

    def test_plugin_warns_on_banned_command(self) -> None:
        """Plugin should warn (not crash) on banned commands."""
        content = _plugin_template_path().read_text()
        # Should have warning logic, not throw/reject
        assert "warningMessage" in content or "WARNING" in content, (
            "Plugin should warn on banned commands"
        )


class TestOpenCodePluginSetupInjectsConfig:
    """Test that opencode setup generates plugin with non-interactive config."""

    def test_generated_plugin_has_non_interactive_section(
        self, isolated_project_env: Path
    ) -> None:
        """Generated plugin should have non-interactive config section."""
        from edison.cli.opencode.setup import main
        import argparse

        from edison.cli.opencode.setup import register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([
            "--repo-root", str(isolated_project_env),
            "--yes", "--json"
        ])
        rc = main(args)
        assert rc == 0

        plugin_path = isolated_project_env / ".opencode" / "plugin" / "edison.ts"
        assert plugin_path.exists()

        content = plugin_path.read_text()
        # Generated plugin should reference non-interactive config
        assert "nonInteractive" in content or "non_interactive" in content.lower() or "NON_INTERACTIVE" in content, (
            "Generated plugin should have non-interactive configuration"
        )
