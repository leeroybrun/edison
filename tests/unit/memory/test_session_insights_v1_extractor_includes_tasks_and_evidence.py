from __future__ import annotations

from pathlib import Path

from tests.helpers.fixtures import create_qa_file, create_task_file
from tests.helpers.session import ensure_session


def test_session_insights_v1_includes_completed_tasks_qas_and_evidence(
    isolated_project_env: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)
    ensure_session("sess-1", state="active")

    task_id = "T-INS-1"
    create_task_file(isolated_project_env, task_id, state="done", session_id="sess-1")
    create_qa_file(isolated_project_env, f"{task_id}-qa", task_id, state="done", session_id="sess-1")

    from edison.core.qa.evidence.service import EvidenceService

    ev = EvidenceService(task_id, project_root=isolated_project_env)
    ev.ensure_round(1)
    ev.write_implementation_report(
        {
            "taskId": task_id,
            "round": 1,
            "implementationApproach": "orchestrator-direct",
            "primaryModel": "codex",
            "completionStatus": "complete",
            "followUpTasks": [{"title": "Add regression test", "blockingBeforeValidation": False, "claimNow": False}],
            "notesForValidator": "All good",
            "tracking": {"processId": 1, "startedAt": "2025-01-01T00:00:00+00:00", "completedAt": "2025-01-01T00:00:01+00:00"},
        },
        round_num=1,
    )
    ev.write_validator_report(
        "security",
        {
            "taskId": task_id,
            "round": 1,
            "validatorId": "security",
            "model": "codex",
            "verdict": "approve",
            "strengths": ["Good input validation"],
            "findings": [],
            "summary": "OK",
            "followUpTasks": [],
            "tracking": {"processId": 2, "startedAt": "2025-01-01T00:00:00+00:00", "completedAt": "2025-01-01T00:00:01+00:00"},
        },
        round_num=1,
    )

    from edison.core.memory.insights import extract_session_insights_v1

    out = extract_session_insights_v1(project_root=isolated_project_env, session_id="sess-1")

    assert task_id in out.get("tasksCompleted", [])
    assert f"{task_id}-qa" in out.get("qasCompleted", [])

    summaries = out.get("evidenceSummaries", [])
    assert isinstance(summaries, list) and summaries
    first = summaries[0]
    assert first.get("taskId") == task_id

    what_worked = out.get("whatWorked", [])
    assert any("Good input validation" in str(x) for x in what_worked)

