import os
import pytest
from pathlib import Path
import yaml
from edison.core.session import worktree
from edison.core.session._config import reset_config_cache
from edison.core.config.cache import clear_all_caches
from edison.core.utils.subprocess import run_with_timeout
from tests.helpers.env_setup import clear_path_caches
import sys

@pytest.fixture(autouse=True)
def setup_worktree_config(session_git_repo_path, monkeypatch):
    """Configure worktree settings for tests."""
    # Setup .edison/config
    config_dir = session_git_repo_path / ".edison" / "config"

    # Create worktrees directory path - use absolute path
    worktrees_dir = session_git_repo_path / "worktrees"

    session_data = {
        "worktrees": {
            "enabled": True,
            "baseDirectory": str(worktrees_dir),
            "branchPrefix": "session/",
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

    # Reset caches to ensure config is loaded
    clear_path_caches()
    clear_all_caches()
    reset_config_cache()

    yield

    # Cleanup
    clear_path_caches()
    clear_all_caches()
    reset_config_cache()

def test_get_worktree_base(session_git_repo_path):
    """Test base directory resolution."""
    base = worktree._get_worktree_base()
    # The base should be the worktrees directory we configured
    expected = session_git_repo_path / "worktrees"
    assert base == expected

def test_git_is_healthy(session_git_repo_path):
    """Test git health check."""
    from edison.core.utils.git.worktree import check_worktree_health
    assert check_worktree_health(session_git_repo_path) is True
    assert check_worktree_health(session_git_repo_path / "nonexistent") is False

def test_create_worktree(session_git_repo_path):
    """Test worktree creation."""
    sid = "test-session"
    # Check current branch
    r = run_with_timeout(["git", "branch", "--show-current"], cwd=session_git_repo_path, capture_output=True, text=True)
    base_branch = r.stdout.strip()
    
    wt_path, branch = worktree.create_worktree(sid, base_branch=base_branch)
    
    assert wt_path is not None
    assert branch == f"session/{sid}"
    assert wt_path.exists()
    assert (wt_path / ".git").exists()
    # Real git worktrees use a `.git` *file* pointing to the parent repo metadata.
    assert (wt_path / ".git").is_file()
    
    # Verify it's in the list
    from edison.core.utils.git.worktree import list_worktrees as git_list_worktrees
    items = git_list_worktrees()
    found = False
    for item in items:
        p = Path(item["path"])
        b = item.get("branch", "")
        if p.resolve() == wt_path.resolve() and b == branch:
            found = True
            break
    assert found

def test_create_worktree_from_dirty_non_base_branch(session_git_repo_path):
    """Creating a worktree must not require checking out the base branch in a dirty primary checkout.

    Real-world primary checkouts are often dirty (task files, logs, local tweaks). Worktree
    creation must still produce a registered git worktree (not a clone fallback).
    """
    # Create a diverged branch so switching back to main would touch tracked files.
    run_with_timeout(
        ["git", "checkout", "-b", "feature"],
        cwd=session_git_repo_path,
        check=True,
        capture_output=True,
        text=True,
    )

    readme = session_git_repo_path / "README.md"
    readme.write_text("# Test Repository (feature)\n", encoding="utf-8")
    run_with_timeout(["git", "add", "README.md"], cwd=session_git_repo_path, check=True, capture_output=True, text=True)
    run_with_timeout(["git", "commit", "-m", "feature commit"], cwd=session_git_repo_path, check=True, capture_output=True, text=True)

    # Make working tree dirty with a change that would be overwritten by checkout main.
    readme.write_text("# Test Repository (dirty)\n", encoding="utf-8")

    sid = "dirty-non-base"
    wt_path, branch = worktree.create_worktree(sid, base_branch="main")

    assert wt_path is not None
    assert branch == f"session/{sid}"
    assert wt_path.exists()
    assert (wt_path / ".git").exists()
    assert (wt_path / ".git").is_file()

    # Verify it is registered (git worktree list)
    from edison.core.utils.git.worktree import list_worktrees as git_list_worktrees
    items = git_list_worktrees()
    assert any(Path(item["path"]).resolve() == wt_path.resolve() for item in items)

def test_create_worktree_idempotent(session_git_repo_path):
    """Test that creating existing worktree returns it."""
    sid = "test-idempotent"
    r = run_with_timeout(["git", "branch", "--show-current"], cwd=session_git_repo_path, capture_output=True, text=True)
    base_branch = r.stdout.strip()
    
    p1, b1 = worktree.create_worktree(sid, base_branch=base_branch)
    p2, b2 = worktree.create_worktree(sid, base_branch=base_branch)
    
    assert p1 == p2
    assert b1 == b2

def test_cleanup_worktree(session_git_repo_path):
    """Test worktree cleanup."""
    sid = "test-cleanup"
    r = run_with_timeout(["git", "branch", "--show-current"], cwd=session_git_repo_path, capture_output=True, text=True)
    base_branch = r.stdout.strip()

    p, b = worktree.create_worktree(sid, base_branch=base_branch)
    assert p.exists()

    worktree.cleanup_worktree(sid, p, b, delete_branch=True)

    assert not p.exists()
    # Check branch is gone
    r = run_with_timeout(["git", "show-ref", "--verify", f"refs/heads/{b}"], cwd=session_git_repo_path, capture_output=True)
    assert r.returncode != 0


def test_resolve_worktree_target_consistency(session_git_repo_path):
    """Test that resolve_worktree_target returns consistent results."""
    sid = "test-resolve"

    # Call the public API function
    path1, branch1 = worktree.resolve_worktree_target(sid)
    path2, branch2 = worktree.resolve_worktree_target(sid)

    # Should be consistent
    assert path1 == path2
    assert branch1 == branch2
    assert branch1 == f"session/{sid}"
    assert path1.name == sid


def test_ensure_worktree_materialized_complete_metadata(session_git_repo_path):
    """Test that ensure_worktree_materialized returns complete git metadata."""
    sid = "test-meta"
    r = run_with_timeout(["git", "branch", "--show-current"], cwd=session_git_repo_path, capture_output=True, text=True)
    base_branch = r.stdout.strip()

    # Ensure worktree exists and get metadata
    meta = worktree.ensure_worktree_materialized(sid)

    # Should return complete metadata
    assert "worktreePath" in meta
    assert "branchName" in meta
    assert meta["worktreePath"]
    assert meta["branchName"] == f"session/{sid}"

    # The worktree should exist
    wt_path = Path(meta["worktreePath"])
    assert wt_path.exists()
    assert (wt_path / ".git").exists()


def test_archive_and_restore_worktree(session_git_repo_path):
    """Test archiving and restoring a worktree."""
    sid = "test-archive"
    r = run_with_timeout(["git", "branch", "--show-current"], cwd=session_git_repo_path, capture_output=True, text=True)
    base_branch = r.stdout.strip()

    # Create worktree
    wt_path, branch = worktree.create_worktree(sid, base_branch=base_branch)
    assert wt_path.exists()

    # Archive it
    archived_path = worktree.archive_worktree(sid, wt_path)
    assert archived_path.exists()
    assert not wt_path.exists()

    # Restore it
    restored_path = worktree.restore_worktree(sid, base_branch=base_branch)
    assert restored_path.exists()
    assert (restored_path / ".git").exists()

    # Should be back in original location
    assert restored_path == wt_path


def test_worktree_health_check_overall(session_git_repo_path):
    """Test overall worktree health check."""
    ok, notes = worktree.worktree_health_check()

    # Should be healthy with proper config
    assert ok is True
    assert len(notes) > 0
    assert any("baseDirectory" in note for note in notes)


def test_create_worktree_disabled_config(session_git_repo_path, monkeypatch):
    """Test worktree creation when disabled in config."""
    # Update config to disable worktrees
    config_dir = session_git_repo_path / ".edison" / "config"
    session_data = {
        "worktrees": {
            "enabled": False,
            "baseDirectory": str(session_git_repo_path / "worktrees"),
            "branchPrefix": "session/"
        }
    }
    (config_dir / "session.yml").write_text(yaml.dump(session_data))

    # Reset config cache
    from edison.core.session._config import reset_config_cache
    reset_config_cache()
    from edison.core.config.cache import clear_all_caches
    clear_all_caches()

    # Try to create worktree
    wt_path, branch = worktree.create_worktree("test-disabled")

    # Should return None when disabled
    assert wt_path is None
    assert branch is None


def test_list_worktrees(session_git_repo_path):
    """Test listing all worktrees."""
    sid1 = "test-list-1"
    sid2 = "test-list-2"

    r = run_with_timeout(["git", "branch", "--show-current"], cwd=session_git_repo_path, capture_output=True, text=True)
    base_branch = r.stdout.strip()

    # Create two worktrees
    wt1, br1 = worktree.create_worktree(sid1, base_branch=base_branch)
    wt2, br2 = worktree.create_worktree(sid2, base_branch=base_branch)

    # List worktrees
    wts = worktree.list_worktrees()

    # Should include both worktrees plus main repo
    assert len(wts) >= 3

    paths = [Path(w["path"]) for w in wts]
    assert any(p.resolve() == wt1.resolve() for p in paths)
    assert any(p.resolve() == wt2.resolve() for p in paths)


def test_prune_worktrees(session_git_repo_path):
    """Test pruning stale worktree references."""
    # This should not raise an error even if there's nothing to prune
    worktree.prune_worktrees()

    # Dry run should also work
    worktree.prune_worktrees(dry_run=True)


def test_worktree_sessions_directory_is_shared_symlink(session_git_repo_path):
    """Session runtime state must be shared across git worktrees.

    Git worktrees do not share untracked files. Edison stores session runtime state under
    `.project/sessions`, so we must ensure worktrees see a shared directory (via symlink),
    otherwise `edison session status/me` fails inside the worktree.
    """
    if sys.platform.startswith("win"):
        pytest.skip("Symlink semantics differ on Windows")

    # Ensure primary sessions directory exists (shared target)
    shared = session_git_repo_path / ".project" / "sessions"
    (shared / "wip").mkdir(parents=True, exist_ok=True)

    sid = "shared-sessions"
    wt_path, _ = worktree.create_worktree(sid, base_branch="main")
    assert wt_path is not None

    link = wt_path / ".project" / "sessions"
    assert link.exists()
    assert link.is_symlink()
    assert link.resolve() == shared.resolve()


def test_worktree_writes_session_id_file_for_auto_resolution(session_git_repo_path):
    """Worktrees should carry `.project/.session-id` so `edison session status` resolves without flags."""
    if sys.platform.startswith("win"):
        pytest.skip("Symlink semantics differ on Windows")

    sid = "worktree-session-id-file"
    wt_path, _ = worktree.create_worktree(sid, base_branch="main")
    assert wt_path is not None

    session_id_file = wt_path / ".project" / ".session-id"
    assert session_id_file.exists()
    assert session_id_file.read_text(encoding="utf-8").strip() == sid
