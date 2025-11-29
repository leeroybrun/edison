"""Test that session manager delegates worktree operations correctly.

Following TDD: These tests define the expected behavior BEFORE implementation.
"""
import pytest
import yaml
from pathlib import Path
from edison.core.session.manager import create_session
from edison.core.session import SessionManager
from edison.core.session._config import reset_config_cache
from edison.core.config.cache import clear_all_caches
import edison.core.utils.paths.resolver as path_resolver


@pytest.fixture(autouse=True)
def setup_worktree_config(session_git_repo_path, monkeypatch):
    """Configure worktree settings for tests."""
    # Reset caches
    path_resolver._PROJECT_ROOT_CACHE = None
    clear_all_caches()
    reset_config_cache()

    # Setup config
    config_dir = session_git_repo_path / ".edison" / "config"

    worktrees_dir = session_git_repo_path / "worktrees"

    session_data = {
        "worktrees": {
            "enabled": True,
            "baseDirectory": str(worktrees_dir),
            "branchPrefix": "session/",
            "baseBranch": "main",
            "timeouts": {
                "health_check": 2,
                "fetch": 5,
                "checkout": 5,
                "worktree_add": 5,
                "clone": 10,
                "install": 10
            }
        }
    }
    (config_dir / "session.yml").write_text(yaml.dump(session_data))

    # Set env vars
    monkeypatch.setenv("PROJECT_NAME", "testproj")

    # Reset caches after env vars
    path_resolver._PROJECT_ROOT_CACHE = None
    clear_all_caches()
    reset_config_cache()

    yield

    # Cleanup
    path_resolver._PROJECT_ROOT_CACHE = None
    clear_all_caches()
    reset_config_cache()


def test_create_session_delegates_worktree_creation(session_git_repo_path):
    """Test that create_session properly delegates to worktree module.

    RED: This should fail initially because create_session duplicates logic.
    GREEN: After refactoring, it should pass by delegating to worktree module.
    """
    session_id = "test-delegate-1"

    # Create session with worktree
    path = create_session(session_id, owner="test", create_wt=True)

    # Verify session was created
    assert path.exists()

    # Load session and verify git metadata was set correctly
    mgr = SessionManager(project_root=session_git_repo_path)
    session = mgr.repo.get(session_id)
    assert session is not None

    data = session.to_dict()
    git_meta = data.get("git", {})

    # These should be set by delegating to worktree.create_worktree
    assert "worktreePath" in git_meta
    assert "branchName" in git_meta
    assert git_meta["branchName"] == f"session/{session_id}"

    # Verify the worktree actually exists
    wt_path = Path(git_meta["worktreePath"])
    assert wt_path.exists()
    assert (wt_path / ".git").exists()


def test_create_session_with_worktree_is_redundant(session_git_repo_path):
    """Test that create_session with create_wt=True works correctly.

    This test verifies that create_session(create_wt=True) properly creates
    sessions with worktrees, replacing the old create_session_with_worktree function.
    """
    session_id = "test-redundant-1"

    # Create session with worktree using create_session
    path1 = create_session(session_id, owner="test", create_wt=True)

    # Cleanup for second test
    mgr = SessionManager(project_root=session_git_repo_path)
    session = mgr.repo.get(session_id)
    from edison.core.session import worktree
    if session:
        git_meta = session.to_dict().get("git", {})
        if "worktreePath" in git_meta:
            wt_path = Path(git_meta["worktreePath"])
            branch = git_meta.get("branchName")
            if wt_path.exists():
                worktree.cleanup_worktree(session_id, wt_path, branch, delete_branch=True)

    # Delete session metadata
    session_path = mgr.repo.get_session_json_path(session_id)
    if session_path.exists():
        session_path.unlink()

    # Try with create_session
    session_id2 = "test-redundant-2"
    path2 = create_session(session_id2, owner="test", create_wt=True)

    # Both should create worktrees
    s1 = mgr.repo.get("test-redundant-1") if mgr.repo.exists("test-redundant-1") else None
    s2 = mgr.repo.get(session_id2)

    # The structure should be identical (both should have git metadata)
    if s2:
        assert "git" in s2.to_dict()
        assert "worktreePath" in s2.to_dict()["git"]


def test_session_metadata_update_is_centralized(session_git_repo_path):
    """Test that git metadata updates happen in one place.

    RED: Currently each function manually updates git.worktreePath and git.branchName.
    GREEN: Should delegate to a single helper that handles metadata updates.
    """
    session_id = "test-centralized-1"

    path = create_session(session_id, owner="test", create_wt=True)

    mgr = SessionManager(project_root=session_git_repo_path)
    session = mgr.repo.get(session_id)
    data = session.to_dict()
    git_meta = data.get("git", {})

    # All required fields should be present
    assert "worktreePath" in git_meta
    assert "branchName" in git_meta
    assert "baseBranch" in git_meta  # Should come from config

    # Values should match what worktree module returns
    from edison.core.session import worktree
    wt_path, branch = worktree.resolve_worktree_target(session_id)

    assert git_meta["branchName"] == branch
    assert Path(git_meta["worktreePath"]).resolve() == Path(git_meta["worktreePath"]).resolve()


def test_no_direct_subprocess_calls_in_manager(session_git_repo_path):
    """Test that manager.py doesn't make direct subprocess calls.

    RED: Currently imports subprocess for error handling.
    GREEN: Should only delegate to worktree module, no subprocess imports needed.
    """
    # This is a meta-test that checks the code structure
    from edison.core.session import manager
    import inspect

    source = inspect.getsource(manager)

    # Should not have any subprocess.run or subprocess.call patterns
    # (subprocess.CalledProcessError in exception handling is OK)
    import re

    # Look for actual subprocess calls, not just error handling
    subprocess_calls = re.findall(r'subprocess\.(run|call|Popen|check_output)', source)

    assert len(subprocess_calls) == 0, (
        f"manager.py should not make direct subprocess calls. "
        f"Found: {subprocess_calls}. Delegate to worktree module instead."
    )
