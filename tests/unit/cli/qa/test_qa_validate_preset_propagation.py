from __future__ import annotations

import argparse
from pathlib import Path

import pytest


@pytest.mark.qa
def test_qa_validate_execute_uses_preset_in_executor_auto_mode(
    isolated_project_env: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    # Define a validator that is ONLY included by the "deep" preset (no triggers).
    (isolated_project_env / ".edison" / "config" / "validation.yaml").write_text(
        "\n".join(
            [
                "validation:",
                "  defaultPreset: fast",
                "  presets:",
                "    fast:",
                "      name: fast",
                "      validators: []",
                "      required_evidence: []",
                "      blocking_validators: []",
                "    deep:",
                "      name: deep",
                "      validators: ['alpha']",
                "      required_evidence: []",
                "      blocking_validators: ['alpha']",
                "  validators:",
                "    global-claude:",
                "      enabled: false",
                "    global-codex:",
                "      enabled: false",
                "    alpha:",
                "      name: Alpha",
                "      engine: pal-mcp",
                "      wave: deep_test",
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

    task_id = "900-wave1-preset-root"
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
            wave="deep_test",
            preset="deep",
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

    # The preset-selected validator should be part of execution, resulting in delegation output.
    assert (ev.get_round_dir(1) / "delegation-alpha.md").exists()


@pytest.mark.qa
def test_qa_validate_execute_without_preset_uses_validation_default_preset(
    isolated_project_env: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    # Ensure qa validate --execute does NOT silently use sessionClose.preset as the default.
    # When no preset is provided, preset selection must come from validation.defaultPreset.
    (isolated_project_env / ".edison" / "config" / "validation.yaml").write_text(
        "\n".join(
            [
                "validation:",
                "  defaultPreset: fast",
                "  sessionClose:",
                "    preset: deep",
                "  presets:",
                "    fast:",
                "      name: fast",
                "      validators: []",
                "      required_evidence: []",
                "      blocking_validators: []",
                "    deep:",
                "      name: deep",
                "      validators: ['alpha']",
                "      required_evidence: []",
                "      blocking_validators: ['alpha']",
                "  validators:",
                "    global-claude:",
                "      enabled: false",
                "    global-codex:",
                "      enabled: false",
                "    alpha:",
                "      name: Alpha",
                "      engine: pal-mcp",
                "      wave: deep_test",
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

    task_id = "902-wave1-default-preset"
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
            wave="deep_test",
            preset=None,
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

    # Bundle summaries should reflect the preset that was actually used for selection,
    # which defaults via validation.defaultPreset when no CLI preset override is provided.
    summary = (ev.get_round_dir(1) / ev.bundle_filename).read_text(encoding="utf-8")
    assert "preset: fast" in summary

    # If sessionClose.preset were incorrectly used as the default, alpha would be executed and delegated.
    assert not (ev.get_round_dir(1) / "delegation-alpha.md").exists()


@pytest.mark.qa
def test_qa_round_summarize_verdict_uses_preset_blocking_set_and_allows_empty_blocking(
    isolated_project_env: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    # "quick" has no blocking validators and should be approvable.
    # "deep" includes alpha as blocking, so missing alpha must fail approval.
    (isolated_project_env / ".edison" / "config" / "validation.yaml").write_text(
        "\n".join(
            [
                "validation:",
                "  defaultPreset: quick",
                "  presets:",
                "    quick:",
                "      name: quick",
                "      validators: []",
                "      required_evidence: []",
                "      blocking_validators: []",
                "    deep:",
                "      name: deep",
                "      validators: ['alpha']",
                "      required_evidence: []",
                "      blocking_validators: ['alpha']",
                "  validators:",
                "    global-claude:",
                "      enabled: false",
                "    global-codex:",
                "      enabled: false",
                "    alpha:",
                "      name: Alpha",
                "      engine: pal-mcp",
                "      wave: deep_test",
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

    task_id = "901-wave1-preset-root"
    TaskQAWorkflow(isolated_project_env).create_task(task_id=task_id, title="Root", create_qa=False)

    ev = EvidenceService(task_id, project_root=isolated_project_env)
    ev.ensure_round(1)
    ev.write_implementation_report({"filesChanged": []}, round_num=1)

    from edison.cli.qa.round.summarize_verdict import main as summarize_main

    # Deep preset should NOT approve because alpha has no report.
    rc_deep = summarize_main(
        argparse.Namespace(
            task_id=task_id,
            scope="hierarchy",
            session=None,
            round=1,
            preset="deep",
            add_validators=None,
            sequential=True,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc_deep == 1
    payload = (ev.get_round_dir(1) / ev.bundle_filename).read_text(encoding="utf-8")
    assert "preset: deep" in payload
    assert "- alpha" in payload

    # Quick preset should approve (nothing blocks).
    rc_quick = summarize_main(
        argparse.Namespace(
            task_id=task_id,
            scope="hierarchy",
            session=None,
            round=1,
            preset="quick",
            add_validators=None,
            sequential=True,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc_quick == 0
