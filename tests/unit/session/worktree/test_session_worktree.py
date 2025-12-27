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
    meta_dir = worktrees_dir / "_meta"

    session_data = {
        "worktrees": {
            "enabled": True,
            "baseDirectory": str(worktrees_dir),
            "branchPrefix": "session/",
            "sharedState": {
                "mode": "meta",
                "metaBranch": "edison-meta",
                "metaPathTemplate": str(meta_dir),
                # Do not override sharedPaths defaults here; tests that need overrides
                # should modify `session.yml` explicitly.
            },
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

    # Ensure meta worktree exists, then seed shared target.
    meta = worktree.ensure_meta_worktree()
    shared = Path(meta["meta_path"]) / ".project" / "sessions"
    (shared / "wip").mkdir(parents=True, exist_ok=True)

    sid = "shared-sessions"
    wt_path, _ = worktree.create_worktree(sid, base_branch="main")
    assert wt_path is not None

    link = wt_path / ".project" / "sessions"
    assert link.exists()
    assert link.is_symlink()
    assert link.resolve() == shared.resolve()


def test_worktree_management_dirs_are_shared_symlinks(session_git_repo_path):
    """Project management state must be shared across git worktrees.

    Git worktrees do not share untracked files. Edison stores project management state under
    `.project/*` (tasks, QA, logs, archive, sessions). Worktrees must see the same directories
    via symlinks so that task/QA commands work identically from inside the worktree.
    """
    if sys.platform.startswith("win"):
        pytest.skip("Symlink semantics differ on Windows")

    meta = worktree.ensure_meta_worktree()
    shared_root = Path(meta["meta_path"]) / ".project"
    shared_tasks = shared_root / "tasks"
    shared_qa = shared_root / "qa"
    shared_logs = shared_root / "logs"
    shared_archive = shared_root / "archive"
    shared_sessions = shared_root / "sessions"

    (shared_tasks / "todo").mkdir(parents=True, exist_ok=True)
    (shared_qa / "waiting").mkdir(parents=True, exist_ok=True)
    (shared_logs / "edison").mkdir(parents=True, exist_ok=True)
    shared_archive.mkdir(parents=True, exist_ok=True)
    (shared_sessions / "wip").mkdir(parents=True, exist_ok=True)

    sid = "shared-mgmt-dirs"
    wt_path, _ = worktree.create_worktree(sid, base_branch="main")
    assert wt_path is not None

    for rel, shared in [
        ("tasks", shared_tasks),
        ("qa", shared_qa),
        ("logs", shared_logs),
        ("archive", shared_archive),
        ("sessions", shared_sessions),
    ]:
        link = wt_path / ".project" / rel
        assert link.exists()
        assert link.is_symlink()
        assert link.resolve() == shared.resolve()


def test_worktree_project_generated_dir_is_shared_symlink(session_git_repo_path):
    """Composed project artifacts must be visible inside a session worktree.

    Edison-generated project artifacts live under `<project-config-dir>/_generated` and are
    referenced by start prompts and constitutions. Git worktrees do not share untracked files,
    so the worktree must link to the primary checkout's generated directory.
    """
    if sys.platform.startswith("win"):
        pytest.skip("Symlink semantics differ on Windows")

    from edison.core.utils.paths.project import get_project_config_dir

    project_cfg_dir = get_project_config_dir(session_git_repo_path, create=True)
    shared = (project_cfg_dir / "_generated").resolve()
    shared.mkdir(parents=True, exist_ok=True)

    sid = "shared-generated"
    wt_path, _ = worktree.create_worktree(sid, base_branch="main")
    assert wt_path is not None

    link = (wt_path / project_cfg_dir.name / "_generated")
    assert link.exists()
    assert link.is_symlink()
    assert link.resolve() == shared.resolve()


def test_worktree_retargets_existing_symlinks_when_shared_root_changes(session_git_repo_path):
    """Existing symlinks should be retargeted to the configured shared root.

    Projects may migrate from primary-shared to meta-shared state. Worktrees that already
    have `.project/*` symlinks must be corrected when `create_worktree()` runs again.
    """
    if sys.platform.startswith("win"):
        pytest.skip("Symlink semantics differ on Windows")

    sid = "retarget-links"
    wt_path, _ = worktree.create_worktree(sid, base_branch="main")
    assert wt_path is not None

    # Force a wrong target (primary repo .project) for a shared subdir symlink.
    wrong_shared = (session_git_repo_path / ".project" / "tasks").resolve()
    wrong_shared.mkdir(parents=True, exist_ok=True)

    link = wt_path / ".project" / "tasks"
    if link.exists() or link.is_symlink():
        try:
            link.unlink()
        except Exception:
            pass
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(wrong_shared, target_is_directory=True)

    # Re-run create_worktree (idempotent) - should fix the link to point at meta.
    wt2, _ = worktree.create_worktree(sid, base_branch="main")
    assert wt2 is not None

    expected = (session_git_repo_path / "worktrees" / "_meta" / ".project" / "tasks").resolve()
    assert (wt2 / ".project" / "tasks").resolve() == expected


def test_worktree_config_deep_merges_shared_state_defaults(session_git_repo_path):
    """Overriding `worktrees.sharedState` must not discard nested defaults.

    Project configs commonly override only `sharedState.mode`/paths. Edison must keep
    defaults like `gitExcludes` and `commitGuard` unless explicitly overridden.
    """
    from edison.core.config.domains.session import SessionConfig

    cfg = SessionConfig(repo_root=session_git_repo_path).get_worktree_config()
    ss = cfg.get("sharedState") or {}

    assert "gitExcludes" in ss
    assert "commitGuard" in ss
    assert ss["gitExcludes"]["session"] == [".project/", ".edison/_generated/"]


def test_create_worktree_applies_worktree_local_git_excludes(session_git_repo_path):
    """Session worktrees should write worktree-local excludes for shared state.

    Shared `.project/*` symlinks are visible inside the session worktree but must not
    show up as untracked noise; Edison should use worktree-local excludes (info/exclude).
    """
    if sys.platform.startswith("win"):
        pytest.skip("Git worktree exclude paths differ on Windows")

    sid = "git-excludes"
    wt_path, _ = worktree.create_worktree(sid, base_branch="main")
    assert wt_path is not None

    cp = run_with_timeout(
        ["git", "config", "--worktree", "--get", "core.excludesFile"],
        cwd=wt_path,
        capture_output=True,
        text=True,
        check=False,
    )
    excludes_file_raw = (cp.stdout or "").strip()
    assert excludes_file_raw, "Expected Edison to configure core.excludesFile for this worktree"
    exclude_file = Path(excludes_file_raw).expanduser().resolve()
    assert exclude_file.exists()
    contents = exclude_file.read_text(encoding="utf-8")
    assert ".project/" in contents.splitlines()


def test_create_worktree_writes_excludes_for_shared_path_symlinks(session_git_repo_path):
    """Configured shared path symlinks should not show as untracked noise.

    Git treats a symlink as a file, so excluding only `.specify/` does not ignore a `.specify`
    symlink. Edison should write exclude patterns that ignore the symlink path itself.
    """
    if sys.platform.startswith("win"):
        pytest.skip("Git worktree exclude paths differ on Windows")

    config_path = session_git_repo_path / ".edison" / "config" / "session.yml"
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["worktrees"]["sharedState"]["sharedPaths"] = [{"path": ".specify", "scopes": ["session"]}]
    config_path.write_text(yaml.dump(data), encoding="utf-8")
    clear_path_caches()
    clear_all_caches()
    reset_config_cache()

    sid = "git-excludes-shared-path"
    wt_path, _ = worktree.create_worktree(sid, base_branch="main")
    assert wt_path is not None
    assert (wt_path / ".specify").is_symlink()

    cp = run_with_timeout(
        ["git", "config", "--worktree", "--get", "core.excludesFile"],
        cwd=wt_path,
        capture_output=True,
        text=True,
        check=False,
    )
    excludes_file_raw = (cp.stdout or "").strip()
    assert excludes_file_raw, "Expected Edison to configure core.excludesFile for this worktree"
    exclude_file = Path(excludes_file_raw).expanduser().resolve()
    assert exclude_file.exists()
    contents = exclude_file.read_text(encoding="utf-8").splitlines()
    assert ".specify" in contents


def test_ensure_meta_worktree_installs_commit_guard_hook(session_git_repo_path):
    """Meta worktree should install a pre-commit hook to keep meta branch clean."""
    if sys.platform.startswith("win"):
        pytest.skip("Symlink semantics differ on Windows")

    status = worktree.ensure_meta_worktree()
    meta_path = Path(status["meta_path"])
    assert meta_path.exists()

    hooks_path_cp = run_with_timeout(
        ["git", "rev-parse", "--path-format=absolute", "--git-path", "hooks/pre-commit"],
        cwd=meta_path,
        capture_output=True,
        text=True,
        check=True,
    )
    hook_path = Path((hooks_path_cp.stdout or "").strip())
    if not hook_path.is_absolute():
        hook_path = (meta_path / hook_path).resolve()
    assert hook_path.exists()

    hook_text = hook_path.read_text(encoding="utf-8")
    assert "EDISON_META_COMMIT_GUARD" in hook_text
    assert ".project/tasks/" in hook_text
    assert ".project/qa/" in hook_text

    # The guard should block commits outside the allow list (e.g., README.md)
    (meta_path / "README.md").write_text("# Modified\n", encoding="utf-8")
    run_with_timeout(["git", "add", "README.md"], cwd=meta_path, check=True, capture_output=True, text=True)
    commit = run_with_timeout(
        ["git", "commit", "-m", "should be blocked"],
        cwd=meta_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert commit.returncode != 0


def test_meta_commit_guard_includes_configured_shared_paths(session_git_repo_path):
    """Meta commit guard should automatically allow configured sharedPaths.

    sharedPaths are the set of repo-root paths that are intended to be meta-managed and
    symlinked into primary/session worktrees. The meta branch should be able to commit
    those paths without requiring a second, duplicated allowlist.
    """
    if sys.platform.startswith("win"):
        pytest.skip("Symlink semantics differ on Windows")

    # Configure sharedPaths but leave commitGuard allowPrefixes empty.
    config_path = session_git_repo_path / ".edison" / "config" / "session.yml"
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["worktrees"]["sharedState"]["sharedPaths"] = [
        {"path": ".pal", "scopes": ["primary", "session"]},
        {"path": ".claude", "scopes": ["primary", "session"]},
        {"path": ".coderabbit.yaml", "type": "file", "scopes": ["primary", "session"]},
    ]
    if "commitGuard" not in (data.get("worktrees", {}).get("sharedState", {}) or {}):
        data["worktrees"]["sharedState"]["commitGuard"] = {"enabled": True, "allowPrefixes": []}
    else:
        data["worktrees"]["sharedState"]["commitGuard"]["allowPrefixes"] = []
    config_path.write_text(yaml.dump(data), encoding="utf-8")

    clear_path_caches()
    clear_all_caches()
    reset_config_cache()

    status = worktree.ensure_meta_worktree()
    meta_path = Path(status["meta_path"])
    assert meta_path.exists()

    hooks_path_cp = run_with_timeout(
        ["git", "rev-parse", "--path-format=absolute", "--git-path", "hooks/pre-commit"],
        cwd=meta_path,
        capture_output=True,
        text=True,
        check=True,
    )
    hook_path = Path((hooks_path_cp.stdout or "").strip())
    if not hook_path.is_absolute():
        hook_path = (meta_path / hook_path).resolve()
    assert hook_path.exists()

    hook_text = hook_path.read_text(encoding="utf-8")
    assert "EDISON_META_COMMIT_GUARD" in hook_text
    assert ".pal/" in hook_text
    assert ".claude/" in hook_text
    assert ".coderabbit.yaml" in hook_text


def test_meta_commit_guard_dedupes_allow_prefixes(session_git_repo_path):
    """Meta commit guard should not emit duplicate allow prefixes.

    Users may include sharedPaths entries in commitGuard.allowPrefixes (historical config).
    The generated hook should remain stable and avoid duplicating identical prefixes.
    """
    if sys.platform.startswith("win"):
        pytest.skip("Symlink semantics differ on Windows")

    config_path = session_git_repo_path / ".edison" / "config" / "session.yml"
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["worktrees"]["sharedState"]["sharedPaths"] = [{"path": ".pal", "scopes": ["primary", "session"]}]
    data["worktrees"]["sharedState"]["commitGuard"] = {
        "enabled": True,
        "allowPrefixes": [".project/tasks/", ".project/qa/", ".pal/"],
    }
    config_path.write_text(yaml.dump(data), encoding="utf-8")

    clear_path_caches()
    clear_all_caches()
    reset_config_cache()

    status = worktree.ensure_meta_worktree()
    meta_path = Path(status["meta_path"])

    hooks_path_cp = run_with_timeout(
        ["git", "rev-parse", "--path-format=absolute", "--git-path", "hooks/pre-commit"],
        cwd=meta_path,
        capture_output=True,
        text=True,
        check=True,
    )
    hook_path = Path((hooks_path_cp.stdout or "").strip())
    if not hook_path.is_absolute():
        hook_path = (meta_path / hook_path).resolve()
    hook_text = hook_path.read_text(encoding="utf-8")

    # The ALLOW_PREFIXES block uses one prefix per line like: '  ".pal/"'
    assert hook_text.splitlines().count('  ".pal/"') == 1


def test_meta_commit_guard_supports_subpath_allowlist_for_shared_dirs(session_git_repo_path):
    """A shared dir may be non-committable by default but allow specific subpaths.

    Example: `.codex` contains runtime state (auth/history/logs) that must not be committed,
    but `.codex/prompts/` should be committable and tracked in meta.
    """
    if sys.platform.startswith("win"):
        pytest.skip("Symlink semantics differ on Windows")

    config_path = session_git_repo_path / ".edison" / "config" / "session.yml"
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["worktrees"]["sharedState"]["sharedPaths"] = [
        {
            "path": ".codex",
            "scopes": ["primary", "session"],
            "commitAllowed": False,
            "commitAllowPrefixes": [".codex/prompts/"],
        }
    ]
    data["worktrees"]["sharedState"]["commitGuard"] = {"enabled": True, "allowPrefixes": []}
    config_path.write_text(yaml.dump(data), encoding="utf-8")

    clear_path_caches()
    clear_all_caches()
    reset_config_cache()

    status = worktree.ensure_meta_worktree()
    meta_path = Path(status["meta_path"])

    hooks_path_cp = run_with_timeout(
        ["git", "rev-parse", "--path-format=absolute", "--git-path", "hooks/pre-commit"],
        cwd=meta_path,
        capture_output=True,
        text=True,
        check=True,
    )
    hook_path = Path((hooks_path_cp.stdout or "").strip())
    if not hook_path.is_absolute():
        hook_path = (meta_path / hook_path).resolve()
    hook_text = hook_path.read_text(encoding="utf-8")

    # Ensure base dir is NOT allowed (only explicit sub-prefix is).
    assert '  ".codex/"' not in hook_text.splitlines()
    assert ".codex/prompts/" in hook_text


def test_meta_git_excludes_ignore_codex_noise_but_not_prompts(session_git_repo_path):
    """Meta worktree should ignore codex runtime noise but keep prompts visible."""
    if sys.platform.startswith("win"):
        pytest.skip("Symlink semantics differ on Windows")

    status = worktree.ensure_meta_worktree()
    meta_path = Path(status["meta_path"])

    # Create codex noise + a new prompt.
    (meta_path / ".codex" / "prompts").mkdir(parents=True, exist_ok=True)
    (meta_path / ".codex" / "auth.json").write_text("secret\n", encoding="utf-8")
    (meta_path / ".codex" / "prompts" / "new-prompt.md").write_text("# hi\n", encoding="utf-8")

    # `auth.json` should be ignored; the prompt should remain visible for normal `git add`.
    st = run_with_timeout(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=meta_path,
        capture_output=True,
        text=True,
        check=True,
    )
    lines = (st.stdout or "").splitlines()
    assert not any(".codex/auth.json" in ln for ln in lines)
    assert any(".codex/prompts/new-prompt.md" in ln for ln in lines)


def test_initialize_meta_shared_state_links_primary_and_writes_excludes(session_git_repo_path):
    """Meta init should make the primary checkout share `.project/*` via symlinks + excludes."""
    if sys.platform.startswith("win"):
        pytest.skip("Symlink semantics differ on Windows")

    # Simulate a legacy installation where Edison wrote shared-path ignores into the
    # repo-wide `.git/info/exclude`. With per-worktree excludes enabled, these stale
    # ignores must be removed or they will prevent the meta branch from tracking
    # meta-managed shared paths like `.claude/`.
    info_exclude = session_git_repo_path / ".git" / "info" / "exclude"
    info_exclude.parent.mkdir(parents=True, exist_ok=True)
    info_exclude.write_text(
        "\n".join(
            [
                "# legacy excludes",
                ".project/",
                ".claude/",
                ".cursor/",
                ".pal/",
                ".edison/_generated/",
                "",
            ]
        ),
        encoding="utf-8",
    )

    # Seed primary checkout with local management state that should become shared.
    primary_seed = session_git_repo_path / ".project" / "tasks" / "todo" / "seed.txt"
    primary_seed.parent.mkdir(parents=True, exist_ok=True)
    primary_seed.write_text("seed\n", encoding="utf-8")

    init = worktree.initialize_meta_shared_state()
    meta_path = Path(init["meta_path"])

    link = session_git_repo_path / ".project" / "tasks"
    assert link.exists()
    assert link.is_symlink()
    assert link.resolve() == (meta_path / ".project" / "tasks").resolve()

    # Ensure the seeded file is now visible from the shared target.
    assert (meta_path / ".project" / "tasks" / "todo" / "seed.txt").exists()

    # Primary checkout should have worktree-local excludes to avoid untracked noise.
    cp = run_with_timeout(
        ["git", "config", "--worktree", "--get", "core.excludesFile"],
        cwd=session_git_repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    excludes_file_raw = (cp.stdout or "").strip()
    assert excludes_file_raw, "Expected Edison to configure core.excludesFile for the primary worktree"
    exclude_file = Path(excludes_file_raw).expanduser().resolve()
    assert exclude_file.exists()
    assert ".project/" in exclude_file.read_text(encoding="utf-8").splitlines()

    # Repo-wide info/exclude should no longer ignore meta-managed/shared paths.
    # If left in place, `git status` in the meta worktree won't show these files and
    # they can't be committed as intended.
    info_lines = info_exclude.read_text(encoding="utf-8").splitlines()
    assert ".project/" not in info_lines
    assert ".claude/" not in info_lines
    assert ".cursor/" not in info_lines
    assert ".pal/" not in info_lines
    assert ".edison/_generated/" not in info_lines


def test_ensure_meta_worktree_creates_orphan_branch(session_git_repo_path):
    """Meta branch must be an orphan branch (no shared history with primary)."""
    if sys.platform.startswith("win"):
        pytest.skip("Symlink semantics differ on Windows")

    status = worktree.ensure_meta_worktree()
    meta_branch = str(status["meta_branch"])
    assert meta_branch

    mb = run_with_timeout(
        ["git", "merge-base", meta_branch, "HEAD"],
        cwd=session_git_repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert mb.returncode != 0


def test_worktree_links_configured_shared_paths(session_git_repo_path):
    """Session worktrees should link configured shared paths outside `.project`."""
    if sys.platform.startswith("win"):
        pytest.skip("Symlink semantics differ on Windows")

    config_path = session_git_repo_path / ".edison" / "config" / "session.yml"
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["worktrees"]["sharedState"]["sharedPaths"] = [{"path": ".specify", "scopes": ["session"]}]
    config_path.write_text(yaml.dump(data), encoding="utf-8")
    clear_path_caches()
    clear_all_caches()
    reset_config_cache()

    wt1, _ = worktree.create_worktree("shared-paths-1", base_branch="main")
    assert wt1 is not None

    meta_path = Path(worktree.ensure_meta_worktree()["meta_path"])
    link = wt1 / ".specify"
    assert link.exists()
    assert link.is_symlink()
    assert link.resolve() == (meta_path / ".specify").resolve()

    (wt1 / ".specify" / "foo.txt").parent.mkdir(parents=True, exist_ok=True)
    (wt1 / ".specify" / "foo.txt").write_text("hello\n", encoding="utf-8")

    assert (meta_path / ".specify" / "foo.txt").exists()

    wt2, _ = worktree.create_worktree("shared-paths-2", base_branch="main")
    assert wt2 is not None
    assert (wt2 / ".specify" / "foo.txt").exists()


def test_shared_paths_can_disable_defaults(session_git_repo_path):
    """Projects should be able to disable a default sharedPath via enabled:false appended entry."""
    if sys.platform.startswith("win"):
        pytest.skip("Symlink semantics differ on Windows")

    # Append a disable marker for a default path (e.g. .pal).
    config_path = session_git_repo_path / ".edison" / "config" / "session.yml"
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["worktrees"]["sharedState"]["sharedPaths"] = ["+", {"path": ".pal", "enabled": False}]
    config_path.write_text(yaml.dump(data), encoding="utf-8")
    clear_path_caches()
    clear_all_caches()
    reset_config_cache()

    # Create a worktree; .pal should NOT be symlinked/managed.
    wt_path, _ = worktree.create_worktree("disable-shared-defaults", base_branch="main")
    assert wt_path is not None
    assert not (wt_path / ".pal").exists()


def test_initialize_meta_shared_state_skips_tracked_shared_paths(session_git_repo_path):
    """Meta init must not replace tracked content with symlinks."""
    if sys.platform.startswith("win"):
        pytest.skip("Symlink semantics differ on Windows")

    config_path = session_git_repo_path / ".edison" / "config" / "session.yml"
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["worktrees"]["sharedState"]["sharedPaths"] = [{"path": ".specify", "scopes": ["primary"]}]
    config_path.write_text(yaml.dump(data), encoding="utf-8")
    clear_path_caches()
    clear_all_caches()
    reset_config_cache()

    tracked = session_git_repo_path / ".specify" / "tracked.txt"
    tracked.parent.mkdir(parents=True, exist_ok=True)
    tracked.write_text("tracked\n", encoding="utf-8")
    run_with_timeout(["git", "add", ".specify/tracked.txt"], cwd=session_git_repo_path, check=True, capture_output=True, text=True)
    run_with_timeout(["git", "commit", "-m", "track specify"], cwd=session_git_repo_path, check=True, capture_output=True, text=True)

    init = worktree.initialize_meta_shared_state()
    assert init.get("shared_paths_primary_skipped_tracked") == 1
    assert (session_git_repo_path / ".specify").exists()
    assert not (session_git_repo_path / ".specify").is_symlink()


def test_recreate_meta_shared_state_resets_non_orphan_and_preserves_shared_paths(session_git_repo_path):
    """Meta recreate should rebuild a non-orphan meta branch as orphan and preserve configured shared paths."""
    if sys.platform.startswith("win"):
        pytest.skip("Symlink semantics differ on Windows")

    config_path = session_git_repo_path / ".edison" / "config" / "session.yml"
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    # Append to default sharedPaths (do not replace defaults like `.project/tasks`).
    data["worktrees"]["sharedState"]["sharedPaths"] = ["+", {"path": ".specify", "scopes": ["session"]}]
    config_path.write_text(yaml.dump(data), encoding="utf-8")
    clear_path_caches()
    clear_all_caches()
    reset_config_cache()

    meta_dir = session_git_repo_path / "worktrees" / "_meta"
    meta_branch = "edison-meta"

    # Create a non-orphan meta branch/worktree (shares history with primary).
    run_with_timeout(
        ["git", "worktree", "add", "-b", meta_branch, str(meta_dir), "HEAD"],
        cwd=session_git_repo_path,
        capture_output=True,
        text=True,
        check=True,
    )
    mb_before = run_with_timeout(
        ["git", "merge-base", meta_branch, "HEAD"],
        cwd=session_git_repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert mb_before.returncode == 0

    (meta_dir / ".project" / "tasks" / "todo").mkdir(parents=True, exist_ok=True)
    (meta_dir / ".project" / "tasks" / "todo" / "seed.md").write_text("seed\n", encoding="utf-8")
    (meta_dir / ".specify").mkdir(parents=True, exist_ok=True)
    (meta_dir / ".specify" / "foo.txt").write_text("foo\n", encoding="utf-8")

    out = worktree.recreate_meta_shared_state(force=True)
    assert out.get("recreated") is True

    mb_after = run_with_timeout(
        ["git", "merge-base", meta_branch, "HEAD"],
        cwd=session_git_repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert mb_after.returncode != 0
    assert (meta_dir / ".project" / "tasks" / "todo" / "seed.md").exists()
    assert (meta_dir / ".specify" / "foo.txt").exists()

    wt, _ = worktree.create_worktree("after-recreate", base_branch="main")
    assert wt is not None
    assert (wt / ".specify" / "foo.txt").exists()


def test_recreate_meta_shared_state_does_not_follow_symlink_cycles(session_git_repo_path):
    """Meta recreate must not follow symlinks when snapshotting preserved state."""
    if sys.platform.startswith("win"):
        pytest.skip("Symlink semantics differ on Windows")

    meta_dir = session_git_repo_path / "worktrees" / "_meta"
    meta_branch = "edison-meta"

    run_with_timeout(
        ["git", "worktree", "add", "-b", meta_branch, str(meta_dir), "HEAD"],
        cwd=session_git_repo_path,
        capture_output=True,
        text=True,
        check=True,
    )

    recovery = meta_dir / ".project" / "sessions" / "recovery"
    recovery.mkdir(parents=True, exist_ok=True)
    (recovery / "real").mkdir(parents=True, exist_ok=True)
    (recovery / "real" / "seed.txt").write_text("seed\n", encoding="utf-8")

    cycle = recovery / "cycle"
    if cycle.exists() or cycle.is_symlink():
        cycle.unlink()
    cycle.symlink_to(recovery, target_is_directory=True)

    out = worktree.recreate_meta_shared_state(force=True)
    assert out.get("recreated") is True
    assert (meta_dir / ".project" / "sessions" / "recovery" / "real" / "seed.txt").exists()
    assert (meta_dir / ".project" / "sessions" / "recovery" / "cycle").is_symlink()


def test_recreate_meta_shared_state_refuses_tracked_without_force(session_git_repo_path):
    """Recreate must fail-closed when meta branch tracks unexpected files (unless forced)."""
    if sys.platform.startswith("win"):
        pytest.skip("Symlink semantics differ on Windows")

    meta_dir = session_git_repo_path / "worktrees" / "_meta"
    meta_branch = "edison-meta"
    run_with_timeout(
        ["git", "worktree", "add", "-b", meta_branch, str(meta_dir), "HEAD"],
        cwd=session_git_repo_path,
        capture_output=True,
        text=True,
        check=True,
    )

    with pytest.raises(Exception):
        worktree.recreate_meta_shared_state()


def test_create_worktree_links_primary_management_dirs_in_meta_mode(session_git_repo_path):
    """Creating a session worktree in meta mode should also align primary `.project/*`."""
    if sys.platform.startswith("win"):
        pytest.skip("Symlink semantics differ on Windows")

    primary_seed = session_git_repo_path / ".project" / "tasks" / "todo" / "seed2.txt"
    primary_seed.parent.mkdir(parents=True, exist_ok=True)
    primary_seed.write_text("seed2\n", encoding="utf-8")

    sid = "links-primary"
    wt_path, _ = worktree.create_worktree(sid, base_branch="main")
    assert wt_path is not None

    meta_path = session_git_repo_path / "worktrees" / "_meta"
    link = session_git_repo_path / ".project" / "tasks"
    assert link.is_symlink()
    assert link.resolve() == (meta_path / ".project" / "tasks").resolve()
    assert (meta_path / ".project" / "tasks" / "todo" / "seed2.txt").exists()


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
