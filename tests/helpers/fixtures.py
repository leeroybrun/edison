"""Reusable fixture factories for test setup.

This module provides factory functions to reduce duplication across tests.
Use these instead of reimplementing common setup patterns.
"""
from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Optional

from tests.helpers.io_utils import write_yaml
from tests.helpers.cache_utils import reset_edison_caches


def create_repo_with_git(tmp_path: Path) -> Path:
    """Create a directory with .git marker for git root detection.

    Args:
        tmp_path: Temporary directory from pytest fixture

    Returns:
        Path to the repository root
    """
    repo = tmp_path
    (repo / ".git").mkdir(parents=True, exist_ok=True)
    return repo


def create_edison_config_structure(
    repo: Path,
    defaults: Optional[dict[str, Any]] = None,
    session: Optional[dict[str, Any]] = None,
    task: Optional[dict[str, Any]] = None,
    workflow: Optional[dict[str, Any]] = None,
) -> Path:
    """Create Edison config directory structure with optional config files.

    Args:
        repo: Repository root path
        defaults: Contents for defaults.yaml
        session: Contents for session.yaml
        task: Contents for tasks.yaml
        workflow: Contents for workflow.yaml

    Returns:
        Path to the config directory
    """
    config_dir = repo / ".edison" / "core" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    if defaults is not None:
        write_yaml(config_dir / "defaults.yaml", defaults)
    if session is not None:
        write_yaml(config_dir / "session.yaml", session)
    if task is not None:
        write_yaml(config_dir / "tasks.yaml", task)
    if workflow is not None:
        write_yaml(config_dir / "workflow.yaml", workflow)

    return config_dir


def create_project_structure(
    repo: Path,
    task_states: Optional[list[str]] = None,
    qa_states: Optional[list[str]] = None,
    session_states: Optional[list[str]] = None,
) -> Path:
    """Create .project directory structure with state directories.

    Args:
        repo: Repository root path
        task_states: List of task state directories to create
        qa_states: List of QA state directories to create
        session_states: List of session state directories to create

    Returns:
        Path to the .project directory
    """
    project_dir = repo / ".project"

    # Default states if not provided
    task_states = task_states or ["todo", "wip", "done"]
    qa_states = qa_states or ["pending", "wip", "passed"]
    session_states = session_states or ["draft", "wip", "completed"]

    for state in task_states:
        (project_dir / "tasks" / state).mkdir(parents=True, exist_ok=True)

    for state in qa_states:
        (project_dir / "qa" / state).mkdir(parents=True, exist_ok=True)

    for state in session_states:
        (project_dir / "sessions" / state).mkdir(parents=True, exist_ok=True)

    return project_dir


def setup_isolated_repo(
    tmp_path: Path,
    monkeypatch: Any,
    config: Optional[dict[str, Any]] = None,
) -> Path:
    """Create a fully isolated repository environment for testing.

    This is the recommended way to set up test repositories.
    Combines git init, config setup, and environment variables.

    Args:
        tmp_path: Temporary directory from pytest fixture
        monkeypatch: Pytest monkeypatch fixture
        config: Optional config data to write to defaults.yaml

    Returns:
        Path to the repository root
    """
    repo = create_repo_with_git(tmp_path)

    if config is not None:
        create_edison_config_structure(repo, defaults=config)

    # Set environment variable
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))

    # Reset caches to pick up new environment
    reset_edison_caches()

    return repo


def reload_config_modules(*module_names: str) -> None:
    """Reload Edison config-dependent modules.

    Use this after changing config files to ensure modules pick up changes.

    Args:
        *module_names: Module names to reload (e.g., "edison.core.config.domains.task")
    """
    for name in module_names:
        try:
            mod = importlib.import_module(name)
            importlib.reload(mod)
        except ImportError:
            pass


# Common module sets for reloading
CONFIG_MODULES = [
    "edison.core.config.domains.task",
    "edison.core.task.paths",
    "edison.core.utils.paths.resolver",
]

SESSION_MODULES = [
    "edison.core.session._config",
    "edison.core.session.paths",
]


def reset_and_reload_config_modules() -> None:
    """Reset all caches and reload common config modules.

    Convenience function that combines cache reset with module reload.
    """
    reset_edison_caches()
    reload_config_modules(*CONFIG_MODULES)
