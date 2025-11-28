"""Test that hardcoded .project paths have been removed.

This test verifies that all path construction uses config-driven
path resolution via get_management_paths() instead of hardcoded strings.
"""
import tempfile
from pathlib import Path
import pytest


@pytest.fixture(autouse=True)
def clear_path_caches():
    """Clear all path caches before each test."""
    import edison.core.task.paths as task_paths
    from edison.core.utils.paths import management

    # Clear task_paths caches
    task_paths._ROOT_CACHE = None
    task_paths._SESSION_CONFIG_CACHE = None
    task_paths._TASK_CONFIG_CACHE = None
    task_paths._TASK_ROOT_CACHE = None
    task_paths._QA_ROOT_CACHE = None
    task_paths._SESSIONS_ROOT_CACHE = None
    task_paths._TASK_DIRS_CACHE = None
    task_paths._QA_DIRS_CACHE = None
    task_paths._SESSION_DIRS_CACHE = None
    task_paths._PREFIX_CACHE = None

    # Clear management paths singleton
    management._paths_instance = None

    yield

    # Clear again after test
    task_paths._ROOT_CACHE = None
    task_paths._SESSION_CONFIG_CACHE = None
    task_paths._TASK_CONFIG_CACHE = None
    task_paths._TASK_ROOT_CACHE = None
    task_paths._QA_ROOT_CACHE = None
    task_paths._SESSIONS_ROOT_CACHE = None
    task_paths._TASK_DIRS_CACHE = None
    task_paths._QA_DIRS_CACHE = None
    task_paths._SESSION_DIRS_CACHE = None
    task_paths._PREFIX_CACHE = None
    management._paths_instance = None


def test_task_repository_no_hardcoded_project_paths(tmp_path, monkeypatch):
    """Test TaskRepository uses config-driven paths, not hardcoded .project."""
    from edison.core.task.repository import TaskRepository
    from edison.core.utils.paths import get_management_paths, PathResolver

    # Create custom management dir via config
    project_root = tmp_path / "test_project"
    project_root.mkdir()

    # Create custom config with different management dir
    config_dir = project_root / ".edison"
    config_dir.mkdir()
    config_file = config_dir / "config.yml"
    config_file.write_text("management_dir: .custom_mgmt\n")

    # Mock PathResolver to return our test project root
    monkeypatch.setattr(PathResolver, "resolve_project_root", lambda: project_root)

    # Initialize repository
    repo = TaskRepository(project_root=project_root)

    # Get management paths
    mgmt = get_management_paths(project_root)
    expected_sessions_wip = mgmt.get_session_state_dir("wip") / "test-session"

    # Test that _resolve_session_task_path uses config path
    # This should create dirs under .custom_mgmt, NOT .project
    task_path = repo._resolve_session_task_path("T-001", "test-session", "wip")

    # Verify path uses custom management dir
    assert ".custom_mgmt" in str(task_path), f"Path should use .custom_mgmt: {task_path}"
    assert ".project" not in str(task_path), f"Path should NOT use hardcoded .project: {task_path}"

    # Verify it matches expected path structure
    # Path should be: .custom_mgmt/sessions/wip/test-session/tasks/wip/T-001.md
    assert task_path.parent.name == "wip"  # task state
    assert task_path.parent.parent.name == "tasks"  # tasks directory
    assert task_path.parent.parent.parent.name == "test-session"  # session ID


def test_qa_repository_no_hardcoded_project_paths(tmp_path, monkeypatch):
    """Test QARepository uses config-driven paths, not hardcoded .project."""
    from edison.core.qa.repository import QARepository
    from edison.core.utils.paths import get_management_paths, PathResolver

    # Create custom management dir via config
    project_root = tmp_path / "test_project"
    project_root.mkdir()

    # Create custom config with different management dir
    config_dir = project_root / ".edison"
    config_dir.mkdir()
    config_file = config_dir / "config.yml"
    config_file.write_text("management_dir: .custom_mgmt\n")

    # Mock PathResolver to return our test project root
    monkeypatch.setattr(PathResolver, "resolve_project_root", lambda: project_root)

    # Initialize repository
    repo = QARepository(project_root=project_root)

    # Get management paths
    mgmt = get_management_paths(project_root)
    expected_sessions_wip = mgmt.get_session_state_dir("wip") / "test-session"

    # Test that _resolve_session_qa_path uses config path
    qa_path = repo._resolve_session_qa_path("T-001-qa", "test-session", "wip")

    # Verify path uses custom management dir
    assert ".custom_mgmt" in str(qa_path), f"Path should use .custom_mgmt: {qa_path}"
    assert ".project" not in str(qa_path), f"Path should NOT use hardcoded .project: {qa_path}"

    # Verify it matches expected path structure
    # Path should be: .custom_mgmt/sessions/wip/test-session/qa/wip/T-001-qa.md
    assert qa_path.parent.name == "wip"  # QA state
    assert qa_path.parent.parent.name == "qa"  # qa directory
    assert qa_path.parent.parent.parent.name == "test-session"  # session ID


def test_session_current_no_hardcoded_project_paths(tmp_path, monkeypatch):
    """Test session current module uses config-driven paths, not hardcoded .project."""
    from edison.core.session.current import _get_session_id_file
    from edison.core.utils.paths import get_management_paths, PathResolver

    # Create custom management dir via config
    project_root = tmp_path / "test_project"
    project_root.mkdir()

    # Create custom config
    config_dir = project_root / ".edison"
    config_dir.mkdir()
    config_file = config_dir / "config.yml"
    config_file.write_text("management_dir: .custom_mgmt\n")

    # Mock is_worktree to return True
    from edison.core.session import current
    monkeypatch.setattr(current, "_is_in_worktree", lambda: True)

    # Mock PathResolver to return our test project root
    monkeypatch.setattr(PathResolver, "resolve_project_root", lambda: project_root)

    # Get the session ID file path
    session_file = _get_session_id_file()

    # Verify path uses custom management dir
    assert session_file is not None
    assert ".custom_mgmt" in str(session_file), f"Path should use .custom_mgmt: {session_file}"
    assert ".project" not in str(session_file), f"Path should NOT use hardcoded .project: {session_file}"

    # Verify it matches expected structure
    mgmt = get_management_paths(project_root)
    expected_file = mgmt.get_management_root() / ".session-id"
    assert session_file == expected_file
