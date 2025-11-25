import os
from pathlib import Path

import json
import os

from edison.core.session.context import SessionContext


def test_in_session_worktree_switches_and_restores(tmp_path: Path, monkeypatch) -> None:
    session_id = "sess-ctx"
    worktree = tmp_path / "wt"
    worktree.mkdir()
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    data = {"meta": {}, "git": {"worktreePath": str(worktree)}}
    store_dir = tmp_path / ".project" / "sessions" / "active" / session_id
    store_dir.mkdir(parents=True, exist_ok=True)
    (store_dir / "session.json").write_text(json.dumps(data), encoding="utf-8")

    original = os.getcwd()
    with SessionContext.in_session_worktree(session_id) as sess:
        assert Path.cwd() == worktree
        assert sess["git"]["worktreePath"] == str(worktree)
    assert Path.cwd() == Path(original)


def test_in_session_worktree_without_path(tmp_path: Path, monkeypatch) -> None:
    session_id = "sess-no-wt"
    data = {"meta": {}, "git": {}}
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    store_dir = tmp_path / ".project" / "sessions" / "active" / session_id
    store_dir.mkdir(parents=True, exist_ok=True)
    (store_dir / "session.json").write_text(json.dumps(data), encoding="utf-8")

    with SessionContext.in_session_worktree(session_id) as sess:
        assert sess["git"] == {}
