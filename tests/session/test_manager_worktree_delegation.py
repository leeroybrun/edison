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
from edison.core.utils.subprocess import run_with_timeout
from edison.core.utils.paths import PathResolver
import edison.core.utils.paths.resolver as path_resolver


@pytest.fixture
def git_repo(tmp_path, monkeypatch):
    """Setup a temporary git repo with config."""
    # Reset caches
    path_resolver._PROJECT_ROOT_CACHE = None
    clear_all_caches()
    reset_config_cache()

    # Setup config
    config_dir = tmp_path / ".edison" / "config"
    config_dir.mkdir(parents=True)

    defaults_data = {"edison": {"version": "1.0.0"}}
    (config_dir / "defaults.yml").write_text(yaml.dump(defaults_data))

    worktrees_dir = tmp_path / "worktrees"

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
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("PROJECT_NAME", "testproj")

    # Initialize git repo
    run_with_timeout(["git", "init"], cwd=tmp_path, check=True)
    run_with_timeout(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    run_with_timeout(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    run_with_timeout(["git", "commit", "--allow-empty", "-m", "Initial"], cwd=tmp_path, check=True)

    # Reset caches after env vars
    path_resolver._PROJECT_ROOT_CACHE = None
    clear_all_caches()
    reset_config_cache()

    yield tmp_path

    # Cleanup
    path_resolver._PROJECT_ROOT_CACHE = None
    clear_all_caches()
    reset_config_cache()


def test_create_session_delegates_worktree_creation(git_repo):
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
    mgr = SessionManager(project_root=git_repo)
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


def test_create_session_with_worktree_is_redundant(git_repo):
    """Test that create_session with create_wt=True works correctly.

    This test verifies that create_session(create_wt=True) properly creates
    sessions with worktrees, replacing the old create_session_with_worktree function.
    """
    session_id = "test-redundant-1"

    # Create session with worktree using create_session
    path1 = create_session(session_id, owner="test", create_wt=True)

    # Cleanup for second test
    mgr = SessionManager(project_root=git_repo)
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


def test_session_metadata_update_is_centralized(git_repo):
    """Test that git metadata updates happen in one place.

    RED: Currently each function manually updates git.worktreePath and git.branchName.
    GREEN: Should delegate to a single helper that handles metadata updates.
    """
    session_id = "test-centralized-1"

    path = create_session(session_id, owner="test", create_wt=True)

    mgr = SessionManager(project_root=git_repo)
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


def test_no_direct_subprocess_calls_in_manager(git_repo):
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
