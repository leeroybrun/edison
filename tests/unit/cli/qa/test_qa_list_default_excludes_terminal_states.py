from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from tests.helpers.markdown_utils import create_qa_file


@pytest.mark.qa
def test_qa_list_excludes_terminal_state_by_default(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.config.domains.workflow import WorkflowConfig
    from edison.cli.qa.list import main as list_main

    cfg = WorkflowConfig(repo_root=isolated_project_env)
    final_states = cfg.get_final_states("qa")
    assert final_states
    final_state = final_states[0]
    non_final_state = next(s for s in cfg.get_states("qa") if s not in set(final_states))

    create_qa_file(
        isolated_project_env / ".project" / "qa" / non_final_state / "T-QA-ACTIVE-qa.md",
        "T-QA-ACTIVE-qa",
        title="Active QA",
        task_id="T-QA-ACTIVE",
    )
    create_qa_file(
        isolated_project_env / ".project" / "qa" / final_state / "T-QA-FINAL-qa.md",
        "T-QA-FINAL-qa",
        title="Final QA",
        task_id="T-QA-FINAL",
    )

    rc = list_main(
        argparse.Namespace(
            status=None,
            session=None,
            all=False,
            json=False,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    out = capsys.readouterr().out
    assert "T-QA-ACTIVE-qa" in out
    assert "T-QA-FINAL-qa" not in out


@pytest.mark.qa
def test_qa_list_all_includes_terminal_state(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.config.domains.workflow import WorkflowConfig
    from edison.cli.qa.list import main as list_main

    cfg = WorkflowConfig(repo_root=isolated_project_env)
    final_states = cfg.get_final_states("qa")
    assert final_states
    final_state = final_states[0]

    create_qa_file(
        isolated_project_env / ".project" / "qa" / final_state / "T-QA-FINAL-qa.md",
        "T-QA-FINAL-qa",
        title="Final QA",
        task_id="T-QA-FINAL",
    )

    rc = list_main(
        argparse.Namespace(
            status=None,
            session=None,
            all=True,
            json=False,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    out = capsys.readouterr().out
    assert "T-QA-FINAL-qa" in out

