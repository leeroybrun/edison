from __future__ import annotations

import argparse
from pathlib import Path

import pytest


@pytest.mark.session
def test_session_list_excludes_terminal_state_by_default(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.config.domains.workflow import WorkflowConfig
    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository
    from edison.cli.session.list import main as list_main

    cfg = WorkflowConfig(repo_root=isolated_project_env)
    final_states = cfg.get_final_states("session")
    assert final_states
    final_state = final_states[0]

    repo = SessionRepository(isolated_project_env)
    repo.create(Session.create("sess-active", state="active"))
    repo.create(Session.create("sess-final", state=final_state))

    rc = list_main(
        argparse.Namespace(
            status=None,
            owner=None,
            all=False,
            json=False,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    out = capsys.readouterr().out
    assert "sess-active" in out
    assert "sess-final" not in out


@pytest.mark.session
def test_session_list_all_includes_terminal_state(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.config.domains.workflow import WorkflowConfig
    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository
    from edison.cli.session.list import main as list_main

    cfg = WorkflowConfig(repo_root=isolated_project_env)
    final_states = cfg.get_final_states("session")
    assert final_states
    final_state = final_states[0]

    repo = SessionRepository(isolated_project_env)
    repo.create(Session.create("sess-final", state=final_state))

    rc = list_main(
        argparse.Namespace(
            status=None,
            owner=None,
            all=True,
            json=False,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    out = capsys.readouterr().out
    assert "sess-final" in out

