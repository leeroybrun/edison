"""Tests for CLI engine environment policy configuration.

The envPolicy feature allows config-driven control over how environment
variables are handled when executing validator CLI subprocesses.

Policies:
- inherit: Pass through all env vars from parent process
- denylist: Pass through all except configured denylist (default)
- clean: Start with minimal env (PATH, HOME only), add configured allowlist
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
import yaml

from edison.core.qa.engines.base import EngineConfig


def _write_validation_config(root: Path, engines_config: dict[str, Any]) -> None:
    """Write validation config with engine env policy settings."""
    cfg_dir = root / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    # Also need orchestration to allow CLI engines
    (cfg_dir / "orchestration.yml").write_text(
        "orchestration:\n"
        "  allowCliEngines: true\n",
        encoding="utf-8",
    )
    (cfg_dir / "validators.yml").write_text(
        yaml.safe_dump({"validation": {"engines": engines_config}}),
        encoding="utf-8",
    )


class TestEnvPolicyConfigParsing:
    """Test parsing of envPolicy configuration in EngineConfig."""

    def test_engine_config_parses_env_policy_inherit(self) -> None:
        """EngineConfig should parse envPolicy: inherit."""
        config = EngineConfig.from_dict(
            "test-engine",
            {
                "type": "cli",
                "command": "test",
                "envPolicy": {"mode": "inherit"},
            },
        )
        assert config.env_policy is not None
        assert config.env_policy.mode == "inherit"

    def test_engine_config_parses_env_policy_denylist(self) -> None:
        """EngineConfig should parse envPolicy: denylist with custom vars."""
        config = EngineConfig.from_dict(
            "test-engine",
            {
                "type": "cli",
                "command": "test",
                "envPolicy": {
                    "mode": "denylist",
                    "denylist": ["SECRET_KEY", "API_TOKEN"],
                },
            },
        )
        assert config.env_policy is not None
        assert config.env_policy.mode == "denylist"
        assert "SECRET_KEY" in config.env_policy.denylist
        assert "API_TOKEN" in config.env_policy.denylist

    def test_engine_config_parses_env_policy_clean(self) -> None:
        """EngineConfig should parse envPolicy: clean with allowlist."""
        config = EngineConfig.from_dict(
            "test-engine",
            {
                "type": "cli",
                "command": "test",
                "envPolicy": {
                    "mode": "clean",
                    "allowlist": ["PATH", "HOME", "LANG"],
                },
            },
        )
        assert config.env_policy is not None
        assert config.env_policy.mode == "clean"
        assert "PATH" in config.env_policy.allowlist
        assert "HOME" in config.env_policy.allowlist

    def test_engine_config_default_env_policy_is_denylist(self) -> None:
        """EngineConfig should default to denylist mode with session vars."""
        config = EngineConfig.from_dict(
            "test-engine",
            {
                "type": "cli",
                "command": "test",
            },
        )
        assert config.env_policy is not None
        assert config.env_policy.mode == "denylist"
        # Default denylist should include Edison session vars
        assert "AGENTS_SESSION" in config.env_policy.denylist
        assert "EDISON_SESSION_ID" in config.env_policy.denylist

    def test_engine_config_denylist_extends_defaults(self) -> None:
        """Custom denylist should extend (not replace) default session vars."""
        config = EngineConfig.from_dict(
            "test-engine",
            {
                "type": "cli",
                "command": "test",
                "envPolicy": {
                    "mode": "denylist",
                    "denylist": ["CUSTOM_SECRET"],
                },
            },
        )
        assert config.env_policy is not None
        # Should have both custom AND default vars
        assert "CUSTOM_SECRET" in config.env_policy.denylist
        assert "AGENTS_SESSION" in config.env_policy.denylist


class TestEnvPolicyAppliedToSubprocess:
    """Test that envPolicy is applied when building subprocess environment."""

    def test_inherit_policy_passes_all_env_vars(
        self, isolated_project_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """inherit policy should pass through all env vars."""
        _write_validation_config(
            isolated_project_env,
            {
                "test-cli": {
                    "type": "cli",
                    "command": "echo",
                    "envPolicy": {"mode": "inherit"},
                }
            },
        )

        from edison.core.qa.engines.cli import CLIEngine
        from edison.core.qa.engines.base import EngineConfig

        config = EngineConfig.from_dict(
            "test-cli",
            {
                "type": "cli",
                "command": "echo",
                "envPolicy": {"mode": "inherit"},
            },
        )
        engine = CLIEngine(config, project_root=isolated_project_env)

        # Set a test var that should be inherited
        monkeypatch.setenv("TEST_INHERIT_VAR", "test_value")
        monkeypatch.setenv("AGENTS_SESSION", "session-123")

        env = engine._build_subprocess_env(isolated_project_env)

        assert env.get("TEST_INHERIT_VAR") == "test_value"
        # Even session vars should be inherited with inherit policy
        assert env.get("AGENTS_SESSION") == "session-123"

    def test_denylist_policy_removes_configured_vars(
        self, isolated_project_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """denylist policy should remove configured vars but keep others."""
        from edison.core.qa.engines.cli import CLIEngine
        from edison.core.qa.engines.base import EngineConfig

        config = EngineConfig.from_dict(
            "test-cli",
            {
                "type": "cli",
                "command": "echo",
                "envPolicy": {
                    "mode": "denylist",
                    "denylist": ["SECRET_VAR"],
                },
            },
        )
        engine = CLIEngine(config, project_root=isolated_project_env)

        monkeypatch.setenv("SECRET_VAR", "should_be_removed")
        monkeypatch.setenv("NORMAL_VAR", "should_remain")
        monkeypatch.setenv("AGENTS_SESSION", "session-123")

        env = engine._build_subprocess_env(isolated_project_env)

        assert "SECRET_VAR" not in env
        assert env.get("NORMAL_VAR") == "should_remain"
        # Default session vars should also be removed
        assert "AGENTS_SESSION" not in env

    def test_clean_policy_only_includes_allowlist(
        self, isolated_project_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """clean policy should only include allowlist vars."""
        from edison.core.qa.engines.cli import CLIEngine
        from edison.core.qa.engines.base import EngineConfig

        config = EngineConfig.from_dict(
            "test-cli",
            {
                "type": "cli",
                "command": "echo",
                "envPolicy": {
                    "mode": "clean",
                    "allowlist": ["PATH", "HOME", "ALLOWED_VAR"],
                },
            },
        )
        engine = CLIEngine(config, project_root=isolated_project_env)

        monkeypatch.setenv("ALLOWED_VAR", "should_be_included")
        monkeypatch.setenv("NOT_ALLOWED", "should_be_excluded")

        env = engine._build_subprocess_env(isolated_project_env)

        assert env.get("ALLOWED_VAR") == "should_be_included"
        assert "NOT_ALLOWED" not in env
        # PATH and HOME should always be included in clean mode
        assert "PATH" in env

    def test_default_denylist_includes_edison_session_vars(
        self, isolated_project_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Default denylist should include Edison/Agents session vars."""
        from edison.core.qa.engines.cli import CLIEngine
        from edison.core.qa.engines.base import EngineConfig

        config = EngineConfig.from_dict(
            "test-cli",
            {"type": "cli", "command": "echo"},
        )
        engine = CLIEngine(config, project_root=isolated_project_env)

        # Set Edison session vars that should be scrubbed
        monkeypatch.setenv("AGENTS_SESSION", "session-123")
        monkeypatch.setenv("EDISON_SESSION_ID", "session-456")
        monkeypatch.setenv("PAL_WORKING_DIR", "/some/path")
        monkeypatch.setenv("EDISON_ACTOR_ID", "actor-1")
        monkeypatch.setenv("EDISON_ACTOR_ROLE", "validator")

        env = engine._build_subprocess_env(isolated_project_env)

        # All session-related vars should be removed
        assert "AGENTS_SESSION" not in env
        assert "EDISON_SESSION_ID" not in env
        assert "PAL_WORKING_DIR" not in env
        assert "EDISON_ACTOR_ID" not in env
        assert "EDISON_ACTOR_ROLE" not in env


class TestEnvPolicyFromRegistry:
    """Test that env policy is correctly loaded from registry config."""

    def test_registry_loads_engine_with_env_policy(
        self, isolated_project_env: Path
    ) -> None:
        """EngineRegistry should load engines with envPolicy from config."""
        _write_validation_config(
            isolated_project_env,
            {
                "custom-cli": {
                    "type": "cli",
                    "command": "custom",
                    "envPolicy": {
                        "mode": "clean",
                        "allowlist": ["PATH", "HOME", "CUSTOM_VAR"],
                    },
                }
            },
        )

        from edison.core.qa.engines.registry import EngineRegistry

        registry = EngineRegistry(project_root=isolated_project_env)
        engine = registry._get_or_create_engine("custom-cli")

        assert engine is not None
        assert engine.config.env_policy is not None
        assert engine.config.env_policy.mode == "clean"
        assert "CUSTOM_VAR" in engine.config.env_policy.allowlist
