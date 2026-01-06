"""Tests for hook session gating.

RED phase: These tests define the expected behavior for unified session gating
in Claude Code hooks. Hooks should only run when an Edison session is detected,
unless configured otherwise.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


class TestHookExecutionScopeConfig:
    """Test execution scope configuration loading."""

    def test_default_execution_scope_is_session(
        self, isolated_project_env: Path
    ) -> None:
        """Default executionScope should be 'session'."""
        from edison.core.config import ConfigManager

        config = ConfigManager(repo_root=isolated_project_env).load_config(
            validate=False, include_packs=True
        )
        hooks_settings = config.get("hooks", {}).get("settings", {})

        # Default should be 'session' (hooks only run when session detected)
        assert hooks_settings.get("executionScope") == "session"

    def test_hook_definition_can_override_execution_scope(
        self, isolated_project_env: Path
    ) -> None:
        """Individual hook definitions should be able to override executionScope."""
        from edison.core.config import ConfigManager
        import textwrap

        hooks_config_path = isolated_project_env / ".edison" / "config" / "hooks.yaml"
        hooks_config_path.parent.mkdir(parents=True, exist_ok=True)
        hooks_config_path.write_text(
            textwrap.dedent(
                """
                hooks:
                  definitions:
                    inject-session-context:
                      executionScope: always
                """
            ).lstrip(),
            encoding="utf-8",
        )

        config = ConfigManager(repo_root=isolated_project_env).load_config(
            validate=False, include_packs=True
        )
        hooks_defs = config.get("hooks", {}).get("definitions", {})

        session_context_hook = hooks_defs.get("inject-session-context", {})
        assert session_context_hook.get("executionScope") == "always"

    def test_project_wide_execution_scope_applies_to_rendered_hooks(
        self, isolated_project_env: Path
    ) -> None:
        """A project-wide executionScope should apply to hooks unless overridden.

        This ensures hook scripts can be switched from session-gated execution
        (default) to project-wide execution via config, without repeating
        `executionScope` on every hook definition.
        """
        from edison.core.adapters.components.hooks import compose_hooks
        import textwrap

        hooks_config_path = isolated_project_env / ".edison" / "config" / "hooks.yaml"
        hooks_config_path.parent.mkdir(parents=True, exist_ok=True)
        hooks_config_path.write_text(
            textwrap.dedent(
                """
                hooks:
                  settings:
                    executionScope: project
                  definitions:
                    inject-session-context:
                      executionScope: session
                """
            ).lstrip(),
            encoding="utf-8",
        )

        compose_hooks(repo_root=isolated_project_env)

        hooks_dir = isolated_project_env / ".claude" / "hooks"
        remind_tdd = (hooks_dir / "remind-tdd.sh").read_text(encoding="utf-8")
        inject_ctx = (hooks_dir / "inject-session-context.sh").read_text(encoding="utf-8")

        assert 'edison_hook_guard "remind-tdd" "project"' in remind_tdd
        assert 'edison_hook_guard "inject-session-context" "session"' in inject_ctx


class TestHookDefinitionExecutionScope:
    """Test HookDefinition includes executionScope."""

    def test_hook_definition_has_execution_scope_field(
        self, isolated_project_env: Path
    ) -> None:
        """HookDefinition dataclass should have executionScope field."""
        from edison.core.adapters.components.hooks import HookDefinition

        hook = HookDefinition(
            id="test-hook",
            type="PreToolUse",
            execution_scope="project",
        )
        assert hook.execution_scope == "project"

    def test_hook_definition_defaults_execution_scope_to_session(
        self, isolated_project_env: Path
    ) -> None:
        """HookDefinition executionScope should default to 'session'."""
        from edison.core.adapters.components.hooks import HookDefinition

        hook = HookDefinition(
            id="test-hook",
            type="PreToolUse",
        )
        assert hook.execution_scope == "session"


class TestSharedGuardTemplate:
    """Test shared guard script generation."""

    def test_guard_template_exists(self) -> None:
        """_edison_guard.sh.template should exist in bundled templates."""
        from edison.data import get_data_path

        guard_path = Path(get_data_path("templates", "hooks")) / "_edison_guard.sh.template"
        assert guard_path.exists(), f"Guard template not found at {guard_path}"

    def test_compose_hooks_generates_guard_script(
        self, isolated_project_env: Path
    ) -> None:
        """compose_hooks should generate _edison_guard.sh alongside hook scripts."""
        from edison.core.adapters.components.hooks import compose_hooks

        output_dir = isolated_project_env / ".claude" / "hooks"
        compose_hooks(repo_root=isolated_project_env)

        guard_path = output_dir / "_edison_guard.sh"
        assert guard_path.exists(), f"Guard script not generated at {guard_path}"

        # Guard should be executable
        assert guard_path.stat().st_mode & 0o111, "Guard script should be executable"

    def test_guard_script_contains_session_detection(
        self, isolated_project_env: Path
    ) -> None:
        """Guard script should contain session detection logic using Edison CLI."""
        from edison.core.adapters.components.hooks import compose_hooks

        compose_hooks(repo_root=isolated_project_env)
        guard_path = isolated_project_env / ".claude" / "hooks" / "_edison_guard.sh"

        content = guard_path.read_text()

        # Should call Edison's session detect command
        assert "edison session detect" in content or "edison_session_detect" in content

        # Should define the guard function
        assert "edison_hook_guard" in content


class TestHookTemplatesUseGuard:
    """Test that hook templates source the shared guard."""

    def test_inject_session_context_uses_guard(
        self, isolated_project_env: Path
    ) -> None:
        """inject-session-context hook should source _edison_guard.sh."""
        from edison.core.adapters.components.hooks import compose_hooks

        compose_hooks(repo_root=isolated_project_env)
        hook_path = isolated_project_env / ".claude" / "hooks" / "inject-session-context.sh"

        content = hook_path.read_text()

        # Should source the guard script
        assert "_edison_guard.sh" in content
        # Should call the guard function
        assert "edison_hook_guard" in content

    def test_compaction_reminder_uses_guard(
        self, isolated_project_env: Path
    ) -> None:
        """compaction-reminder hook should source _edison_guard.sh."""
        from edison.core.adapters.components.hooks import compose_hooks

        compose_hooks(repo_root=isolated_project_env)
        hook_path = isolated_project_env / ".claude" / "hooks" / "compaction-reminder.sh"

        content = hook_path.read_text()

        # Should source the guard script
        assert "_edison_guard.sh" in content
        # Should call the guard function
        assert "edison_hook_guard" in content

    def test_session_init_uses_guard(
        self, isolated_project_env: Path
    ) -> None:
        """session-init hook should source _edison_guard.sh."""
        from edison.core.adapters.components.hooks import compose_hooks

        compose_hooks(repo_root=isolated_project_env)
        hook_path = isolated_project_env / ".claude" / "hooks" / "session-init.sh"

        content = hook_path.read_text()

        # Should source the guard script
        assert "_edison_guard.sh" in content
        # Should call the guard function
        assert "edison_hook_guard" in content


class TestGuardBehavior:
    """Test guard script behavior in different scenarios."""

    def test_guard_exits_zero_when_no_session_and_scope_session(
        self, isolated_project_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Guard should exit 0 (skip hook) when no session and scope is 'session'."""
        import subprocess

        from edison.core.adapters.components.hooks import compose_hooks

        compose_hooks(repo_root=isolated_project_env)
        guard_path = isolated_project_env / ".claude" / "hooks" / "_edison_guard.sh"

        # Clear session env vars
        monkeypatch.delenv("AGENTS_SESSION", raising=False)
        monkeypatch.delenv("EDISON_SESSION_ID", raising=False)

        # Run guard with scope=session in a directory without session
        result = subprocess.run(
            ["bash", "-c", f'source "{guard_path}" && edison_hook_guard "test-hook" "session"'],
            cwd=isolated_project_env,
            capture_output=True,
            text=True,
        )

        # Should exit 0 (skip hook)
        assert result.returncode == 0

    def test_guard_continues_when_session_detected_and_scope_session(
        self, isolated_project_env: Path
    ) -> None:
        """Guard should continue (not exit) when session detected and scope is 'session'."""
        import subprocess

        from edison.core.adapters.components.hooks import compose_hooks
        from tests.helpers.session import ensure_session

        # Create a session
        session_id = "test-guard-session"
        ensure_session(session_id, state="active")

        compose_hooks(repo_root=isolated_project_env)
        guard_path = isolated_project_env / ".claude" / "hooks" / "_edison_guard.sh"

        # Write session ID to simulate active session
        session_file = isolated_project_env / ".project" / ".session-id"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(session_id)

        # Test script that sources guard, calls guard function, then echoes CONTINUED
        result = subprocess.run(
            [
                "bash", "-c",
                f'''
                source "{guard_path}"
                edison_hook_guard "test-hook" "session"
                echo "CONTINUED"
                '''
            ],
            cwd=isolated_project_env,
            capture_output=True,
            text=True,
            env={**dict(__import__("os").environ), "AGENTS_SESSION": session_id},
        )

        # Script should continue past guard and print CONTINUED
        assert "CONTINUED" in result.stdout

    def test_guard_continues_when_scope_project(
        self, isolated_project_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Guard should continue when scope is 'project' (even without session)."""
        import subprocess

        from edison.core.adapters.components.hooks import compose_hooks

        compose_hooks(repo_root=isolated_project_env)
        guard_path = isolated_project_env / ".claude" / "hooks" / "_edison_guard.sh"

        # Clear session env vars
        monkeypatch.delenv("AGENTS_SESSION", raising=False)
        monkeypatch.delenv("EDISON_SESSION_ID", raising=False)

        # Test with scope=project
        result = subprocess.run(
            [
                "bash", "-c",
                f'''
                source "{guard_path}"
                edison_hook_guard "test-hook" "project"
                echo "CONTINUED"
                '''
            ],
            cwd=isolated_project_env,
            capture_output=True,
            text=True,
        )

        # Script should continue past guard
        assert "CONTINUED" in result.stdout


class TestHookComposerPassesScope:
    """Test HookComposer passes executionScope to templates."""

    def test_render_hook_includes_execution_scope_in_context(
        self, isolated_project_env: Path
    ) -> None:
        """render_hook should include executionScope in template context."""
        from edison.core.adapters.components.hooks import HookComposer, HookDefinition
        from edison.core.adapters.base import PlatformAdapter

        class TestAdapter(PlatformAdapter):
            @property
            def platform_name(self) -> str:
                return "test"

            def sync_all(self) -> dict[str, Any]:
                return {}

        adapter = TestAdapter(project_root=isolated_project_env)
        composer = HookComposer(adapter.context)

        hook_def = HookDefinition(
            id="test-hook",
            type="SessionStart",
            template="session-init.sh.template",
            execution_scope="project",
        )

        rendered = composer.render_hook(hook_def)

        # The rendered hook should call guard with the correct scope
        assert "project" in rendered or "edison_hook_guard" in rendered


class TestNoAdHocSessionDetection:
    """Test that hooks don't contain ad-hoc session detection logic."""

    def test_inject_task_rules_no_adhoc_session_check(
        self, isolated_project_env: Path
    ) -> None:
        """inject-task-rules should not have ad-hoc .session-id checks."""
        from edison.core.adapters.components.hooks import compose_hooks

        compose_hooks(repo_root=isolated_project_env)
        hook_path = isolated_project_env / ".claude" / "hooks" / "inject-task-rules.sh"

        content = hook_path.read_text()

        # Should NOT have ad-hoc session file checks
        assert ".session-id" not in content
        # Should use the unified guard instead
        assert "edison_hook_guard" in content

    def test_hooks_no_duplicate_detection_logic(
        self, isolated_project_env: Path
    ) -> None:
        """Hook templates should not duplicate session detection logic."""
        from edison.core.adapters.components.hooks import compose_hooks

        compose_hooks(repo_root=isolated_project_env)
        hooks_dir = isolated_project_env / ".claude" / "hooks"

        for hook_file in hooks_dir.glob("*.sh"):
            if hook_file.name == "_edison_guard.sh":
                continue

            content = hook_file.read_text()

            # Check for ad-hoc detection patterns that should not be duplicated
            # (these should only be in _edison_guard.sh)
            assert "detect_session_id" not in content, (
                f"{hook_file.name} should use edison_hook_guard instead of detect_session_id"
            )
