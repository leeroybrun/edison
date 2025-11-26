from __future__ import annotations

import json
from pathlib import Path

import pytest

from edison.core.paths import PathResolver 
from edison.core.session.manager import SessionManager 
from edison.core.session import state as session_state 
from edison.core.session.config import SessionConfig

def _session_json_path(root: Path, session_id: str, state: str = "active") -> Path:
    """
    Compute the canonical session.json path for assertions.

    Resolution starts from PathResolver so tests never hard-code the
    project root; this helper simply appends the well-known relative
    layout used by sessionlib.
    """
    project_root = PathResolver.resolve_project_root()
    assert project_root == root
    
    config = SessionConfig(project_root)
    state_map = config.get_session_states()
    dir_name = state_map.get(state.lower(), state.lower())

    return project_root / ".project" / "sessions" / dir_name / session_id / "session.json"


@pytest.mark.session
def test_session_manager_uses_pathresolver_root(isolated_project_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    SessionManager without an explicit root must resolve project root via
    PathResolver so isolated AGENTS_PROJECT_ROOT values are honoured.
    """
    monkeypatch.setenv("PROJECT_NAME", "test-project")

    root = PathResolver.resolve_project_root()
    assert root == isolated_project_env

    mgr = SessionManager()
    assert mgr.project_root == root


@pytest.mark.session
def test_create_session_creates_active_session_json(isolated_project_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Creating a session via SessionManager should materialize a new
    ``session.json`` under ``.project/sessions/active/<id>/`` using the
    canonical layout from sessionlib.
    """
    monkeypatch.setenv("PROJECT_NAME", "test-project")

    mgr = SessionManager()
    sid = "sess-manager-001"

    path = mgr.create_session(sid, metadata={"owner": "tester"})
    assert isinstance(path, Path)
    assert path.exists()

    json_path = _session_json_path(isolated_project_env, sid, state="active")
    assert json_path.exists()

    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["id"] == sid
    # State is stored with canonical casing but must represent "active"
    assert str(data.get("state", "")).lower() == "active"
    assert (data.get("metadata") or {}).get("owner") == "tester"


@pytest.mark.session
def test_state_machine_rejects_invalid_transition(isolated_project_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    SessionStateMachine must fail-closed for invalid transitions as
    required by the state-machine guards guideline.
    """
    monkeypatch.setenv("PROJECT_NAME", "test-project")

    machine = session_state.build_default_state_machine()
    # active → validated is not allowed directly; helper should raise
    with pytest.raises(Exception):
        machine.validate("active", "validated")


@pytest.mark.session
def test_manager_transition_state_updates_state_field(isolated_project_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    SessionManager.transition_state should update both the JSON state
    field and on-disk directory to reflect the new lifecycle state.
    """
    monkeypatch.setenv("PROJECT_NAME", "test-project")

    mgr = SessionManager()
    sid = "sess-manager-002"

    # Start in active state
    mgr.create_session(sid, metadata={"owner": "tester"})
    active_json = _session_json_path(isolated_project_env, sid, state="active")
    assert active_json.exists()

    # Transition to closing; JSON remains in same directory but state
    # metadata must change according to the canonical state machine.
    mgr.transition_state(sid, "closing")

    closing_json = _session_json_path(isolated_project_env, sid, state="closing")
    assert closing_json.exists()

    data = json.loads(closing_json.read_text(encoding="utf-8"))
    assert str(data.get("state", "")).lower() == "closing"
