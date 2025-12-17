from __future__ import annotations

from pathlib import Path

from edison.core.context.files import FileContextService
from edison.core.session.core.models import Session
from edison.core.session.persistence.repository import SessionRepository
from edison.core.utils.subprocess import run_with_timeout


def test_file_context_service_ignores_project_artifacts(isolated_project_env: Path) -> None:
    """Edison metadata/runtime files must not pollute "modifiedFiles".

    In real sessions we create `.project/.session-id`, `.project/sessions` symlinks,
    and validation evidence under `.project/qa/validation-evidence/**`. These are
    workflow artifacts and should not trigger validators.
    """
    repo = isolated_project_env

    session_id = "sid-ignore-project-artifacts"
    worktrees_dir = repo / ".worktrees"
    worktrees_dir.mkdir(parents=True, exist_ok=True)
    wt_path = worktrees_dir / session_id

    run_with_timeout(
        ["git", "worktree", "add", "-b", f"session/{session_id}", str(wt_path), "main"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        timeout_type="git_operations",
    )

    # Create a real product file change (untracked is enough for detection).
    doc = wt_path / "docs" / "e2e.txt"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text("smoke\n", encoding="utf-8")

    # Create typical Edison runtime artifacts that should be ignored.
    (wt_path / ".project").mkdir(parents=True, exist_ok=True)
    (wt_path / ".project" / ".session-id").write_text(session_id, encoding="utf-8")
    evidence = wt_path / ".project" / "qa" / "validation-evidence" / "T001" / "round-1"
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "implementation-report.md").write_text("# Report\n", encoding="utf-8")

    # Persist session metadata so FileContextService resolves the correct worktree.
    session = Session.create(session_id, owner="test", state="active")
    session.git.base_branch = "main"
    session.git.branch_name = f"session/{session_id}"
    session.git.worktree_path = str(wt_path)
    SessionRepository(project_root=repo).create(session)

    ctx = FileContextService(project_root=repo).get_for_session(session_id)
    assert "docs/e2e.txt" in ctx.all_files
    assert ".project/.session-id" not in ctx.all_files
    assert not any(p.startswith(".project/") for p in ctx.all_files)

