from __future__ import annotations

import os
from pathlib import Path

import pytest

from edison.core.config.cache import clear_all_caches
from edison.core.state import StateTransitionError
from edison.core.session import SessionManager


def _write_config(root: Path) -> None:
    cfg = root / ".edison" / "config" / "config.yml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(
        """
        session:
          paths:
            root: .project/sessions
            archive: .project/archive
            tx: .project/sessions/_tx
          validation:
            maxLength: 32
            idRegex: "^[a-z0-9-]+$"
          states:
            active: wip
            done: done
            validated: validated
          lookupOrder: [active, done, validated]
          defaults:
            initialState: active

        statemachine:
          session:
            states:
              active:
                allowed_transitions:
                  - to: done
              done:
                allowed_transitions:
                  - to: validated
              validated:
                allowed_transitions: []
        """,
        encoding="utf-8",
    )
    (root / ".project").mkdir(exist_ok=True)


def _use_root(tmp_path: Path) -> None:
    os.environ["AGENTS_PROJECT_ROOT"] = str(tmp_path)
    clear_all_caches()


def test_session_manager_creates_and_transitions(tmp_path: Path) -> None:
    _write_config(tmp_path)
    _use_root(tmp_path)

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
