"""Tests for qa validate timeout override arguments.

The --timeout and --timeout-multiplier flags allow operators to override
default validator timeouts for LLM CLIs that may take longer.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from edison.cli.qa.validate import register_args


class TestValidateTimeoutArgs:
    """Test timeout argument registration and parsing."""

    def test_register_args_adds_timeout_flag(self) -> None:
        """register_args should add --timeout flag."""
        parser = argparse.ArgumentParser()
        register_args(parser)

        # Parse with --timeout
        args = parser.parse_args(["test-task", "--timeout", "600"])
        assert args.timeout == 600

    def test_register_args_adds_timeout_multiplier_flag(self) -> None:
        """register_args should add --timeout-multiplier flag."""
        parser = argparse.ArgumentParser()
        register_args(parser)

        # Parse with --timeout-multiplier
        args = parser.parse_args(["test-task", "--timeout-multiplier", "2.5"])
        assert args.timeout_multiplier == 2.5

    def test_timeout_default_is_none(self) -> None:
        """Default timeout should be None (use config defaults)."""
        parser = argparse.ArgumentParser()
        register_args(parser)

        args = parser.parse_args(["test-task"])
        assert args.timeout is None

    def test_timeout_multiplier_default_is_none(self) -> None:
        """Default timeout_multiplier should be None (no multiplier)."""
        parser = argparse.ArgumentParser()
        register_args(parser)

        args = parser.parse_args(["test-task"])
        assert args.timeout_multiplier is None

    def test_timeout_and_multiplier_together(self) -> None:
        """Both timeout and multiplier can be specified together."""
        parser = argparse.ArgumentParser()
        register_args(parser)

        args = parser.parse_args([
            "test-task",
            "--timeout", "1200",
            "--timeout-multiplier", "1.5",
        ])
        assert args.timeout == 1200
        assert args.timeout_multiplier == 1.5


class TestValidateTimeoutPassthrough:
    """Test that timeout args are passed through to executor."""

    def test_executor_receives_timeout_override(
        self, isolated_project_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ValidationExecutor should receive timeout override from CLI."""
        from edison.core.qa.engines import ValidationExecutor

        # Track what parameters executor.execute receives
        captured_kwargs: dict = {}

        original_execute = ValidationExecutor.execute

        def mock_execute(self, **kwargs):
            captured_kwargs.update(kwargs)
            # Return a minimal result to avoid actual execution
            from edison.core.qa.engines.executor import ExecutionResult
            return ExecutionResult(
                task_id=kwargs.get("task_id", "test"),
                session_id=kwargs.get("session_id", "test"),
                round_num=1,
            )

        monkeypatch.setattr(ValidationExecutor, "execute", mock_execute)

        from edison.cli.qa.validate import main
        import argparse

        args = argparse.Namespace(
            task_id="test-task",
            session=None,
            round=None,
            new_round=False,
            wave=None,
            validators=None,
            add_validators=None,
            blocking_only=False,
            execute=True,
            check_only=False,
            sequential=False,
            dry_run=False,
            max_workers=4,
            worktree_path=None,
            json=False,
            repo_root=str(isolated_project_env),
            timeout=1800,  # 30 minutes
            timeout_multiplier=None,
        )

        # This should pass timeout through to executor
        main(args)

        assert captured_kwargs.get("timeout") == 1800

    def test_executor_receives_timeout_multiplier(
        self, isolated_project_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ValidationExecutor should receive timeout_multiplier from CLI."""
        from edison.core.qa.engines import ValidationExecutor

        captured_kwargs: dict = {}

        def mock_execute(self, **kwargs):
            captured_kwargs.update(kwargs)
            from edison.core.qa.engines.executor import ExecutionResult
            return ExecutionResult(
                task_id=kwargs.get("task_id", "test"),
                session_id=kwargs.get("session_id", "test"),
                round_num=1,
            )

        monkeypatch.setattr(ValidationExecutor, "execute", mock_execute)

        from edison.cli.qa.validate import main
        import argparse

        args = argparse.Namespace(
            task_id="test-task",
            session=None,
            round=None,
            new_round=False,
            wave=None,
            validators=None,
            add_validators=None,
            blocking_only=False,
            execute=True,
            check_only=False,
            sequential=False,
            dry_run=False,
            max_workers=4,
            worktree_path=None,
            json=False,
            repo_root=str(isolated_project_env),
            timeout=None,
            timeout_multiplier=2.0,
        )

        main(args)

        assert captured_kwargs.get("timeout_multiplier") == 2.0


class TestExecutorTimeoutHandling:
    """Test that executor applies timeout settings correctly."""

    def test_executor_uses_override_timeout(
        self, isolated_project_env: Path
    ) -> None:
        """Executor should use override timeout when provided."""
        from edison.core.qa.engines import ValidationExecutor

        executor = ValidationExecutor(
            project_root=isolated_project_env,
        )

        # Get effective timeout for a validator
        effective = executor._get_effective_timeout(
            validator_timeout=300,  # config default
            override_timeout=1800,  # CLI override
            timeout_multiplier=None,
        )

        assert effective == 1800

    def test_executor_applies_timeout_multiplier(
        self, isolated_project_env: Path
    ) -> None:
        """Executor should multiply timeout when multiplier provided."""
        from edison.core.qa.engines import ValidationExecutor

        executor = ValidationExecutor(
            project_root=isolated_project_env,
        )

        effective = executor._get_effective_timeout(
            validator_timeout=300,
            override_timeout=None,
            timeout_multiplier=2.0,
        )

        assert effective == 600  # 300 * 2.0

    def test_executor_override_takes_precedence_over_multiplier(
        self, isolated_project_env: Path
    ) -> None:
        """Override timeout should take precedence over multiplier."""
        from edison.core.qa.engines import ValidationExecutor

        executor = ValidationExecutor(
            project_root=isolated_project_env,
        )

        effective = executor._get_effective_timeout(
            validator_timeout=300,
            override_timeout=1800,  # Explicit override
            timeout_multiplier=2.0,  # Also has multiplier
        )

        # Override should win
        assert effective == 1800

    def test_executor_uses_config_default_when_no_override(
        self, isolated_project_env: Path
    ) -> None:
        """Executor should use config timeout when no override."""
        from edison.core.qa.engines import ValidationExecutor

        executor = ValidationExecutor(
            project_root=isolated_project_env,
        )

        effective = executor._get_effective_timeout(
            validator_timeout=300,
            override_timeout=None,
            timeout_multiplier=None,
        )

        assert effective == 300


class TestTimeoutPropagationToEngine:
    """Test that timeout is actually propagated to the CLI engine at runtime."""

    def test_cli_engine_receives_effective_timeout(
        self, isolated_project_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CLI engine.run() should receive effective timeout from executor.

        This is the critical integration test - verifies the timeout is actually
        used when running validators, not just computed by _get_effective_timeout().
        """
        from edison.core.qa.engines.cli import CLIEngine

        # Track what timeout the CLI engine receives
        captured_timeout: list[int | None] = []

        original_run = CLIEngine.run

        def mock_run(self, validator, task_id, session_id, worktree_path,
                     round_num=None, evidence_service=None, timeout=None):
            captured_timeout.append(timeout)
            # Return a minimal result
            from edison.core.qa.engines.base import ValidationResult
            return ValidationResult(
                validator_id=validator.id,
                verdict="pending",
                summary="Test mock",
            )

        monkeypatch.setattr(CLIEngine, "run", mock_run)

        # Also need to mock can_execute to return True
        monkeypatch.setattr(CLIEngine, "can_execute", lambda self: True)

        from edison.core.qa.engines import ValidationExecutor

        executor = ValidationExecutor(project_root=isolated_project_env)

        # Execute with explicit timeout override
        executor.execute(
            task_id="test-task",
            session_id="test-session",
            timeout=1800,  # 30 minutes
            timeout_multiplier=None,
        )

        # The CLI engine should receive the effective timeout
        assert len(captured_timeout) > 0, "CLI engine.run() was never called"
        assert captured_timeout[0] == 1800, (
            f"Expected timeout=1800 but got timeout={captured_timeout[0]}"
        )

    def test_cli_engine_receives_multiplied_timeout(
        self, isolated_project_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CLI engine should receive timeout multiplied from executor."""
        from edison.core.qa.engines.cli import CLIEngine
        from edison.core.registries.validators import ValidatorRegistry

        # Get a validator's default timeout to compute expected result
        registry = ValidatorRegistry(project_root=isolated_project_env)
        validator = registry.get("global-codex")
        assert validator is not None
        default_timeout = validator.timeout

        captured_timeout: list[int | None] = []

        def mock_run(self, validator, task_id, session_id, worktree_path,
                     round_num=None, evidence_service=None, timeout=None):
            captured_timeout.append(timeout)
            from edison.core.qa.engines.base import ValidationResult
            return ValidationResult(
                validator_id=validator.id,
                verdict="pending",
                summary="Test mock",
            )

        monkeypatch.setattr(CLIEngine, "run", mock_run)
        monkeypatch.setattr(CLIEngine, "can_execute", lambda self: True)

        from edison.core.qa.engines import ValidationExecutor

        executor = ValidationExecutor(project_root=isolated_project_env)

        # Execute with timeout multiplier
        executor.execute(
            task_id="test-task",
            session_id="test-session",
            timeout=None,
            timeout_multiplier=2.0,
        )

        # The CLI engine should receive multiplied timeout
        assert len(captured_timeout) > 0, "CLI engine.run() was never called"
        expected = int(default_timeout * 2.0)
        assert captured_timeout[0] == expected, (
            f"Expected timeout={expected} (default={default_timeout} * 2.0) "
            f"but got timeout={captured_timeout[0]}"
        )


class TestLLMCLIDefaultTimeouts:
    """Test that LLM CLIs have appropriate default timeouts."""

    def test_codex_cli_has_large_default_timeout(
        self, isolated_project_env: Path
    ) -> None:
        """Codex CLI should have 15+ minute default timeout."""
        from edison.core.registries.validators import ValidatorRegistry

        registry = ValidatorRegistry(project_root=isolated_project_env)
        validator = registry.get("global-codex")

        # Codex validators should have large timeout (at least 10 minutes)
        assert validator is not None
        assert validator.timeout >= 600  # At least 10 minutes

    def test_claude_cli_has_large_default_timeout(
        self, isolated_project_env: Path
    ) -> None:
        """Claude CLI should have reasonable default timeout."""
        from edison.core.registries.validators import ValidatorRegistry

        registry = ValidatorRegistry(project_root=isolated_project_env)
        validator = registry.get("global-claude")

        # Claude validators should have reasonable timeout
        assert validator is not None
        assert validator.timeout >= 300  # At least 5 minutes
