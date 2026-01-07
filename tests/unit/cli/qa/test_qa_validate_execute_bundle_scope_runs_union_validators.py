from __future__ import annotations

import argparse
from pathlib import Path

import pytest


@pytest.mark.qa
def test_qa_validate_execute_bundle_scope_runs_union_of_cluster_validators(
    isolated_project_env: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    # Add two delegated validators in a dedicated wave so execution is fast and deterministic.
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
                "    beta:",
                "      name: Beta",
                "      engine: pal-mcp",
                "      wave: bundle_test",
                "      always_run: false",
                "      blocking: true",
                "      triggers: ['beta.txt']",
                "      focus: []",
                "",
            ]
        ),
        encoding="utf-8",
    )

    from edison.core.qa.evidence import EvidenceService
    from edison.core.task.relationships.service import TaskRelationshipService
    from edison.core.task.workflow import TaskQAWorkflow

    root_task = "900-wave1-bundle-root"
    member_task = "901-wave1-bundle-member"
    workflow = TaskQAWorkflow(isolated_project_env)
    workflow.create_task(task_id=root_task, title="Root", create_qa=False)
    workflow.create_task(task_id=member_task, title="Member", create_qa=False)

    TaskRelationshipService(project_root=isolated_project_env).add(
        task_id=member_task,
        rel_type="bundle_root",
        target_id=root_task,
    )

    root_ev = EvidenceService(root_task, project_root=isolated_project_env)
    member_ev = EvidenceService(member_task, project_root=isolated_project_env)
    root_ev.ensure_round(1)
    member_ev.ensure_round(1)

    root_ev.write_implementation_report({"filesChanged": ["alpha.txt"]}, round_num=1)
    member_ev.write_implementation_report({"filesChanged": ["beta.txt"]}, round_num=1)

    from edison.cli.qa.validate import main as validate_main

    rc = validate_main(
        argparse.Namespace(
            task_id=member_task,
            scope="bundle",
            session=None,
            round=1,
            wave="bundle_test",
            preset="quick",
            validators=None,
            add_validators=None,
            blocking_only=False,
            execute=True,
            sequential=True,
            dry_run=False,
            max_workers=1,
            json=False,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc in (0, 1)

    round_dir = root_ev.get_round_dir(1)
    assert (round_dir / "delegation-alpha.md").exists()
    assert (round_dir / "delegation-beta.md").exists()
