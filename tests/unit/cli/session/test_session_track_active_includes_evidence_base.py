from __future__ import annotations

import argparse
from pathlib import Path

import pytest


def test_session_track_active_prints_evidence_base_when_empty(
    isolated_project_env: Path, monkeypatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.qa._utils import get_evidence_base_path

    evidence_base = get_evidence_base_path(isolated_project_env)

    from edison.cli.session.track import main, register_args

    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args(["active", "--repo-root", str(isolated_project_env)])

    rc = main(args)
    assert rc == 0

    out = capsys.readouterr().out
    assert "No active tracking sessions found" in out
    assert str(evidence_base) in out

