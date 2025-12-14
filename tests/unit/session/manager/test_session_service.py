from __future__ import annotations
from helpers.io_utils import write_config

import os
from pathlib import Path

import pytest

from edison.core.config.cache import clear_all_caches
from edison.core.state import StateTransitionError
from edison.core.session import SessionManager

def _use_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # CRITICAL: use monkeypatch so the env var is reverted after the test.
    # Some session tests run a lot of subprocess + path resolution; leaking
    # AGENTS_PROJECT_ROOT across tests breaks isolation and causes flakiness.
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    clear_all_caches()

def test_session_manager_creates_and_transitions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write_config(tmp_path)
    _use_root(monkeypatch, tmp_path)

    mgr = SessionManager(project_root=tmp_path)

    path = mgr.create(session_id="s1", owner="alice")
    assert path.exists()

    data = path.read_text(encoding="utf-8")
    assert "\"state\": \"active\"" in data
    assert "\"ready\": true" in data.lower()

    # Invalid transition (skips done)
    with pytest.raises(StateTransitionError):
        mgr.transition("s1", "validated")

    # Valid transition
    new_path = mgr.transition("s1", "done")
    assert "done" in str(new_path)
    assert new_path.parent.parent.name == "done"
