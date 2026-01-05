"""Tests for non-interactive guard Claude hook.

RED phase: These tests define the expected behavior for the optional
non-interactive guard hook for Claude Code.

Task 045 requirements:
- Optional PreToolUse hook for banned command detection
- Reads tool payload from stdin
- If Bash and matches banned: warn or block based on config
- Respects active-session gating
"""

from __future__ import annotations

from pathlib import Path

import pytest


class TestNonInteractiveGuardHookConfig:
    """Test hooks.yaml includes non-interactive-guard hook definition."""

    def test_hooks_yaml_has_non_interactive_guard(self) -> None:
        """hooks.yaml should define non-interactive-guard hook."""
        import yaml

        from edison.data import get_data_path

        hooks_path = Path(get_data_path("config")) / "hooks.yaml"
        with hooks_path.open() as f:
            data = yaml.safe_load(f)

        definitions = data.get("hooks", {}).get("definitions", {})
        assert "non-interactive-guard" in definitions, (
            "hooks.yaml should define 'non-interactive-guard' hook"
        )

    def test_non_interactive_guard_is_pretooluse(self) -> None:
        """non-interactive-guard should be PreToolUse type."""
        import yaml

        from edison.data import get_data_path

        hooks_path = Path(get_data_path("config")) / "hooks.yaml"
        with hooks_path.open() as f:
            data = yaml.safe_load(f)

        hook_def = data["hooks"]["definitions"]["non-interactive-guard"]
        assert hook_def.get("type") == "PreToolUse", (
            "non-interactive-guard should be PreToolUse type"
        )

    def test_non_interactive_guard_can_block(self) -> None:
        """non-interactive-guard should have blocking capability."""
        import yaml

        from edison.data import get_data_path

        hooks_path = Path(get_data_path("config")) / "hooks.yaml"
        with hooks_path.open() as f:
            data = yaml.safe_load(f)

        hook_def = data["hooks"]["definitions"]["non-interactive-guard"]
        # Should have blocking field (may be true or false)
        assert "blocking" in hook_def, (
            "non-interactive-guard should have 'blocking' field"
        )

    def test_non_interactive_guard_disabled_by_default(self) -> None:
        """non-interactive-guard should be disabled by default (optional)."""
        import yaml

        from edison.data import get_data_path

        hooks_path = Path(get_data_path("config")) / "hooks.yaml"
        with hooks_path.open() as f:
            data = yaml.safe_load(f)

        hook_def = data["hooks"]["definitions"]["non-interactive-guard"]
        assert hook_def.get("enabled") is False, (
            "non-interactive-guard should be disabled by default"
        )

    def test_non_interactive_guard_has_template(self) -> None:
        """non-interactive-guard should reference a template file."""
        import yaml

        from edison.data import get_data_path

        hooks_path = Path(get_data_path("config")) / "hooks.yaml"
        with hooks_path.open() as f:
            data = yaml.safe_load(f)

        hook_def = data["hooks"]["definitions"]["non-interactive-guard"]
        assert "template" in hook_def, (
            "non-interactive-guard should have 'template' field"
        )
        assert "non-interactive-guard" in hook_def["template"], (
            "template should reference non-interactive-guard template"
        )


class TestNonInteractiveGuardTemplate:
    """Test non-interactive-guard.sh.template exists and has correct structure."""

    def test_template_exists(self) -> None:
        """non-interactive-guard.sh.template should exist."""
        from edison.data import get_data_path

        template_path = (
            Path(get_data_path("templates", "hooks"))
            / "non-interactive-guard.sh.template"
        )
        assert template_path.exists(), (
            f"Template not found at {template_path}"
        )

    def test_template_sources_shared_guard(self) -> None:
        """Template should source _edison_guard.sh for session gating."""
        from edison.data import get_data_path

        template_path = (
            Path(get_data_path("templates", "hooks"))
            / "non-interactive-guard.sh.template"
        )
        content = template_path.read_text()

        assert "_edison_guard.sh" in content, (
            "Template should source shared guard"
        )
        assert "edison_hook_guard" in content, (
            "Template should call edison_hook_guard"
        )

    def test_template_reads_tool_from_stdin(self) -> None:
        """Template should read tool payload from stdin."""
        from edison.data import get_data_path

        template_path = (
            Path(get_data_path("templates", "hooks"))
            / "non-interactive-guard.sh.template"
        )
        content = template_path.read_text()

        # Should read stdin (cat or INPUT pattern)
        assert "cat" in content or "INPUT" in content, (
            "Template should read tool payload from stdin"
        )

    def test_template_checks_bash_tool(self) -> None:
        """Template should check if tool is Bash."""
        from edison.data import get_data_path

        template_path = (
            Path(get_data_path("templates", "hooks"))
            / "non-interactive-guard.sh.template"
        )
        content = template_path.read_text()

        assert "Bash" in content, (
            "Template should check for Bash tool"
        )

    def test_template_has_warn_and_block_modes(self) -> None:
        """Template should support both warn and block modes."""
        from edison.data import get_data_path

        template_path = (
            Path(get_data_path("templates", "hooks"))
            / "non-interactive-guard.sh.template"
        )
        content = template_path.read_text()

        # Should reference onMatch or different exit codes
        assert "warn" in content.lower() or "block" in content.lower(), (
            "Template should support warn/block modes"
        )

    def test_template_config_driven_patterns(self) -> None:
        """Template should use config-driven banned patterns, not hardcoded."""
        from edison.data import get_data_path

        template_path = (
            Path(get_data_path("templates", "hooks"))
            / "non-interactive-guard.sh.template"
        )
        content = template_path.read_text()

        # Should use Jinja templating for patterns (config.something or cfg.something)
        assert "config" in content.lower() or "cfg" in content.lower() or "{%" in content, (
            "Template should use config-driven patterns via Jinja"
        )


class TestNonInteractiveGuardComposition:
    """Test compose_hooks generates non-interactive-guard when enabled."""

    def test_compose_hooks_generates_guard_when_enabled(
        self, isolated_project_env: Path
    ) -> None:
        """compose_hooks should generate non-interactive-guard.sh when enabled."""
        from edison.core.adapters.components.hooks import compose_hooks

        # Enable the hook via project config
        project_config = isolated_project_env / ".edison" / "config" / "hooks.yaml"
        project_config.parent.mkdir(parents=True, exist_ok=True)
        project_config.write_text("""
hooks:
  definitions:
    non-interactive-guard:
      enabled: true
""")

        compose_hooks(repo_root=isolated_project_env)

        guard_path = isolated_project_env / ".claude" / "hooks" / "non-interactive-guard.sh"
        assert guard_path.exists(), (
            "non-interactive-guard.sh should be generated when enabled"
        )

    def test_compose_hooks_skips_guard_when_disabled(
        self, isolated_project_env: Path
    ) -> None:
        """compose_hooks should not generate non-interactive-guard.sh when disabled."""
        from edison.core.adapters.components.hooks import compose_hooks

        compose_hooks(repo_root=isolated_project_env)

        guard_path = isolated_project_env / ".claude" / "hooks" / "non-interactive-guard.sh"
        # Should not exist when disabled by default
        assert not guard_path.exists(), (
            "non-interactive-guard.sh should NOT be generated when disabled"
        )
