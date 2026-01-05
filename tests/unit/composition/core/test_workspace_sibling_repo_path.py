from __future__ import annotations

from pathlib import Path

from edison.core.composition.transformers.base import TransformContext


def test_sibling_repo_path_from_primary_checkout(tmp_path: Path) -> None:
    repo_root = tmp_path / "edison"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()

    ctx = TransformContext(project_root=repo_root, config={"project": {"paths": {"uiRepoName": "edison-ui"}}})

    from edison.core.composition.functions import paths as path_functions

    assert path_functions.sibling_repo_path(ctx, "project.paths.uiRepoName", "edison-ui") == str(
        (tmp_path / "edison-ui").resolve()
    )


def test_sibling_repo_path_from_session_worktree(tmp_path: Path) -> None:
    workspace = tmp_path
    primary_root = workspace / "edison"
    primary_git = primary_root / ".git"
    (primary_git / "worktrees" / "session-123").mkdir(parents=True)

    session_root = primary_root / ".worktrees" / "session-123"
    session_root.mkdir(parents=True)
    (session_root / ".git").write_text(
        f"gitdir: {primary_git}/worktrees/session-123\n",
        encoding="utf-8",
    )

    ctx = TransformContext(project_root=session_root, config={"project": {"paths": {"uiRepoName": "edison-ui"}}})

    from edison.core.composition.functions import paths as path_functions

    assert path_functions.sibling_repo_path(ctx, "project.paths.uiRepoName", "edison-ui") == str(
        (workspace / "edison-ui").resolve()
    )

