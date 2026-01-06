from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.qa
def test_qa_validate_preflight_warns_when_impl_report_fingerprint_is_stale(
    isolated_project_env: Path, monkeypatch
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.qa.evidence import EvidenceService
    from edison.core.task.workflow import TaskQAWorkflow
    from edison.core.utils.git.fingerprint import compute_repo_fingerprint
    from edison.core.workflow.checklists.qa_validate_preflight import QAValidatePreflightChecklistEngine

    task_id = "930-wave1-stale-impl"
    TaskQAWorkflow(isolated_project_env).create_task(task_id=task_id, title="Task", create_qa=False)

    ev = EvidenceService(task_id, project_root=isolated_project_env)
    rd = ev.ensure_round(1)

    fp_before = compute_repo_fingerprint(isolated_project_env)
    ev.write_implementation_report(
        {
            "taskId": task_id,
            "round": 1,
            "gitHead": fp_before.get("gitHead"),
            "gitDirty": fp_before.get("gitDirty"),
            "diffHash": fp_before.get("diffHash"),
        },
        round_num=1,
        body="\n## Changes in this round (required)\n\n- none\n",
        preserve_existing_body=False,
    )

    # Change repo state after report was written.
    (isolated_project_env / "stale.txt").write_text("changed\n", encoding="utf-8")

    checklist = QAValidatePreflightChecklistEngine(project_root=isolated_project_env).compute(
        task_id=task_id,
        session_id=None,
        roster={"taskId": task_id, "alwaysRequired": [], "triggeredBlocking": [], "triggeredOptional": []},
        round_num=1,
        will_execute=False,
        root_task_id=task_id,
        scope_used="hierarchy",
        cluster_task_ids=[task_id],
    )

    items = checklist.get("items") or []
    impl = next((i for i in items if i.get("id") == "implementation-report"), None)
    assert impl is not None
    assert impl.get("severity") == "warning"
    assert impl.get("status") in {"stale", "warning"}
    assert any("implementation-report.md" in str(p) for p in (impl.get("evidencePaths") or []))
