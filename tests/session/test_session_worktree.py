import os
import pytest
import subprocess
from pathlib import Path
import yaml
from edison.core.session import worktree
from edison.core.session._config import reset_config_cache
from edison.core.utils.subprocess import run_with_timeout

@pytest.fixture
def git_repo(tmp_path, monkeypatch):
    """
    Sets up a temporary git repo and configures environment variables.
    """
    # Setup .edison/core/config
    config_dir = tmp_path / ".edison" / "core" / "config"
    config_dir.mkdir(parents=True)
    
    defaults_data = {"edison": {"version": "1.0.0"}}
    (config_dir / "defaults.yaml").write_text(yaml.dump(defaults_data))
    
    session_data = {
        "worktrees": {
            "enabled": True,
            "baseDirectory": str(tmp_path / "worktrees"),
            "branchPrefix": "session/",
            "timeouts": {
                "health_check": 2, # Short timeout for tests
                "fetch": 5,
                "checkout": 5,
                "worktree_add": 5,
                "clone": 10,
                "install": 10
            }
        }
    }
    (config_dir / "session.yaml").write_text(yaml.dump(session_data))
    
    # Set env vars
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("project_ROOT", str(tmp_path))
    monkeypatch.setenv("PROJECT_NAME", "testproj")
    
    # Initialize git repo
    repo_dir = tmp_path
    run_with_timeout(["git", "init"], cwd=repo_dir, check=True)
    run_with_timeout(["git", "config", "user.email", "you@example.com"], cwd=repo_dir, check=True)
    run_with_timeout(["git", "config", "user.name", "Your Name"], cwd=repo_dir, check=True)
    run_with_timeout(["git", "commit", "--allow-empty", "-m", "Initial commit"], cwd=repo_dir, check=True)
    
    # Reset config cache to pick up new settings
    reset_config_cache()
    
    return repo_dir

def test_get_worktree_base(git_repo):
    """Test base directory resolution."""
    base = worktree._get_worktree_base()
    assert base == git_repo / "worktrees"

def test_git_is_healthy(git_repo):
    """Test git health check."""
    assert worktree._git_is_healthy(git_repo) is True
    assert worktree._git_is_healthy(git_repo / "nonexistent") is False

def test_create_worktree(git_repo):
    """Test worktree creation."""
    sid = "test-session"
    wt_path, branch = worktree.create_worktree(sid, base_branch="master") # master is default in old git, main in new. 
    # Check what default branch is. 'Initial commit' usually on master or main.
    # Let's check current branch.
    r = run_with_timeout(["git", "branch", "--show-current"], cwd=git_repo, capture_output=True, text=True)
    base_branch = r.stdout.strip()
    
    wt_path, branch = worktree.create_worktree(sid, base_branch=base_branch)
    
    assert wt_path is not None
    assert branch == f"session/{sid}"
    assert wt_path.exists()
    assert (wt_path / ".git").exists()
    
    # Verify it's in the list
    items = worktree._git_list_worktrees()
    # items is list of (path, branch)
    # We need to resolve paths to compare
    found = False
    for p, b in items:
        if p.resolve() == wt_path.resolve() and b == branch:
            found = True
            break
    assert found

def test_create_worktree_idempotent(git_repo):
    """Test that creating existing worktree returns it."""
    sid = "test-idempotent"
    r = run_with_timeout(["git", "branch", "--show-current"], cwd=git_repo, capture_output=True, text=True)
    base_branch = r.stdout.strip()
    
    p1, b1 = worktree.create_worktree(sid, base_branch=base_branch)
    p2, b2 = worktree.create_worktree(sid, base_branch=base_branch)
    
    assert p1 == p2
    assert b1 == b2

def test_cleanup_worktree(git_repo):
    """Test worktree cleanup."""
    sid = "test-cleanup"
    r = run_with_timeout(["git", "branch", "--show-current"], cwd=git_repo, capture_output=True, text=True)
    base_branch = r.stdout.strip()
    
    p, b = worktree.create_worktree(sid, base_branch=base_branch)
    assert p.exists()
    
    worktree.cleanup_worktree(sid, p, b, delete_branch=True)
    
    assert not p.exists()
    # Check branch is gone
    r = run_with_timeout(["git", "show-ref", "--verify", f"refs/heads/{b}"], cwd=git_repo, capture_output=True)
    assert r.returncode != 0