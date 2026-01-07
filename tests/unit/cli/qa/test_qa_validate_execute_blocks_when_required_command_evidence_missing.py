from __future__ import annotations

import argparse
from pathlib import Path

import pytest


@pytest.mark.qa
def test_qa_validate_execute_blocks_when_required_command_evidence_missing(
    isolated_project_env: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    # Configure a delegated validator and require command evidence via preset.
    (isolated_project_env / ".edison" / "config" / "validation.yaml").write_text(
        "\n".join(
            [
                "validation:",
                "  defaultPreset: standard",
                "  presets:",
                "    standard:",
                "      name: standard",
                "      validators: ['alpha']",
                "      blocking_validators: ['alpha']",
                "      required_evidence:",
                "        - command-test.txt",
                "        - command-lint.txt",
                "  validators:",
                "    global-claude:",
                "      enabled: false",
                "    global-codex:",
                "      enabled: false",
                "    alpha:",
                "      name: Alpha",
                "      engine: pal-mcp",
                "      wave: bundle_test",
                "      always_run: false",
                "      blocking: true",
                "      triggers: []",
                "      focus: []",
                "",
            ]
        ),
        encoding="utf-8",
    )

    from edison.core.qa.evidence import EvidenceService
    from edison.core.task.workflow import TaskQAWorkflow

    task_id = "920-wave1-validate-blocks-missing-evidence"
    TaskQAWorkflow(isolated_project_env).create_task(task_id=task_id, title="Root", create_qa=False)

    ev = EvidenceService(task_id, project_root=isolated_project_env)
    ev.ensure_round(1)
    ev.write_implementation_report({"filesChanged": []}, round_num=1)

    from edison.cli.qa.validate import main as validate_main

    rc = validate_main(
        argparse.Namespace(
            task_id=task_id,
            scope="hierarchy",
            session=None,
            round=1,
            wave=None,
            preset="standard",
            validators=None,
            add_validators=None,
            blocking_only=False,
            execute=True,
            sequential=True,
            dry_run=False,
            max_workers=1,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 1

    # Ensure we did not execute validators (delegated output would exist).
    assert not (ev.get_round_dir(1) / "delegation-alpha.md").exists()

