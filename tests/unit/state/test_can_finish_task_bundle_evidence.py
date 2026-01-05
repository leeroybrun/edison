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


def _write_minimal_round_artifacts(*, repo: Path, task_id: str, round_num: int, include_test: bool) -> None:
    from edison.core.qa.evidence import EvidenceService

    ev = EvidenceService(task_id, project_root=repo)
    ev.ensure_round(round_num)
    ev.write_implementation_report(
        {
            "taskId": task_id,
            "round": int(round_num),
            "completionStatus": "partial",
            "followUpTasks": [],
            "notesForValidator": "",
        },
        round_num=round_num,
    )
    if include_test:
        (ev.get_round_dir(round_num) / "command-test.txt").write_text("ok\n", encoding="utf-8")


@pytest.mark.fast
def test_can_finish_task_allows_bundle_member_to_use_root_command_evidence(
    isolated_project_env: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)
    _write_validation_config(isolated_project_env)

    from tests.helpers.cache_utils import reset_edison_caches

    reset_edison_caches()

    from edison.core.qa.evidence import EvidenceService
    from edison.core.state.builtin.guards.task import can_finish_task
    from edison.core.task.workflow import TaskQAWorkflow

    root_id = "900-bundle-root"
    member_id = "901-bundle-member"

    TaskQAWorkflow(isolated_project_env).create_task(task_id=root_id, title="Root", create_qa=False)
    TaskQAWorkflow(isolated_project_env).create_task(task_id=member_id, title="Member", create_qa=False)

    _write_minimal_round_artifacts(repo=isolated_project_env, task_id=root_id, round_num=1, include_test=True)
    _write_minimal_round_artifacts(repo=isolated_project_env, task_id=member_id, round_num=1, include_test=False)

    # Bundle summary mirrored into the member's evidence dir indicates that the bundle root
    # ran validation and evidence collection for the cluster.
    member_ev = EvidenceService(member_id, project_root=isolated_project_env)
    member_ev.write_bundle(
        {
            "taskId": member_id,
            "rootTask": root_id,
            "rootRound": 1,
            "scope": "bundle",
            "preset": "standard",
            "round": 1,
            "approved": True,
            "tasks": [{"taskId": root_id}, {"taskId": member_id}],
            "validators": [],
            "missing": [],
            "nonBlockingFollowUps": [],
        },
        round_num=1,
    )

    assert (
        can_finish_task(
            {
                "task": {"id": member_id},
                "project_root": isolated_project_env,
                "enforce_evidence": True,
                "skip_context7": True,
                "skip_context7_reason": "no post-training packages touched",
            }
        )
        is True
    )


@pytest.mark.fast
def test_can_finish_task_requires_per_task_evidence_when_not_in_approved_bundle(
    isolated_project_env: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)
    _write_validation_config(isolated_project_env)

    from tests.helpers.cache_utils import reset_edison_caches

    reset_edison_caches()

    from edison.core.state.builtin.guards.task import can_finish_task
    from edison.core.task.workflow import TaskQAWorkflow

    task_id = "902-not-bundled"
    TaskQAWorkflow(isolated_project_env).create_task(task_id=task_id, title="Solo", create_qa=False)

    _write_minimal_round_artifacts(repo=isolated_project_env, task_id=task_id, round_num=1, include_test=False)

    with pytest.raises(ValueError, match=r"Missing evidence files in round-1: command-test\.txt"):
        can_finish_task(
            {
                "task": {"id": task_id},
                "project_root": isolated_project_env,
                "enforce_evidence": True,
                "skip_context7": True,
                "skip_context7_reason": "no post-training packages touched",
            }
        )
