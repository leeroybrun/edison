"""Environment setup helpers for tests.

Centralizes patterns for setting up test environment variables
and ensuring proper isolation between tests.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from tests.helpers.cache_utils import reset_edison_caches


def setup_project_root(monkeypatch: Any, project_path: Path) -> None:
    """Set AGENTS_PROJECT_ROOT environment variable and reset caches.

    This is the standard way to configure an isolated project root for tests.

    Args:
        monkeypatch: Pytest monkeypatch fixture
        project_path: Path to use as project root

    Example:
        def test_something(tmp_path, monkeypatch):
            setup_project_root(monkeypatch, tmp_path)
            # Now AGENTS_PROJECT_ROOT points to tmp_path
    """
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(project_path))
    # Ensure `.edison/` resolves inside this isolated repo (some environments override it).
    monkeypatch.delenv("EDISON_paths__project_config_dir", raising=False)
    reset_edison_caches()


def setup_test_environment(
    monkeypatch: Any,
    project_root: Path,
    additional_env: dict[str, str] | None = None,
) -> None:
    """Set up complete test environment with all required variables.

    Args:
        monkeypatch: Pytest monkeypatch fixture
        project_root: Path to use as project root
        additional_env: Additional environment variables to set

    Example:
        def test_something(tmp_path, monkeypatch):
            setup_test_environment(
                monkeypatch,
                tmp_path,
                additional_env={"DEBUG": "1"}
            )
    """
    # Core project root
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(project_root))
    monkeypatch.delenv("EDISON_paths__project_config_dir", raising=False)

    # Set any additional environment variables
    if additional_env:
        for key, value in additional_env.items():
            monkeypatch.setenv(key, value)

    # Reset all caches to pick up the new environment
    reset_edison_caches()


def clear_path_caches() -> None:
    """Clear PathResolver caches explicitly.

    Use this when you need to clear path caches without a full cache reset.
    """
    try:
        import edison.core.utils.paths.resolver as resolver
        resolver._PROJECT_ROOT_CACHE = None  # type: ignore[attr-defined]
    except (ImportError, AttributeError):
        pass


def setup_session_environment(
    monkeypatch: Any,
    project_root: Path,
    session_id: str,
) -> None:
    """Set up environment for session-related tests.

    Args:
        monkeypatch: Pytest monkeypatch fixture
        project_root: Path to use as project root
        session_id: Session ID to set

    Example:
        def test_session(tmp_path, monkeypatch):
            setup_session_environment(monkeypatch, tmp_path, "test-session-001")
    """
    setup_test_environment(
        monkeypatch,
        project_root,
        additional_env={
            "AGENTS_SESSION": session_id,
        }
    )


def setup_task_environment(
    monkeypatch: Any,
    project_root: Path,
    task_id: str,
    session_id: str | None = None,
) -> None:
    """Set up environment for task-related tests.

    Args:
        monkeypatch: Pytest monkeypatch fixture
        project_root: Path to use as project root
        task_id: Task ID to set
        session_id: Optional session ID

    Example:
        def test_task(tmp_path, monkeypatch):
            setup_task_environment(monkeypatch, tmp_path, "task-123")
    """
    env = {"TASK_ID": task_id}
    if session_id:
        env["AGENTS_SESSION"] = session_id

    setup_test_environment(monkeypatch, project_root, additional_env=env)
