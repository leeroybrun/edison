from __future__ import annotations

import argparse
from pathlib import Path

import pytest


def test_task_new_prints_next_steps_for_required_fill_sections(
    isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from edison.cli.task.new import main, register_args

    parser = argparse.ArgumentParser()
    register_args(parser)

    args = parser.parse_args(
        [
            "--id",
            "101",
            "--slug",
            "required-fill",
            "--repo-root",
            str(isolated_project_env),
        ]
    )

    rc = main(args)
    assert rc == 0

    captured = capsys.readouterr()
    assert "Next steps:" in captured.err
    assert "Fill required sections" in captured.err
