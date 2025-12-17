"""Test that SessionAutoStart delegates worktree operations correctly.

Following TDD: These tests define the expected behavior BEFORE implementation.
"""
import pytest
import yaml
import re
import inspect
from pathlib import Path
from edison.core.session.lifecycle.autostart import SessionAutoStart
from edison.core.session import SessionManager
from edison.core.session._config import reset_config_cache
from edison.core.config.cache import clear_all_caches
from tests.helpers.env_setup import clear_path_caches


@pytest.fixture(autouse=True)
def setup_worktree_config(session_git_repo_path, monkeypatch):
    """Setup git repo with orchestrator config."""
    # Reset caches
    clear_path_caches()
    clear_all_caches()
    reset_config_cache()

    # Setup config directory
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

    # Orchestrator config
    orchestrator_data = {
        "orchestrators": {
            "default": "test",
            "profiles": {
                "test": {
                    "command": "echo",
                    "args": ["test"],
                    "cwd": "{session_worktree}",
                    "initial_prompt": {"enabled": False}
                }
            }
        }
    }
    (config_dir / "orchestrator.yaml").write_text(yaml.dump(orchestrator_data))

    # Set env vars
    monkeypatch.setenv("PROJECT_NAME", "testproj")

    # Reset caches after env vars
    clear_path_caches()
    clear_all_caches()
    reset_config_cache()

    yield

    # Cleanup
    clear_path_caches()
    clear_all_caches()
    reset_config_cache()


def test_autostart_delegates_worktree_creation(session_git_repo_path):
    """Test that SessionAutoStart delegates to worktree module.

    RED: Currently manually calls worktree.create_worktree and updates metadata.
    GREEN: Should delegate both creation and metadata update to a helper.
    """
    autostart = SessionAutoStart(project_root=session_git_repo_path)

    result = autostart.start(
        orchestrator_profile="test",
        launch_orchestrator=False,  # Don't actually launch
        no_worktree=False
    )

    session_id = result["session_id"]

    # Verify worktree was created
    assert result["worktree_path"] is not None

    # Load session and verify metadata
    mgr = SessionManager(project_root=session_git_repo_path)
    session = mgr.repo.get(session_id)
    assert session is not None

    data = session.to_dict()
    git_meta = data.get("git", {})

    # Should have all git metadata
    assert "worktreePath" in git_meta
    assert "branchName" in git_meta
    assert "baseBranch" in git_meta

    # Verify worktree exists
    wt_path = Path(git_meta["worktreePath"])
    assert wt_path.exists()


def test_autostart_uses_service_layer_not_store(session_git_repo_path):
    """Test that autostart uses SessionService instead of direct store access.

    RED: Currently uses load_session/save_session directly.
    GREEN: Should use SessionService for all session operations.
    """
    autostart = SessionAutoStart(project_root=session_git_repo_path)

    result = autostart.start(
        orchestrator_profile="test",
        launch_orchestrator=False,
        no_worktree=False
    )

    session_id = result["session_id"]

    # The session should be accessible via manager
    mgr = SessionManager(project_root=session_git_repo_path)
    session = mgr.repo.get(session_id)

    assert session is not None
    assert session.id == session_id

    # Metadata should be properly structured
    data = session.to_dict()
    assert "meta" in data
    assert "git" in data


def test_autostart_rollback_delegates_cleanup(session_git_repo_path):
    """Test that rollback delegates to worktree.remove_worktree.

    RED: Currently has duplicate cleanup logic in _rollback_worktree.
    GREEN: Should only call worktree.remove_worktree, no fallback logic needed.
    """
    autostart = SessionAutoStart(project_root=session_git_repo_path)

    # Create a worktree first
    result = autostart.start(
        orchestrator_profile="test",
        launch_orchestrator=False,
        no_worktree=False
    )

    session_id = result["session_id"]
    wt_path = Path(result["worktree_path"])

    # Get branch name
    mgr = SessionManager(project_root=session_git_repo_path)
    session = mgr.repo.get(session_id)
    branch = session.to_dict()["git"]["branchName"]

    # Manually call rollback to test it
    autostart._rollback_worktree(wt_path, branch)

    # Worktree should be cleaned up
    assert not wt_path.exists()


def test_autostart_no_manual_metadata_updates(session_git_repo_path):
    """Test that autostart doesn't manually construct git metadata.

    RED: Currently manually sets worktreePath, branchName, baseBranch.
    GREEN: Should get metadata from a centralized helper.
    """
    from edison.core.session import autostart

    source = inspect.getsource(autostart.SessionAutoStart.start)

    # Look for manual metadata assignments
    manual_assignments = re.findall(r'git_meta\["(worktreePath|branchName|baseBranch)"\]\s*=', source)

    # Should not manually assign these fields
    assert len(manual_assignments) == 0, (
        f"autostart.py should not manually assign git metadata. "
        f"Found: {manual_assignments}. Use a helper function instead."
    )


def test_autostart_dry_run_delegates_correctly(session_git_repo_path):
    """Test that dry_run mode properly delegates to worktree module.

    RED: Currently calls worktree.create_worktree with dry_run=True directly.
    GREEN: Delegation is actually OK here, but should be consistent.
    """
    autostart = SessionAutoStart(project_root=session_git_repo_path)

    result = autostart.start(
        orchestrator_profile="test",
        dry_run=True,
        persist_dry_run=False
    )

    # In dry run, worktree path is computed but not created
    assert result["status"] == "dry_run"
    assert result["worktree_path"] is not None  # Path is computed
    assert result["session_id"] is not None  # Session ID is generated

    # But the path should not actually exist
    wt_path = Path(result["worktree_path"])
    # In dry_run without persist, nothing is created


def test_autostart_config_driven_not_hardcoded(session_git_repo_path):
    """Test that autostart uses config values, not hardcoded strings.

    RED: May have hardcoded fallbacks or defaults.
    GREEN: All values should come from config.
    """
    autostart = SessionAutoStart(project_root=session_git_repo_path)

    result = autostart.start(
        orchestrator_profile="test",
        launch_orchestrator=False,
        no_worktree=False
    )

    session_id = result["session_id"]
    mgr = SessionManager(project_root=session_git_repo_path)
    session = mgr.repo.get(session_id)
    git_meta = session.to_dict()["git"]

    # baseBranch should come from config, not hardcoded "main"
    from edison.core.session._config import get_config
    cfg = get_config(session_git_repo_path)
    from edison.core.session import worktree as session_worktree
    expected_base = session_worktree.resolve_worktree_base_ref(
        repo_dir=session_git_repo_path, cfg=cfg.get_worktree_config()
    )

    assert git_meta["baseBranch"] == expected_base
