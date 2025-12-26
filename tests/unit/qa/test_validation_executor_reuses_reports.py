from __future__ import annotations


from edison.core.qa.engines import ValidationExecutor
from edison.core.qa.evidence import EvidenceService


def test_validation_executor_reuses_existing_validator_report(tmp_path) -> None:
    # Arrange: create a round + an approved report for a blocking validator.
    task_id = "t-001"
    session_id = "sess-001"

    ev = EvidenceService(task_id, project_root=tmp_path)
    ev.create_next_round()
    round_num = ev.get_current_round()
    assert round_num == 1

    ev.write_validator_report(
        "global-codex",
        {
            "taskId": task_id,
            "round": round_num,
            "validatorId": "global-codex",
            "model": "codex",
            "verdict": "approve",
            "tracking": {},
        },
        round_num=round_num,
    )

    # Act: execute only that validator. If the report is reused, the executor should
    # treat it as already approved and not delegate / re-run it.
    executor = ValidationExecutor(project_root=tmp_path, max_workers=1)
    result = executor.execute(
        task_id=task_id,
        session_id=session_id,
        wave="critical",
        validators=["global-codex"],
        parallel=False,
        round_num=round_num,
        evidence_service=ev,
    )

    # Assert
    assert result.all_blocking_passed is True
    assert result.blocking_failed == []
    assert result.delegated_validators == []
    assert result.passed_count == 1
    assert result.failed_count == 0
    assert result.pending_count == 0








