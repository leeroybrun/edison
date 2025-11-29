from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
from edison.core.utils.subprocess import run_with_timeout

PROJECT_NAME = os.environ.get("PROJECT_NAME", "example-project")
WORKTREE_DIRNAME = f"{PROJECT_NAME}-worktrees"
WORKTREE_BASE = f"../{WORKTREE_DIRNAME}"
WORKTREE_ARCHIVE = f"{WORKTREE_BASE}/_archived"


def repo_root() -> Path:
    cur = Path(__file__).resolve()
    candidate: Path | None = None
    while cur != cur.parent:
        if (cur / ".git").exists():
            candidate = cur
        cur = cur.parent
    if candidate is None:
        raise RuntimeError("Could not find repository root")
    # When tests run inside the nested .edison git repo, prefer the parent
    # project root if it also has a .git directory.
    if candidate.name == ".edison" and (candidate.parent / ".git").exists():
        return candidate.parent
    return candidate


def sh(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    e = os.environ.copy()
    if env:
        e.update(env)
    return run_with_timeout(cmd, cwd=cwd, env=e, capture_output=True, text=True)


@pytest.fixture()
def project(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    root = tmp_path
    env = {"AGENTS_PROJECT_ROOT": str(root)}
    # Initialize a minimal git repo so sessionlib worktree helpers work
    sh(["git", "init", "-b", "main"], cwd=root)
    (root / "README.md").write_text("test\n")
    sh(["git", "add", "."], cwd=root)
    sh(["git", "-c", "user.email=ci@example.com", "-c", "user.name=CI", "commit", "-m", "init"], cwd=root)
    # Create session directories and template
    (root / ".project" / "sessions" / "wip").mkdir(parents=True)
    # manifest for worktree base (legacy helper)
    (root / ".agents").mkdir(exist_ok=True)
    (root / ".agents" / "manifest.json").write_text(
        json.dumps(
            {
                "worktrees": {
                    "enabled": True,
                    "baseDirectory": WORKTREE_BASE,
                    "archiveDirectory": WORKTREE_ARCHIVE,
                    "branchPrefix": "session/",
                    "baseBranch": "main",
                }
            }
        )
    )
    # Minimal YAML config expected by sessionlib._load_worktree_config
    cfg_path = root / ".agents" / "config.yml"
    if not cfg_path.exists():
        cfg_path.write_text(
            (
                "worktrees:\n"
                "  enabled: true\n"
                f"  baseDirectory: {WORKTREE_BASE}\n"
                f"  archiveDirectory: {WORKTREE_ARCHIVE}\n"
                "  branchPrefix: session/\n"
                "  baseBranch: main\n"
            ),
            encoding="utf-8",
        )
    # Ensure base worktree dirs exist
    (root.parent / WORKTREE_DIRNAME).mkdir(exist_ok=True)
    (root.parent / WORKTREE_DIRNAME / "_archived").mkdir(parents=True, exist_ok=True)
    return root, env


def write_session(root: Path, sid: str) -> None:
    data = {
        "meta": {
            "sessionId": sid,
            "owner": "tester",
            "mode": "auto",
            "createdAt": "2025-01-01T00:00:00Z",
            "lastActive": "2025-01-01T00:00:00Z",
        },
        "state": "active",
        "tasks": {},
        "qa": {},
        "activityLog": [{"timestamp": "2025-01-01T00:00:00Z", "message": "created"}],
        "git": {},
    }
    (root / ".project" / "sessions" / "wip" / f"{sid}.json").write_text(__import__("json").dumps(data))


def test_clean_worktrees_dry_run_detects_orphans(project: tuple[Path, dict[str, str]]):
    root, env = project
    # Create an orphan worktree branch
    orphan_sid = "orphan-123"
    orphan_branch = f"session/{orphan_sid}"
    # Create branch and worktree
    sh(["git", "branch", orphan_branch], cwd=root)
    wt_dir = root.parent / WORKTREE_DIRNAME / orphan_sid
    sh(["git", "worktree", "add", str(wt_dir), orphan_branch], cwd=root)

    script = repo_root() / ".edison" / "core" / "scripts" / "recovery" / "clean-worktrees"
    res = sh([str(script), "--dry-run"], cwd=root, env=env)
    assert res.returncode == 0, res.stderr
    # Should list the orphan
    assert orphan_sid in res.stdout
    # Worktree remains
    assert wt_dir.exists()


def test_clean_worktrees_force_archives_orphans(project: tuple[Path, dict[str, str]]):
    root, env = project
    # Active session worktree (should not clean)
    active_sid = "active-abc"
    write_session(root, active_sid)
    active_branch = f"session/{active_sid}"
    sh(["git", "checkout", "main"], cwd=root)
    sh(["git", "branch", active_branch], cwd=root)
    active_wt = root.parent / WORKTREE_DIRNAME / active_sid
    sh(["git", "worktree", "add", str(active_wt), active_branch], cwd=root)

    # Orphan worktree to clean
    orphan_sid = "orphan-xyz"
    orphan_branch = f"session/{orphan_sid}"
    sh(["git", "checkout", "main"], cwd=root)
    sh(["git", "branch", orphan_branch], cwd=root)
    orphan_wt = root.parent / WORKTREE_DIRNAME / orphan_sid
    sh(["git", "worktree", "add", str(orphan_wt), orphan_branch], cwd=root)

    # Create .keep under active to enforce preservation
    (active_wt / ".keep").write_text("preserve\n")

    script = repo_root() / ".edison" / "core" / "scripts" / "recovery" / "clean-worktrees"
    res = sh([str(script), "--force"], cwd=root, env=env)
    assert res.returncode == 0, res.stderr

    # Active preserved
    assert active_wt.exists(), "Active session worktree must be preserved"
    # Orphan archived
    # archiveDirectory resolves relative to REPO_DIR.parent because manifest uses "../..."
    archived_dir = root.parent.parent / WORKTREE_DIRNAME / "_archived"
    archived_candidates = list(archived_dir.glob(f"*{orphan_sid}"))
    assert archived_candidates, f"Expected archived entry for {orphan_sid}"
