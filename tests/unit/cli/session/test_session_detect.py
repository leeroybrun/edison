from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest
import yaml

from tests.helpers.session import ensure_session


@pytest.mark.session
def test_session_detect_reports_worktree_path_and_in_worktree(
    isolated_project_env: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session_id = "sess-detect-001"
    ensure_session(session_id, state="active")
    monkeypatch.setenv("AGENTS_SESSION", session_id)

    # Persist worktree metadata on the session record.
    from edison.core.session.persistence.repository import SessionRepository

    repo = SessionRepository(project_root=isolated_project_env)
    sess = repo.get(session_id)
    assert sess is not None

    worktree_path = (isolated_project_env / ".worktrees" / session_id).resolve()
    worktree_path.mkdir(parents=True, exist_ok=True)
    sess.git.worktree_path = str(worktree_path)
    repo.save(sess)

    from edison.cli.session.detect import main as detect_main

    args = argparse.Namespace(
        session_id=None,
        owner=None,
        json=True,
        repo_root=isolated_project_env,
    )
    rc = detect_main(args)
    assert rc == 0

    payload = json.loads(capsys.readouterr().out or "{}")
    assert payload.get("sessionId") == session_id
    assert payload.get("worktreePath") == str(worktree_path)
    assert payload.get("inWorktree") is False

    # When invoked from inside the worktree path, inWorktree becomes true.
    monkeypatch.chdir(worktree_path)
    rc2 = detect_main(args)
    assert rc2 == 0
    payload2 = json.loads(capsys.readouterr().out or "{}")
    assert payload2.get("sessionId") == session_id
    assert payload2.get("inWorktree") is True


@pytest.mark.session
def test_session_detect_is_archive_aware_when_worktree_path_is_missing(
    isolated_project_env: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session_id = "sess-detect-arch-001"
    ensure_session(session_id, state="active")
    monkeypatch.setenv("AGENTS_SESSION", session_id)

    from edison.core.session.persistence.repository import SessionRepository

    repo = SessionRepository(project_root=isolated_project_env)
    sess = repo.get(session_id)
    assert sess is not None
    missing_worktree_path = (tmp_path / "missing-worktrees" / session_id).resolve()
    sess.git.worktree_path = str(missing_worktree_path)
    repo.save(sess)

    # Override archive directory for deterministic test paths.
    cfg_dir = isolated_project_env / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "worktrees.yml").write_text(
        yaml.safe_dump(
            {
                "worktrees": {
                    "enabled": True,
                    "archiveDirectory": str(tmp_path / "archives"),
                }
            }
        ),
        encoding="utf-8",
    )
    from helpers.cache_utils import reset_edison_caches

    reset_edison_caches()

    archived_path = (tmp_path / "archives" / session_id).resolve()
    archived_path.mkdir(parents=True, exist_ok=True)

    from edison.cli.session.detect import main as detect_main

    args = argparse.Namespace(
        session_id=None,
        owner=None,
        json=True,
        repo_root=isolated_project_env,
    )
    rc = detect_main(args)
    assert rc == 0

    payload = json.loads(capsys.readouterr().out or "{}")
    assert payload.get("sessionId") == session_id
    assert payload.get("worktreePath") == str(missing_worktree_path)
    assert payload.get("archivedWorktreePath") == str(archived_path)

