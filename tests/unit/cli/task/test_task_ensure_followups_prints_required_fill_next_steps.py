from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from tests.helpers.fixtures import create_task_file


def test_task_ensure_followups_prints_required_fill_next_steps(
    isolated_project_env: Path, capsys: pytest.CaptureFixture[str], monkeypatch
) -> None:
    monkeypatch.chdir(isolated_project_env)

    create_task_file(
        isolated_project_env,
        "901-api-change",
        state="todo",
        session_id=None,
        title="Add API endpoint",
    )

    from edison.cli.task.ensure_followups import main, register_args

    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args(["901-api-change", "--repo-root", str(isolated_project_env)])

    rc = main(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "Next steps:" in out
    assert "Fill required sections" in out

