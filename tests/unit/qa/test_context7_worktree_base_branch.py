from __future__ import annotations

from pathlib import Path

from edison.core.qa.context.context7 import detect_packages
from edison.core.utils.subprocess import run_with_timeout
from helpers.cache_utils import reset_edison_caches


def test_detect_packages_uses_session_base_branch_for_worktree_diff(isolated_project_env: Path) -> None:
    """Worktree diffs must use the session's baseBranch, not hard-coded main.

    If we diff against `main` while the session is based on a feature branch, the
    candidate files set explodes and we incorrectly require Context7 evidence for
    unrelated packages. This mirrors the validator-roster baseBranch bug we fixed.
    """
    repo = isolated_project_env

    # Configure Context7 triggers so only TSX files imply a package.
    cfg_path = repo / ".edison" / "config" / "context7.yaml"
    cfg_path.write_text(
        """
context7:
  triggers:
    react: ["**/*.tsx"]
""".lstrip(),
        encoding="utf-8",
    )
    reset_edison_caches()

    # Create a base branch that diverges from main with a TSX file.
    run_with_timeout(
        ["git", "checkout", "-b", "base-feature"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        timeout_type="git_operations",
    )
    (repo / "feature.tsx").write_text("export const x = 1\n", encoding="utf-8")
    run_with_timeout(
        ["git", "add", "feature.tsx"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        timeout_type="git_operations",
    )
    run_with_timeout(
        ["git", "commit", "-m", "base feature"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        timeout_type="git_operations",
    )

    # Return to main (primary checkout).
    run_with_timeout(
        ["git", "checkout", "main"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        timeout_type="git_operations",
    )

    # Create a session worktree on top of base-feature and add a non-TSX change.
    session_id = "sid-ctx7-base-branch"
    worktrees_dir = repo / ".worktrees"
    worktrees_dir.mkdir(parents=True, exist_ok=True)
    wt_path = worktrees_dir / session_id
    run_with_timeout(
        ["git", "worktree", "add", "-b", f"session/{session_id}", str(wt_path), "base-feature"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        timeout_type="git_operations",
    )
    (wt_path / "notes.txt").write_text("session change\n", encoding="utf-8")
    run_with_timeout(
        ["git", "add", "notes.txt"],
        cwd=wt_path,
        check=True,
        capture_output=True,
        text=True,
        timeout_type="git_operations",
    )
    run_with_timeout(
        ["git", "commit", "-m", "session change"],
        cwd=wt_path,
        check=True,
        capture_output=True,
        text=True,
        timeout_type="git_operations",
    )

    # Create a minimal task file with no Primary Files section so detection relies on worktree diff.
    task_path = repo / ".project" / "tasks" / "todo" / "t1.md"
    task_path.parent.mkdir(parents=True, exist_ok=True)
    task_path.write_text(
        """
---
id: t1
title: Test Context7
---
""".lstrip(),
        encoding="utf-8",
    )

    pkgs = detect_packages(
        task_path,
        session={"git": {"worktreePath": str(wt_path), "baseBranch": "base-feature"}},
    )
    assert "react" not in pkgs

