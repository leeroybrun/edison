from __future__ import annotations

import argparse
from pathlib import Path

import pytest


@pytest.mark.qa
def test_qa_validate_new_round_initializes_implementation_report(
    isolated_project_env: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    # Add a fast delegated validator (avoid external CLIs).
    (isolated_project_env / ".edison" / "config" / "validation.yaml").write_text(
        "\n".join(
            [
                "validation:",
                "  validators:",
                "    alpha:",
                "      name: Alpha",
                "      engine: pal-mcp",
                "      wave: bundle_test",
                "      always_run: false",
                "      blocking: true",
                "      triggers: ['alpha.txt']",
                "      focus: []",
                "",
            ]
        ),
        encoding="utf-8",
    )

    from edison.core.qa.evidence import EvidenceService
    from edison.core.task.relationships.service import TaskRelationshipService
    from edison.core.task.workflow import TaskQAWorkflow

    root_task = "910-wave1-bundle-root"
    member_task = "911-wave1-bundle-member"

    workflow = TaskQAWorkflow(isolated_project_env)
    workflow.create_task(task_id=root_task, title="Root", create_qa=True)
    workflow.create_task(task_id=member_task, title="Member", create_qa=True)

    TaskRelationshipService(project_root=isolated_project_env).add(
        task_id=member_task,
        rel_type="bundle_root",
        target_id=root_task,
    )

    root_ev = EvidenceService(root_task, project_root=isolated_project_env)

    from edison.cli.qa.round.prepare import main as prepare_main

    rc = prepare_main(
        argparse.Namespace(
            task_id=member_task,
            scope="bundle",
            session=None,
            status="pending",
            note=None,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    round_num = root_ev.get_current_round()
    assert round_num is not None
    round_dir = root_ev.get_round_dir(int(round_num))
    assert (round_dir / "implementation-report.md").exists()
    assert (round_dir / "validation-summary.md").exists()
