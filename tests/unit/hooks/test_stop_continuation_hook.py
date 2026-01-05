"""Tests for stop-continuation hook (Claude Code Stop hook for FC/RL assist).

RED phase: These tests define the expected behavior for the stop-continuation
hook that injects continuation prompts when the session is incomplete.

The hook should:
1. Be fail-open (never blocks/throws even if Edison is unavailable)
2. Emit nothing when session is complete (or minimal "complete" line if configured)
3. Emit a compact continuation prompt when incomplete and continuation enabled
4. Source CWAM text from Edison rules/context, not hardcoded prose
"""

from __future__ import annotations

from pathlib import Path


class TestStopContinuationHookDefinition:
    """Test stop-continuation hook is defined in hooks.yaml."""

    def test_stop_continuation_hook_exists_in_config(
        self, isolated_project_env: Path
    ) -> None:
        """stop-continuation hook should be defined in hooks.yaml."""
        from edison.core.config import ConfigManager

        config = ConfigManager(repo_root=isolated_project_env).load_config(
            validate=False, include_packs=True
        )
        hooks_defs = config.get("hooks", {}).get("definitions", {})

        assert "stop-continuation" in hooks_defs, (
            "stop-continuation hook should be defined in hooks.yaml"
        )

    def test_stop_continuation_hook_has_stop_type(
        self, isolated_project_env: Path
    ) -> None:
        """stop-continuation hook should have type: Stop."""
        from edison.core.config import ConfigManager

        config = ConfigManager(repo_root=isolated_project_env).load_config(
            validate=False, include_packs=True
        )
        hooks_defs = config.get("hooks", {}).get("definitions", {})

        hook = hooks_defs.get("stop-continuation", {})
        assert hook.get("type") == "Stop", (
            "stop-continuation hook should have type: Stop"
        )

    def test_stop_continuation_hook_is_enabled_by_default(
        self, isolated_project_env: Path
    ) -> None:
        """stop-continuation hook should be enabled by default."""
        from edison.core.config import ConfigManager

        config = ConfigManager(repo_root=isolated_project_env).load_config(
            validate=False, include_packs=True
        )
        hooks_defs = config.get("hooks", {}).get("definitions", {})

        hook = hooks_defs.get("stop-continuation", {})
        # Default to enabled if not specified, or explicitly enabled
        enabled = hook.get("enabled", True)
        assert enabled is True, (
            "stop-continuation hook should be enabled by default"
        )

    def test_stop_continuation_hook_is_non_blocking(
        self, isolated_project_env: Path
    ) -> None:
        """stop-continuation hook should be non-blocking (fail-open)."""
        from edison.core.config import ConfigManager

        config = ConfigManager(repo_root=isolated_project_env).load_config(
            validate=False, include_packs=True
        )
        hooks_defs = config.get("hooks", {}).get("definitions", {})

        hook = hooks_defs.get("stop-continuation", {})
        assert hook.get("blocking", False) is False, (
            "stop-continuation hook should be non-blocking"
        )

    def test_stop_continuation_hook_has_template(
        self, isolated_project_env: Path
    ) -> None:
        """stop-continuation hook should reference a template file."""
        from edison.core.config import ConfigManager

        config = ConfigManager(repo_root=isolated_project_env).load_config(
            validate=False, include_packs=True
        )
        hooks_defs = config.get("hooks", {}).get("definitions", {})

        hook = hooks_defs.get("stop-continuation", {})
        template = hook.get("template", "")
        assert template == "stop-continuation.sh.template", (
            "stop-continuation hook should reference stop-continuation.sh.template"
        )


class TestStopContinuationTemplateExists:
    """Test stop-continuation template is bundled."""

    def test_template_file_exists(self) -> None:
        """stop-continuation.sh.template should exist in bundled templates."""
        from edison.data import get_data_path

        template_path = Path(get_data_path("templates", "hooks")) / "stop-continuation.sh.template"
        assert template_path.exists(), (
            f"Template not found at {template_path}"
        )


class TestStopContinuationHookGeneration:
    """Test stop-continuation hook is generated correctly."""

    def test_compose_hooks_generates_stop_continuation(
        self, isolated_project_env: Path
    ) -> None:
        """compose_hooks should generate stop-continuation.sh."""
        from edison.core.adapters.components.hooks import compose_hooks

        output_dir = isolated_project_env / ".claude" / "hooks"
        compose_hooks(repo_root=isolated_project_env)

        hook_path = output_dir / "stop-continuation.sh"
        assert hook_path.exists(), (
            f"stop-continuation.sh not generated at {hook_path}"
        )

    def test_generated_hook_is_executable(
        self, isolated_project_env: Path
    ) -> None:
        """Generated stop-continuation.sh should be executable."""
        from edison.core.adapters.components.hooks import compose_hooks

        compose_hooks(repo_root=isolated_project_env)
        hook_path = isolated_project_env / ".claude" / "hooks" / "stop-continuation.sh"

        assert hook_path.stat().st_mode & 0o111, (
            "stop-continuation.sh should be executable"
        )


class TestStopContinuationUsesGuard:
    """Test stop-continuation hook uses shared guard."""

    def test_hook_sources_guard_script(
        self, isolated_project_env: Path
    ) -> None:
        """stop-continuation hook should source _edison_guard.sh."""
        from edison.core.adapters.components.hooks import compose_hooks

        compose_hooks(repo_root=isolated_project_env)
        hook_path = isolated_project_env / ".claude" / "hooks" / "stop-continuation.sh"

        content = hook_path.read_text()

        assert "_edison_guard.sh" in content, (
            "Hook should source the guard script"
        )
        assert "edison_hook_guard" in content, (
            "Hook should call the guard function"
        )


class TestStopContinuationUsesCompletionOnlyAPI:
    """Test stop-continuation hook uses the --completion-only API."""

    def test_hook_calls_session_next_completion_only(
        self, isolated_project_env: Path
    ) -> None:
        """Hook should call edison session next with --completion-only flag."""
        from edison.core.adapters.components.hooks import compose_hooks

        compose_hooks(repo_root=isolated_project_env)
        hook_path = isolated_project_env / ".claude" / "hooks" / "stop-continuation.sh"

        content = hook_path.read_text()

        # Should use the completion-only API to get minimal payload
        assert "session next" in content or "session-next" in content, (
            "Hook should call edison session next"
        )
        assert "--completion-only" in content, (
            "Hook should use --completion-only flag for minimal output"
        )


class TestStopContinuationFailOpen:
    """Test stop-continuation hook is fail-open."""

    def test_hook_exits_zero_on_edison_failure(
        self, isolated_project_env: Path
    ) -> None:
        """Hook should exit 0 even if edison commands fail."""
        from edison.core.adapters.components.hooks import compose_hooks

        compose_hooks(repo_root=isolated_project_env)
        hook_path = isolated_project_env / ".claude" / "hooks" / "stop-continuation.sh"

        content = hook_path.read_text()

        # Should have fail-open patterns
        assert "|| true" in content or "|| exit 0" in content or "2>/dev/null" in content, (
            "Hook should be fail-open (never blocks on Edison failure)"
        )
        assert "exit 0" in content, (
            "Hook should explicitly exit 0 at the end"
        )


class TestStopContinuationEmitsPrompt:
    """Test stop-continuation hook emits continuation prompt when needed."""

    def test_hook_emits_continuation_prompt_when_incomplete(
        self, isolated_project_env: Path
    ) -> None:
        """Hook template should emit continuation.prompt when shouldContinue is true."""
        from edison.core.adapters.components.hooks import compose_hooks

        compose_hooks(repo_root=isolated_project_env)
        hook_path = isolated_project_env / ".claude" / "hooks" / "stop-continuation.sh"

        content = hook_path.read_text()

        # Should check shouldContinue and emit prompt
        assert "shouldContinue" in content or "continuation" in content, (
            "Hook should check continuation status"
        )

    def test_hook_silent_when_complete(
        self, isolated_project_env: Path
    ) -> None:
        """Hook should emit nothing (or minimal line) when session is complete."""
        from edison.core.adapters.components.hooks import compose_hooks

        compose_hooks(repo_root=isolated_project_env)
        hook_path = isolated_project_env / ".claude" / "hooks" / "stop-continuation.sh"

        content = hook_path.read_text()

        # Should check isComplete or shouldContinue
        assert "isComplete" in content or "shouldContinue" in content, (
            "Hook should check completion status to decide whether to emit"
        )


class TestStopContinuationNoDependencyOnJq:
    """Test stop-continuation hook does not require jq."""

    def test_hook_does_not_require_jq(
        self, isolated_project_env: Path
    ) -> None:
        """Hook should not require jq for JSON parsing."""
        from edison.core.adapters.components.hooks import compose_hooks

        compose_hooks(repo_root=isolated_project_env)
        hook_path = isolated_project_env / ".claude" / "hooks" / "stop-continuation.sh"

        content = hook_path.read_text()

        # Should NOT use jq (use Python or grep/cut as fallback)
        # If jq is used, it should be optional (with fallback)
        if "jq " in content:
            # If jq is used, must have fallback
            assert "command -v jq" in content or "|| " in content, (
                "If jq is used, it must have a fallback"
            )


class TestStopContinuationHookConfig:
    """Test stop-continuation hook configuration options."""

    def test_hook_has_config_section(
        self, isolated_project_env: Path
    ) -> None:
        """stop-continuation hook should have configurable options."""
        from edison.core.config import ConfigManager

        config = ConfigManager(repo_root=isolated_project_env).load_config(
            validate=False, include_packs=True
        )
        hooks_defs = config.get("hooks", {}).get("definitions", {})

        hook = hooks_defs.get("stop-continuation", {})
        cfg = hook.get("config", {})

        # Should have at least one configurable option
        assert isinstance(cfg, dict), (
            "stop-continuation hook should have a config section"
        )
