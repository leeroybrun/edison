from __future__ import annotations

from pathlib import Path

import pytest


def _write_validation_config(repo: Path) -> None:
    (repo / ".edison" / "config").mkdir(parents=True, exist_ok=True)
    (repo / ".edison" / "config" / "validation.yaml").write_text(
        "\n".join(
            [
                "validation:",
                "  defaultPreset: standard",
                "  evidence:",
                "    requiredFiles:",
                "      - command-test.txt",
                "  presets:",
                "    standard:",
                "      name: standard",
                "      validators: []",
                "      blocking_validators: []",
                "",
            ]
        ),
        encoding="utf-8",
    )


@pytest.mark.fast
def test_has_required_evidence_allows_bundle_member_to_use_root_round(
    isolated_project_env: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)
    _write_validation_config(isolated_project_env)

    from tests.helpers.cache_utils import reset_edison_caches

    reset_edison_caches()

    from edison.core.qa.evidence import EvidenceService
    from edison.core.state.builtin.conditions.qa import has_required_evidence
    from edison.core.task.workflow import TaskQAWorkflow

    root_id = "910-evidence-root"
    member_id = "911-evidence-member"

    TaskQAWorkflow(isolated_project_env).create_task(task_id=root_id, title="Root", create_qa=False)
    TaskQAWorkflow(isolated_project_env).create_task(task_id=member_id, title="Member", create_qa=False)

    root_ev = EvidenceService(root_id, project_root=isolated_project_env)
    root_ev.ensure_round(1)
    (root_ev.get_round_dir(1) / "command-test.txt").write_text("ok\n", encoding="utf-8")
    root_ev.write_implementation_report({"taskId": root_id, "round": 1}, round_num=1)

    member_ev = EvidenceService(member_id, project_root=isolated_project_env)
    member_ev.ensure_round(1)
    member_ev.write_implementation_report({"taskId": member_id, "round": 1}, round_num=1)
    member_ev.write_bundle(
        {
            "taskId": member_id,
            "rootTask": root_id,
            "scope": "bundle",
            "round": 1,
            "approved": True,
            "validators": [{"validatorId": "x", "verdict": "approve"}],
            "missing": [],
        },
        round_num=1,
    )

    assert has_required_evidence({"task_id": member_id}) is True


@pytest.mark.fast
def test_has_required_evidence_fails_closed_without_bundle_or_evidence(
    isolated_project_env: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)
    _write_validation_config(isolated_project_env)

    from tests.helpers.cache_utils import reset_edison_caches

    reset_edison_caches()

    from edison.core.qa.evidence import EvidenceService
    from edison.core.state.builtin.conditions.qa import has_required_evidence
    from edison.core.task.workflow import TaskQAWorkflow

    task_id = "912-evidence-solo"
    TaskQAWorkflow(isolated_project_env).create_task(task_id=task_id, title="Solo", create_qa=False)

    ev = EvidenceService(task_id, project_root=isolated_project_env)
    ev.ensure_round(1)
    ev.write_implementation_report({"taskId": task_id, "round": 1}, round_num=1)

    assert has_required_evidence({"task_id": task_id}) is False

