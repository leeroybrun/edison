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


def create_repo_with_git(tmp_path: Path, name: Optional[str] = None) -> Path:
    """Create a directory with a real git repository initialized.

    Uses `git init` to create a proper git repository rather than just
    a .git directory marker. This ensures git commands like
    `git rev-parse --show-toplevel` work correctly.

    Args:
        tmp_path: Temporary directory from pytest fixture
        name: Optional subdirectory name (if None, uses tmp_path directly)

    Returns:
        Path to the repository root
    """
    from edison.core.utils.subprocess import run_with_timeout
    import subprocess

    repo = tmp_path / name if name else tmp_path
    repo.mkdir(parents=True, exist_ok=True)

    # Initialize a real git repository.
    #
    # IMPORTANT (test isolation): `run_with_timeout` normally consults TimeoutsConfig,
    # which consults ConfigManager and populates the global config cache for `repo`.
    # At this point in many tests, `.edison/config/*.yaml` has not been written yet.
    # Pass an explicit timeout to avoid priming the config cache with an incomplete
    # view of project overrides.
    run_with_timeout(
        ["git", "init", "-b", "main"],
        cwd=repo,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=30,
    )
    return repo


def create_edison_config_structure(
    repo: Path,
    defaults: Optional[dict[str, Any]] = None,
    session: Optional[dict[str, Any]] = None,
    task: Optional[dict[str, Any]] = None,
    workflow: Optional[dict[str, Any]] = None,
) -> Path:
    """Create Edison config directory structure with optional config files.

    Creates project-level config overrides at .edison/config/ (not .edison/core/config
    which is legacy). These configs override bundled defaults from
    src/edison/data/config/*.yaml.

    Args:
        repo: Repository root path
        defaults: Contents for defaults.yaml
        session: Contents for session.yaml
        task: Contents for tasks.yaml
        workflow: Contents for workflow.yaml

    Returns:
        Path to the config directory
    """
    config_dir = repo / ".edison" / "config"
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

    # Default states are loaded from tests/config/states.yaml to avoid hardcoding.
    if task_states is None or qa_states is None or session_states is None:
        from tests.config import load_states

        states = load_states()
        task_states = task_states or states["task"]["unique_dirs"]
        qa_states = qa_states or states["qa"]["unique_dirs"]
        session_states = session_states or states["session"]["unique_dirs"]

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


def create_task_file(
    repo_path: Path,
    task_id: str,
    state: str = "todo",
    session_id: Optional[str] = None,
    title: Optional[str] = None,
):
    """Create a task file using the TaskRepository.

    This helper creates real Task entities using the repository layer,
    following the NO MOCKS principle for testing real behavior.

    Args:
        repo_path: Path to the repository root
        task_id: Task identifier
        state: Task state (default: "todo")
        session_id: Optional session ID for the task
        title: Optional task title (defaults to "Task {task_id}")

    Returns:
        The created Task object
    """
    from edison.core.task.repository import TaskRepository
    from edison.core.task.models import Task
    from edison.core.entity import EntityMetadata

    repo = TaskRepository(project_root=repo_path)
    task = Task(
        id=task_id,
        state=state,
        title=title or f"Task {task_id}",
        session_id=session_id,
        metadata=EntityMetadata.create(created_by="test", session_id=session_id)
    )
    repo.save(task)
    return task


def create_qa_file(
    repo_path: Path,
    qa_id: str,
    task_id: str,
    state: str = "waiting",
    session_id: Optional[str] = None,
    title: Optional[str] = None,
):
    """Create a QA file using the QARepository.

    This helper creates real QARecord entities using the repository layer,
    following the NO MOCKS principle for testing real behavior.

    Args:
        repo_path: Path to the repository root
        qa_id: QA identifier
        task_id: Associated task ID
        state: QA state (default: "waiting")
        session_id: Optional session ID for the QA record
        title: Optional QA title (defaults to "QA {task_id}")

    Returns:
        The created QARecord object
    """
    from edison.core.qa.workflow.repository import QARepository
    from edison.core.qa.models import QARecord
    from edison.core.entity import EntityMetadata

    repo = QARepository(project_root=repo_path)
    qa = QARecord(
        id=qa_id,
        task_id=task_id,
        state=state,
        title=title or f"QA {task_id}",
        session_id=session_id,
        metadata=EntityMetadata.create(created_by="test", session_id=session_id)
    )
    repo.save(qa)
    return qa


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
