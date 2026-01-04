from __future__ import annotations

from pathlib import Path

from edison.core.qa.context.context7 import detect_packages
from edison.core.utils.subprocess import run_with_timeout
from helpers.cache_utils import reset_edison_caches


def test_detect_packages_is_task_scoped_not_session_diff(isolated_project_env: Path) -> None:
    """A task's Context7 requirements must not be polluted by other session changes.

    Regression test for the multi-task session contamination bug:
    - worktree diff includes a TSX change (would normally imply "react")
    - the task is DB-only and declares only DB files as Primary Files
    Expected: detect_packages() does NOT require react for the DB task.
    """
    repo = isolated_project_env

    # Configure minimal triggers.
    (repo / ".edison" / "config" / "context7.yaml").write_text(
        """
context7:
  triggers:
    react: ["**/*.tsx"]
""".lstrip(),
        encoding="utf-8",
    )
    reset_edison_caches()

    # Create a session worktree that contains only a TSX change (unrelated to DB task).
    session_id = "sid-ctx7-contamination"
    wt_path = repo / ".worktrees" / session_id
    wt_path.parent.mkdir(parents=True, exist_ok=True)
    run_with_timeout(
        ["git", "worktree", "add", "-b", f"session/{session_id}", str(wt_path), "main"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        timeout_type="git_operations",
    )
    (wt_path / "ui" / "Widget.tsx").parent.mkdir(parents=True, exist_ok=True)
    (wt_path / "ui" / "Widget.tsx").write_text("export const Widget = () => null\n", encoding="utf-8")
    run_with_timeout(
        ["git", "add", "ui/Widget.tsx"],
        cwd=wt_path,
        check=True,
        capture_output=True,
        text=True,
        timeout_type="git_operations",
    )
    run_with_timeout(
        ["git", "commit", "-m", "ui change"],
        cwd=wt_path,
        check=True,
        capture_output=True,
        text=True,
        timeout_type="git_operations",
    )

    # DB-only task file (no TSX in primary files).
    task_path = repo / ".project" / "tasks" / "todo" / "t-db.md"
    task_path.parent.mkdir(parents=True, exist_ok=True)
    task_path.write_text(
        """
---
id: t-db
title: DB task
---

## Primary Files / Areas
- db/schema.sql
""".lstrip(),
        encoding="utf-8",
    )

    pkgs = detect_packages(
        task_path,
        session={"git": {"worktreePath": str(wt_path), "baseBranch": "main"}},
    )
    assert "react" not in pkgs

