from __future__ import annotations

import argparse
from pathlib import Path

import pytest


def test_session_track_complete_error_includes_expected_report_path(
    isolated_project_env: Path, monkeypatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(isolated_project_env)

    task_id = "201-track-complete-missing"

    from edison.cli.session.track import main, register_args

    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args(
        ["complete", "--task", task_id, "--repo-root", str(isolated_project_env)]
    )

    rc = main(args)
    assert rc == 1

    err = capsys.readouterr().err
    assert "No tracking records found" in err
    assert "implementation-report.md" in err

