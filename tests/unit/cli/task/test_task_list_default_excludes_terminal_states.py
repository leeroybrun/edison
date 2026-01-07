from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from tests.helpers.markdown_utils import create_markdown_task


@pytest.mark.task
def test_task_list_excludes_terminal_state_by_default(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.config.domains.workflow import WorkflowConfig
    from edison.cli.task.list import main as list_main

    cfg = WorkflowConfig(repo_root=isolated_project_env)
    final_states = cfg.get_final_states("task")
    assert final_states
    final_state = final_states[0]
    non_final_state = next(s for s in cfg.get_states("task") if s not in set(final_states))

    create_markdown_task(
        isolated_project_env / ".project" / "tasks" / non_final_state / "T-ACTIVE.md",
        "T-ACTIVE",
        "Active task",
    )
    create_markdown_task(
        isolated_project_env / ".project" / "tasks" / final_state / "T-FINAL.md",
        "T-FINAL",
        "Final task",
    )

    rc = list_main(
        argparse.Namespace(
            status=None,
            session=None,
            type="task",
            all=False,
            json=False,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    out = capsys.readouterr().out
    assert "T-ACTIVE" in out
    assert "T-FINAL" not in out


@pytest.mark.task
def test_task_list_all_includes_terminal_state(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.config.domains.workflow import WorkflowConfig
    from edison.cli.task.list import main as list_main

    cfg = WorkflowConfig(repo_root=isolated_project_env)
    final_states = cfg.get_final_states("task")
    assert final_states
    final_state = final_states[0]

    create_markdown_task(
        isolated_project_env / ".project" / "tasks" / final_state / "T-FINAL.md",
        "T-FINAL",
        "Final task",
    )

    rc = list_main(
        argparse.Namespace(
            status=None,
            session=None,
            type="task",
            all=True,
            json=False,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    out = capsys.readouterr().out
    assert "T-FINAL" in out

