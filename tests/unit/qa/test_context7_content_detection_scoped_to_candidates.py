from __future__ import annotations

from pathlib import Path

from edison.core.qa.context.context7 import detect_packages
from edison.core.utils.subprocess import run_with_timeout
from helpers.cache_utils import reset_edison_caches


def test_content_detection_is_scoped_to_candidate_files(isolated_project_env: Path) -> None:
    """Content detection must not scan the whole repo/worktree.

    Packs often define broad filePatterns like "**/*.ts". If we scan the entire
    worktree, any existing Prisma/Zod usage in unrelated files would force
    Context7 evidence even for docs-only tasks. We must limit scanning to
    the candidate file set (Primary Files + worktree diff).
    """
    repo = isolated_project_env

    # Configure broad content detection that would match an unrelated committed file.
    cfg_path = repo / ".edison" / "config" / "context7.yaml"
    cfg_path.write_text(
        """
context7:
  triggers: {}
  contentDetection:
    prisma:
      filePatterns: ["**/*.ts"]
      searchPatterns: ["PrismaClient"]
""".lstrip(),
        encoding="utf-8",
    )
    reset_edison_caches()

    # Commit an unrelated TS file containing the search pattern.
    src = repo / "src" / "db.ts"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("export const PrismaClient = {}\n", encoding="utf-8")
    run_with_timeout(
        ["git", "add", "src/db.ts"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        timeout_type="git_operations",
    )
    run_with_timeout(
        ["git", "commit", "-m", "add prisma reference"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        timeout_type="git_operations",
    )

    # Create a session worktree with ONLY a docs change.
    session_id = "sid-ctx7-scope"
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
    (wt_path / "docs" / "note.md").parent.mkdir(parents=True, exist_ok=True)
    (wt_path / "docs" / "note.md").write_text("docs\n", encoding="utf-8")
    run_with_timeout(
        ["git", "add", "docs/note.md"],
        cwd=wt_path,
        check=True,
        capture_output=True,
        text=True,
        timeout_type="git_operations",
    )
    run_with_timeout(
        ["git", "commit", "-m", "docs change"],
        cwd=wt_path,
        check=True,
        capture_output=True,
        text=True,
        timeout_type="git_operations",
    )

    # Minimal task file with no Primary Files section.
    task_path = repo / ".project" / "tasks" / "todo" / "t2.md"
    task_path.parent.mkdir(parents=True, exist_ok=True)
    task_path.write_text(
        """
---
id: t2
title: Test Context7
---
""".lstrip(),
        encoding="utf-8",
    )

    pkgs = detect_packages(
        task_path,
        session={"git": {"worktreePath": str(wt_path), "baseBranch": "main"}},
    )
    assert "prisma" not in pkgs

