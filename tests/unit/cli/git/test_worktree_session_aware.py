from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest


def _stdout_json(capsys: pytest.CaptureFixture[str]) -> dict:
    return json.loads(capsys.readouterr().out)


def test_worktree_create_defaults_to_current_session(
    isolated_project_env: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository

    session_id = "sess-worktree-create-default"
    SessionRepository(project_root=isolated_project_env).create(
        Session.create(session_id, owner="test", state="active")
    )
    monkeypatch.setenv("AGENTS_SESSION", session_id)

    from edison.cli.git.worktree_create import main, register_args

    parser = argparse.ArgumentParser()
    register_args(parser)

    # No session_id positional arg: should resolve from current session context.
    args = parser.parse_args(["--dry-run", "--json"])
    rc = main(args)
    assert rc == 0

    payload = _stdout_json(capsys)
    assert payload["session_id"] == session_id
    assert payload["dry_run"] is True


def test_worktree_create_fails_fast_when_session_already_linked_elsewhere(
    isolated_project_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.session import worktree as worktree_lib

    session_id = "sess-worktree-linked-mismatch"
    repo = SessionRepository(project_root=isolated_project_env)
    session = Session.create(session_id, owner="test", state="active")

    target_path, _branch = worktree_lib.resolve_worktree_target(session_id)
    mismatch_path = target_path.parent / f"{target_path.name}-other"
    data = session.to_dict()
    data.setdefault("git", {})
    data["git"]["worktreePath"] = str(mismatch_path)
    repo.create(Session.from_dict(data))

    monkeypatch.setenv("AGENTS_SESSION", session_id)

    from edison.cli.git.worktree_create import main, register_args

    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args(["--dry-run", "--json"])

    rc = main(args)
    assert rc != 0


def test_worktree_restore_defaults_to_current_session(
    isolated_project_env: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository

    session_id = "sess-worktree-restore-default"
    SessionRepository(project_root=isolated_project_env).create(
        Session.create(session_id, owner="test", state="active")
    )
    monkeypatch.setenv("AGENTS_SESSION", session_id)

    # Create a fake archive source that satisfies restore_worktree's existence check.
    archive_root = tmp_path / "archive-root"
    (archive_root / session_id).mkdir(parents=True, exist_ok=True)

    from edison.cli.git.worktree_restore import main, register_args

    parser = argparse.ArgumentParser()
    register_args(parser)

    args = parser.parse_args(["--dry-run", "--json", "--source", str(archive_root)])
    rc = main(args)
    assert rc == 0

    payload = _stdout_json(capsys)
    assert payload["session_id"] == session_id
    assert payload["dry_run"] is True


def test_worktree_create_persists_git_metadata_into_session_record(
    isolated_project_env: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Force worktree paths to stay inside the isolated repo for deterministic tests.
    cfg_dir = isolated_project_env / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "worktrees.yaml").write_text(
        """
worktrees:
  enabled: true
  branchPrefix: "session/"
  pathTemplate: "worktrees/{sessionId}"
  archiveDirectory: "worktrees/_archived"
  sharedState:
    mode: "primary"
""".lstrip(),
        encoding="utf-8",
    )

    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository

    session_id = "sess-worktree-create-persist"
    repo = SessionRepository(project_root=isolated_project_env)
    repo.create(Session.create(session_id, owner="test", state="active"))

    monkeypatch.setenv("AGENTS_SESSION", session_id)

    from edison.cli.git.worktree_create import main, register_args

    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args(["--json"])

    rc = main(args)
    assert rc == 0

    payload = _stdout_json(capsys)
    assert payload["session_found"] is True
    assert payload["session_updated"] is True
    assert payload["worktree_path"]
    assert payload["branch_name"]

    sess = repo.get(session_id)
    assert sess is not None
    git_meta = sess.to_dict().get("git") or {}
    assert git_meta.get("worktreePath") == payload["worktree_path"]
    assert git_meta.get("branchName") == payload["branch_name"]
