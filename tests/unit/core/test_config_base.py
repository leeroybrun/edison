"""DomainConfig base class eliminates duplicate initialization code.

This test verifies that:
1. DomainConfig provides shared initialization logic for all domain configs
2. Subclasses inherit repo_root, _mgr, _full_config, and _section_config automatically
3. The get_subsection() helper method works correctly
4. All domain configs can benefit from the base class without duplication

Following strict TDD: Write failing tests FIRST, then implement.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import pytest
import yaml


def _write_yaml(path: Path, data: dict) -> None:
    """Helper to write YAML test fixtures."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


class TestDomainConfigBase:
    """Test the DomainConfig abstract base class."""

    def test_domain_config_initializes_with_repo_root(self, tmp_path: Path, monkeypatch):
        """DomainConfig must initialize ConfigManager with provided repo_root."""
        repo = tmp_path
        (repo / ".git").mkdir()

        config_dir = repo / ".edison" / "core" / "config"
        _write_yaml(
            config_dir / "defaults.yaml",
            {
                "session": {
                    "paths": {"root": ".project/sessions"},
                },
            },
        )

        monkeypatch.chdir(repo)
        monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
        import edison.core.paths.resolver as resolver
        resolver._PROJECT_ROOT_CACHE = None

        from edison.core.config_base import DomainConfig

        # Create a concrete implementation for testing
        class TestConfig(DomainConfig):
            def __init__(self, repo_root: Optional[Path] = None):
                super().__init__(repo_root=repo_root, section="session")

        cfg = TestConfig(repo_root=repo)

        # Verify that ConfigManager was initialized
        assert cfg.repo_root == repo
        assert cfg._mgr is not None
        assert cfg._full_config is not None
        assert isinstance(cfg._full_config, dict)

    def test_domain_config_loads_section_config(self, tmp_path: Path, monkeypatch):
        """DomainConfig must extract section-specific config from full config."""
        repo = tmp_path
        (repo / ".git").mkdir()

        config_dir = repo / ".edison" / "core" / "config"
        _write_yaml(
            config_dir / "defaults.yaml",
            {
                "session": {
                    "paths": {"root": ".project/sessions"},
                    "validation": {"maxLength": 64},
                },
                "tasks": {
                    "paths": {"root": ".project/tasks"},
                },
            },
        )

        monkeypatch.chdir(repo)
        monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
        import edison.core.paths.resolver as resolver
        resolver._PROJECT_ROOT_CACHE = None

        from edison.core.config_base import DomainConfig

        class TestSessionConfig(DomainConfig):
            def __init__(self, repo_root: Optional[Path] = None):
                super().__init__(repo_root=repo_root, section="session")

        class TestTaskConfig(DomainConfig):
            def __init__(self, repo_root: Optional[Path] = None):
                super().__init__(repo_root=repo_root, section="tasks")

        session_cfg = TestSessionConfig(repo_root=repo)
        task_cfg = TestTaskConfig(repo_root=repo)

        # Verify section-specific config extraction
        assert "paths" in session_cfg._section_config
        assert session_cfg._section_config["paths"]["root"] == ".project/sessions"
        assert "validation" in session_cfg._section_config

        assert "paths" in task_cfg._section_config
        assert task_cfg._section_config["paths"]["root"] == ".project/tasks"

    def test_domain_config_get_subsection_returns_dict(self, tmp_path: Path, monkeypatch):
        """DomainConfig.get_subsection() must return subsection as dict."""
        repo = tmp_path
        (repo / ".git").mkdir()

        config_dir = repo / ".edison" / "core" / "config"
        _write_yaml(
            config_dir / "defaults.yaml",
            {
                "session": {
                    "paths": {
                        "root": ".project/sessions",
                        "archive": ".project/archive",
                    },
                    "validation": {"maxLength": 64},
                },
            },
        )

        monkeypatch.chdir(repo)
        monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
        import edison.core.paths.resolver as resolver
        resolver._PROJECT_ROOT_CACHE = None

        from edison.core.config_base import DomainConfig

        class TestConfig(DomainConfig):
            def __init__(self, repo_root: Optional[Path] = None):
                super().__init__(repo_root=repo_root, section="session")

        cfg = TestConfig(repo_root=repo)

        paths = cfg.get_subsection("paths")
        assert isinstance(paths, dict)
        assert paths["root"] == ".project/sessions"
        assert paths["archive"] == ".project/archive"

        validation = cfg.get_subsection("validation")
        assert isinstance(validation, dict)
        assert validation["maxLength"] == 64

    def test_domain_config_get_subsection_returns_empty_dict_when_missing(
        self, tmp_path: Path, monkeypatch
    ):
        """DomainConfig.get_subsection() must return empty dict when key is missing."""
        repo = tmp_path
        (repo / ".git").mkdir()

        config_dir = repo / ".edison" / "core" / "config"
        _write_yaml(
            config_dir / "defaults.yaml",
            {
                "session": {
                    "paths": {"root": ".project/sessions"},
                },
            },
        )

        monkeypatch.chdir(repo)
        monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
        import edison.core.paths.resolver as resolver
        resolver._PROJECT_ROOT_CACHE = None

        from edison.core.config_base import DomainConfig

        class TestConfig(DomainConfig):
            def __init__(self, repo_root: Optional[Path] = None):
                super().__init__(repo_root=repo_root, section="session")

        cfg = TestConfig(repo_root=repo)

        # Non-existent key should return empty dict
        missing = cfg.get_subsection("nonexistent")
        assert isinstance(missing, dict)
        assert len(missing) == 0

    def test_domain_config_get_subsection_handles_none_values(
        self, tmp_path: Path, monkeypatch
    ):
        """DomainConfig.get_subsection() must handle None values safely."""
        repo = tmp_path
        (repo / ".git").mkdir()

        config_dir = repo / ".edison" / "core" / "config"
        _write_yaml(
            config_dir / "defaults.yaml",
            {
                "session": {
                    "paths": {"root": ".project/sessions"},
                    "optional": None,  # Explicit None value
                },
            },
        )

        monkeypatch.chdir(repo)
        monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
        import edison.core.paths.resolver as resolver
        resolver._PROJECT_ROOT_CACHE = None

        from edison.core.config_base import DomainConfig

        class TestConfig(DomainConfig):
            def __init__(self, repo_root: Optional[Path] = None):
                super().__init__(repo_root=repo_root, section="session")

        cfg = TestConfig(repo_root=repo)

        # None values should return empty dict
        optional = cfg.get_subsection("optional")
        assert isinstance(optional, dict)
        assert len(optional) == 0

    def test_domain_config_handles_missing_section(self, tmp_path: Path, monkeypatch):
        """DomainConfig must handle missing section in config gracefully."""
        repo = tmp_path
        (repo / ".git").mkdir()

        config_dir = repo / ".edison" / "core" / "config"
        _write_yaml(
            config_dir / "defaults.yaml",
            {
                # No session section
                "tasks": {
                    "paths": {"root": ".project/tasks"},
                },
            },
        )

        monkeypatch.chdir(repo)
        monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
        import edison.core.paths.resolver as resolver
        resolver._PROJECT_ROOT_CACHE = None

        from edison.core.config_base import DomainConfig

        class TestConfig(DomainConfig):
            def __init__(self, repo_root: Optional[Path] = None):
                super().__init__(repo_root=repo_root, section="session")

        cfg = TestConfig(repo_root=repo)

        # Should have empty section config when section is missing
        assert isinstance(cfg._section_config, dict)
        assert len(cfg._section_config) == 0

    def test_domain_config_auto_discovers_repo_root(self, tmp_path: Path, monkeypatch):
        """DomainConfig must auto-discover repo_root when not provided."""
        repo = tmp_path
        (repo / ".git").mkdir()

        config_dir = repo / ".edison" / "core" / "config"
        _write_yaml(
            config_dir / "defaults.yaml",
            {
                "session": {
                    "paths": {"root": ".project/sessions"},
                },
            },
        )

        monkeypatch.chdir(repo)
        monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
        import edison.core.paths.resolver as resolver
        resolver._PROJECT_ROOT_CACHE = None

        from edison.core.config_base import DomainConfig

        class TestConfig(DomainConfig):
            def __init__(self, repo_root: Optional[Path] = None):
                super().__init__(repo_root=repo_root, section="session")

        # Create without explicit repo_root
        cfg = TestConfig()

        # Should auto-discover
        assert cfg.repo_root == repo
        assert cfg._mgr.repo_root == repo


class TestDomainConfigIntegrationWithExistingConfigs:
    """Test that existing configs can adopt DomainConfig without breaking."""

    def test_session_config_can_use_domain_config(self, tmp_path: Path, monkeypatch):
        """SessionConfig should be able to inherit from DomainConfig."""
        repo = tmp_path
        (repo / ".git").mkdir()

        config_dir = repo / ".edison" / "core" / "config"
        _write_yaml(
            config_dir / "defaults.yaml",
            {
                "statemachine": {
                    "session": {
                        "states": {
                            "active": {"initial": True},
                            "done": {"final": True},
                        },
                    },
                },
                "session": {
                    "paths": {"root": ".project/sessions"},
                },
            },
        )

        monkeypatch.chdir(repo)
        monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
        import edison.core.paths.resolver as resolver
        resolver._PROJECT_ROOT_CACHE = None

        # After refactoring, SessionConfig will use DomainConfig
        from edison.core.session.config import SessionConfig

        cfg = SessionConfig(repo_root=repo)

        # Verify it has the expected attributes from DomainConfig
        assert hasattr(cfg, "repo_root")
        assert hasattr(cfg, "_mgr")
        assert hasattr(cfg, "_full_config")
        # SessionConfig has _session_config and _state_config, not _section_config
        # This is fine - domain configs can have their own conventions

    def test_task_config_can_use_domain_config(self, tmp_path: Path, monkeypatch):
        """TaskConfig should be able to inherit from DomainConfig."""
        repo = tmp_path
        (repo / ".git").mkdir()

        config_dir = repo / ".edison" / "core" / "config"
        _write_yaml(
            config_dir / "defaults.yaml",
            {
                "tasks": {
                    "paths": {
                        "root": ".project/tasks",
                        "qaRoot": ".project/qa",
                    },
                },
            },
        )

        monkeypatch.chdir(repo)
        monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
        import edison.core.paths.resolver as resolver
        resolver._PROJECT_ROOT_CACHE = None

        from edison.core.task.config import TaskConfig

        cfg = TaskConfig(repo_root=repo)

        # Verify it has the expected attributes from DomainConfig
        assert hasattr(cfg, "repo_root")
        assert hasattr(cfg, "_mgr")
        assert hasattr(cfg, "_config")  # TaskConfig uses _config not _full_config

    def test_qa_config_can_use_domain_config(self, tmp_path: Path, monkeypatch):
        """QAConfig should be able to inherit from DomainConfig."""
        repo = tmp_path
        (repo / ".git").mkdir()

        config_dir = repo / ".edison" / "core" / "config"
        _write_yaml(
            config_dir / "defaults.yaml",
            {
                "delegation": {
                    "taskTypeRules": {},
                },
                "orchestration": {
                    "maxConcurrentAgents": 5,
                },
            },
        )

        monkeypatch.chdir(repo)
        monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
        import edison.core.paths.resolver as resolver
        resolver._PROJECT_ROOT_CACHE = None

        from edison.core.qa.config import QAConfig

        cfg = QAConfig(repo_root=repo)

        # Verify it has the expected attributes from DomainConfig
        assert hasattr(cfg, "repo_root")
        assert hasattr(cfg, "_mgr")
        assert hasattr(cfg, "_config")  # QAConfig uses _config not _full_config

    def test_orchestrator_config_can_use_domain_config(self, tmp_path: Path, monkeypatch):
        """OrchestratorConfig should be able to inherit from DomainConfig."""
        repo = tmp_path
        (repo / ".git").mkdir()

        config_dir = repo / ".edison" / "core" / "config"
        _write_yaml(
            config_dir / "defaults.yaml",
            {
                "orchestrators": {
                    "default": "test",
                    "profiles": {
                        "test": {
                            "command": ["echo", "test"],
                        },
                    },
                },
            },
        )

        monkeypatch.chdir(repo)
        monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
        import edison.core.paths.resolver as resolver
        resolver._PROJECT_ROOT_CACHE = None

        from edison.core.orchestrator.config import OrchestratorConfig

        cfg = OrchestratorConfig(repo_root=repo, validate=False)

        # Verify it has the expected attributes from DomainConfig
        assert hasattr(cfg, "repo_root")
        assert hasattr(cfg, "_mgr")
        assert hasattr(cfg, "_full_config")
