import os
from pathlib import Path

import json
import os

from edison.core.session.context import SessionContext


def test_in_session_worktree_switches_and_restores(tmp_path: Path, monkeypatch) -> None:
    from edison.core.config.domains import SessionConfig

    session_id = "sess-ctx"
    worktree = tmp_path / "wt"
    worktree.mkdir()
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))

    # Get the correct initial session state directory name
    config = SessionConfig()
    initial_state = config.get_initial_session_state()
    state_dir = config.get_session_states().get(initial_state, initial_state)

    data = {"meta": {}, "git": {"worktreePath": str(worktree)}}
    store_dir = tmp_path / ".project" / "sessions" / state_dir / session_id
    store_dir.mkdir(parents=True, exist_ok=True)
    (store_dir / "session.json").write_text(json.dumps(data), encoding="utf-8")

    original = os.getcwd()
    with SessionContext.in_session_worktree(session_id) as sess:
        assert Path.cwd() == worktree
        assert sess["git"]["worktreePath"] == str(worktree)
    assert Path.cwd() == Path(original)


def test_in_session_worktree_without_path(tmp_path: Path, monkeypatch) -> None:
    from edison.core.config.domains import SessionConfig

    session_id = "sess-no-wt"
    data = {"meta": {}, "git": {}}
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))

    # Get the correct initial session state directory name
    config = SessionConfig()
    initial_state = config.get_initial_session_state()
    state_dir = config.get_session_states().get(initial_state, initial_state)

    store_dir = tmp_path / ".project" / "sessions" / state_dir / session_id
    store_dir.mkdir(parents=True, exist_ok=True)
    (store_dir / "session.json").write_text(json.dumps(data), encoding="utf-8")

    with SessionContext.in_session_worktree(session_id) as sess:
        # Session model provides default GitInfo with None worktreePath
        assert sess["git"]["worktreePath"] is None
        assert sess["git"]["baseBranch"] == "main"
