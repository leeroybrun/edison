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
    workflow.create_task(task_id=root_task, title="Root", create_qa=False)
    workflow.create_task(task_id=member_task, title="Member", create_qa=False)

    TaskRelationshipService(project_root=isolated_project_env).add(
        task_id=member_task,
        rel_type="bundle_root",
        target_id=root_task,
    )

    root_ev = EvidenceService(root_task, project_root=isolated_project_env)
    root_ev.ensure_round(1)
    # Provide context so roster triggers alpha.
    root_ev.write_implementation_report({"filesChanged": ["alpha.txt"]}, round_num=1)

    from edison.cli.qa.validate import main as validate_main

    rc = validate_main(
        argparse.Namespace(
            task_id=member_task,
            scope="bundle",
            session=None,
            round=None,
            new_round=True,
            wave="bundle_test",
            preset=None,
            validators=None,
            add_validators=None,
            blocking_only=False,
            execute=True,
            check_only=False,
            sequential=True,
            dry_run=False,
            max_workers=1,
            json=False,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc in (0, 1)

    round2_dir = root_ev.get_round_dir(2)
    assert (round2_dir / "implementation-report.md").exists()
    assert (round2_dir / "bundle-summary.md").exists()

