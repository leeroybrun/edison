from __future__ import annotations

import argparse
from pathlib import Path

import pytest


@pytest.mark.session
def test_session_list_lists_sessions_and_supports_status_alias(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository

    repo = SessionRepository(isolated_project_env)
    repo.create(Session.create("sess-1", state="active"))
    repo.create(Session.create("sess-2", state="draft"))

    from edison.cli.session.list import main as list_main

    rc = list_main(
        argparse.Namespace(
            status=None,
            owner=None,
            json=False,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "sess-1" in out
    assert "sess-2" in out

    rc = list_main(
        argparse.Namespace(
            status="wip",
            owner=None,
            json=False,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "sess-1" in out
    assert "sess-2" not in out

