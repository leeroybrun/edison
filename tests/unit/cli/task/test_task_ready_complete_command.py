from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest


def _create_minimal_round_1_evidence(project_root: Path, task_id: str) -> None:
    """Create minimal evidence needed for task completion guards."""
    from edison.core.config.domains.qa import QAConfig
    from edison.core.qa.evidence import EvidenceService

    ev = EvidenceService(task_id, project_root=project_root)
    round_dir = ev.get_evidence_root() / "round-1"
    round_dir.mkdir(parents=True, exist_ok=True)

    (round_dir / "implementation-report.md").write_text(
        f"""---
taskId: "{task_id}"
round: 1
status: "complete"
summary: "Test implementation"
---
""",
        encoding="utf-8",
    )

    required = QAConfig(repo_root=project_root).get_required_evidence_files()
    for name in required:
        (round_dir / str(name)).write_text("PASS\n", encoding="utf-8")


@pytest.mark.task
def test_task_ready_with_record_id_completes_task(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.task.workflow import TaskQAWorkflow
    from edison.core.task.repository import TaskRepository

    session_id = "sess-1"
    task_id = "12007-wave8-db-remove-tracked-prisma-backups"

    SessionRepository(isolated_project_env).create(Session.create(session_id, state="wip"))

    workflow = TaskQAWorkflow(isolated_project_env)
    workflow.create_task(task_id=task_id, title="Test", session_id=None, create_qa=True)
    workflow.claim_task(task_id, session_id)

    _create_minimal_round_1_evidence(isolated_project_env, task_id)

    from edison.cli.task.ready import main as ready_main

    rc = ready_main(
        argparse.Namespace(
            record_id=task_id,
            session=session_id,
            run=False,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["record_id"] == task_id
    assert payload["ready"] is True
    assert payload["state"] == "done"
    assert payload["session_id"] == session_id

    updated = TaskRepository(project_root=isolated_project_env).get(task_id)
    assert updated is not None
    assert updated.state == "done"

