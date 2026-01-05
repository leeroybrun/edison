"""Tests for non-interactive environment guardrails configuration.

RED phase: These tests define the expected behavior for non-interactive
environment guardrails configuration in Edison.

Task 045 requirements:
- execution.nonInteractive.enabled: bool
- execution.nonInteractive.env: dict (e.g., CI=1, PAGER=cat)
- execution.nonInteractive.bannedCommandPatterns: list (strings/regex)
- execution.nonInteractive.onMatch: warn|block
"""

from __future__ import annotations

from pathlib import Path

import pytest


class TestNonInteractiveConfigSchema:
    """Test that execution.yaml defines non-interactive environment config."""

    def test_execution_config_yaml_exists(self) -> None:
        """execution.yaml should exist in bundled config."""
        from edison.data import get_data_path

        config_path = Path(get_data_path("config")) / "execution.yaml"
        assert config_path.exists(), f"execution.yaml not found at {config_path}"

    def test_execution_config_has_non_interactive_section(self) -> None:
        """execution.yaml should have nonInteractive section."""
        import yaml

        from edison.data import get_data_path

        config_path = Path(get_data_path("config")) / "execution.yaml"
        with config_path.open() as f:
            data = yaml.safe_load(f)

        assert "execution" in data, "execution.yaml should have 'execution' key"
        assert "nonInteractive" in data["execution"], (
            "execution config should have 'nonInteractive' section"
        )

    def test_non_interactive_config_has_enabled_flag(self) -> None:
        """nonInteractive section should have 'enabled' flag."""
        import yaml

        from edison.data import get_data_path

        config_path = Path(get_data_path("config")) / "execution.yaml"
        with config_path.open() as f:
            data = yaml.safe_load(f)

        non_interactive = data["execution"]["nonInteractive"]
        assert "enabled" in non_interactive, (
            "nonInteractive should have 'enabled' flag"
        )
        assert isinstance(non_interactive["enabled"], bool)

    def test_non_interactive_config_has_env_dict(self) -> None:
        """nonInteractive section should have 'env' dict for environment variables."""
        import yaml

        from edison.data import get_data_path

        config_path = Path(get_data_path("config")) / "execution.yaml"
        with config_path.open() as f:
            data = yaml.safe_load(f)

        non_interactive = data["execution"]["nonInteractive"]
        assert "env" in non_interactive, (
            "nonInteractive should have 'env' dict"
        )
        assert isinstance(non_interactive["env"], dict)

    def test_non_interactive_env_has_sensible_defaults(self) -> None:
        """env should have sensible default environment variables."""
        import yaml

        from edison.data import get_data_path

        config_path = Path(get_data_path("config")) / "execution.yaml"
        with config_path.open() as f:
            data = yaml.safe_load(f)

        env = data["execution"]["nonInteractive"]["env"]
        # Expect common non-interactive env vars
        expected_keys = ["CI", "PAGER", "GIT_PAGER"]
        for key in expected_keys:
            assert key in env, f"env should include {key}"

    def test_non_interactive_config_has_banned_patterns(self) -> None:
        """nonInteractive section should have 'bannedCommandPatterns' list."""
        import yaml

        from edison.data import get_data_path

        config_path = Path(get_data_path("config")) / "execution.yaml"
        with config_path.open() as f:
            data = yaml.safe_load(f)

        non_interactive = data["execution"]["nonInteractive"]
        assert "bannedCommandPatterns" in non_interactive, (
            "nonInteractive should have 'bannedCommandPatterns'"
        )
        assert isinstance(non_interactive["bannedCommandPatterns"], list)

    def test_banned_patterns_has_common_interactive_commands(self) -> None:
        """bannedCommandPatterns should include common interactive commands."""
        import yaml

        from edison.data import get_data_path

        config_path = Path(get_data_path("config")) / "execution.yaml"
        with config_path.open() as f:
            data = yaml.safe_load(f)

        patterns = data["execution"]["nonInteractive"]["bannedCommandPatterns"]
        patterns_str = " ".join(patterns)
        # Expect common interactive commands to be banned
        expected = ["vim", "vi", "nano", "less", "more", "top", "htop"]
        for cmd in expected:
            assert cmd in patterns_str, f"bannedCommandPatterns should include {cmd}"

    def test_non_interactive_config_has_on_match(self) -> None:
        """nonInteractive section should have 'onMatch' behavior setting."""
        import yaml

        from edison.data import get_data_path

        config_path = Path(get_data_path("config")) / "execution.yaml"
        with config_path.open() as f:
            data = yaml.safe_load(f)

        non_interactive = data["execution"]["nonInteractive"]
        assert "onMatch" in non_interactive, (
            "nonInteractive should have 'onMatch'"
        )
        assert non_interactive["onMatch"] in ("warn", "block"), (
            "onMatch should be 'warn' or 'block'"
        )

    def test_default_on_match_is_warn(self) -> None:
        """Default onMatch should be 'warn' (conservative)."""
        import yaml

        from edison.data import get_data_path

        config_path = Path(get_data_path("config")) / "execution.yaml"
        with config_path.open() as f:
            data = yaml.safe_load(f)

        on_match = data["execution"]["nonInteractive"]["onMatch"]
        assert on_match == "warn", (
            "Default onMatch should be 'warn' (conservative)"
        )


class TestExecutionConfigDomain:
    """Test ExecutionConfig domain accessor."""

    def test_execution_config_class_exists(self) -> None:
        """ExecutionConfig class should exist."""
        from edison.core.config.domains.execution import ExecutionConfig

        assert ExecutionConfig is not None

    def test_execution_config_inherits_base(self) -> None:
        """ExecutionConfig should inherit from BaseDomainConfig."""
        from edison.core.config.base import BaseDomainConfig
        from edison.core.config.domains.execution import ExecutionConfig

        assert issubclass(ExecutionConfig, BaseDomainConfig)

    def test_execution_config_has_non_interactive_enabled(
        self, isolated_project_env: Path
    ) -> None:
        """ExecutionConfig should expose non_interactive_enabled property."""
        from edison.core.config.domains.execution import ExecutionConfig

        config = ExecutionConfig(repo_root=isolated_project_env)
        # Should return bool
        assert isinstance(config.non_interactive_enabled, bool)

    def test_execution_config_has_non_interactive_env(
        self, isolated_project_env: Path
    ) -> None:
        """ExecutionConfig should expose non_interactive_env property."""
        from edison.core.config.domains.execution import ExecutionConfig

        config = ExecutionConfig(repo_root=isolated_project_env)
        # Should return dict
        assert isinstance(config.non_interactive_env, dict)

    def test_execution_config_has_banned_command_patterns(
        self, isolated_project_env: Path
    ) -> None:
        """ExecutionConfig should expose banned_command_patterns property."""
        from edison.core.config.domains.execution import ExecutionConfig

        config = ExecutionConfig(repo_root=isolated_project_env)
        # Should return list
        assert isinstance(config.banned_command_patterns, list)

    def test_execution_config_has_on_match(
        self, isolated_project_env: Path
    ) -> None:
        """ExecutionConfig should expose on_match property."""
        from edison.core.config.domains.execution import ExecutionConfig

        config = ExecutionConfig(repo_root=isolated_project_env)
        # Should return 'warn' or 'block'
        assert config.on_match in ("warn", "block")

    def test_execution_config_matches_banned_command(
        self, isolated_project_env: Path
    ) -> None:
        """ExecutionConfig should have method to check if command matches banned patterns."""
        from edison.core.config.domains.execution import ExecutionConfig

        config = ExecutionConfig(repo_root=isolated_project_env)
        # Should have is_command_banned method
        assert hasattr(config, "is_command_banned")
        # vim should be banned by default
        assert config.is_command_banned("vim file.txt")
        # normal commands should not be banned
        assert not config.is_command_banned("ls -la")

    def test_execution_config_get_matching_pattern_survives_invalid_regex(
        self, isolated_project_env: Path
    ) -> None:
        """get_matching_pattern should return the correct pattern even if some are invalid."""
        from edison.core.config.domains.execution import ExecutionConfig

        class TestExecutionConfig(ExecutionConfig):
            @property
            def non_interactive_enabled(self) -> bool:  # type: ignore[override]
                return True

            @property
            def banned_command_patterns(self) -> list[str]:  # type: ignore[override]
                return ["^(", "^vim "]

        config = TestExecutionConfig(repo_root=isolated_project_env)
        assert config.get_matching_pattern("vim file.txt") == "^vim "
