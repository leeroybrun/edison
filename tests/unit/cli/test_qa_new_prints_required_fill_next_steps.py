from __future__ import annotations

import argparse
from pathlib import Path

import pytest


def test_qa_new_prints_next_steps_for_required_fill_sections(
    isolated_project_env: Path, capsys: pytest.CaptureFixture[str], monkeypatch
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.task.workflow import TaskQAWorkflow

    TaskQAWorkflow(project_root=isolated_project_env).create_task(
        task_id="200-qa-next-steps",
        title="Task for QA",
        create_qa=False,
    )

    from edison.cli.qa.new import main, register_args

    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args(["200-qa-next-steps", "--repo-root", str(isolated_project_env)])

    rc = main(args)
    assert rc == 0

    out = capsys.readouterr().out
    assert "Next steps:" in out
    assert "Fill required sections" in out

