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
def test_task_done_completes_task(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.task.repository import TaskRepository
    from edison.core.task.workflow import TaskQAWorkflow

    session_id = "sess-1"
    task_id = "12007-wave8-db-remove-tracked-prisma-backups"

    SessionRepository(isolated_project_env).create(Session.create(session_id, state="wip"))

    workflow = TaskQAWorkflow(isolated_project_env)
    workflow.create_task(task_id=task_id, title="Test", session_id=None, create_qa=True)
    workflow.claim_task(task_id, session_id)

    _create_minimal_round_1_evidence(isolated_project_env, task_id)

    from edison.cli.task.done import main as done_main

    rc = done_main(
        argparse.Namespace(
            record_id=task_id,
            session=session_id,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["record_id"] == task_id
    assert payload["state"] == "done"

    updated = TaskRepository(project_root=isolated_project_env).get(task_id)
    assert updated is not None
    assert updated.state == "done"


@pytest.mark.task
def test_task_done_resolves_short_id_prefix(
    isolated_project_env: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.task.repository import TaskRepository
    from edison.core.task.workflow import TaskQAWorkflow

    session_id = "sess-2"
    task_id = "12008-wave8-api-tests"

    SessionRepository(isolated_project_env).create(Session.create(session_id, state="wip"))

    workflow = TaskQAWorkflow(isolated_project_env)
    workflow.create_task(task_id=task_id, title="Test", session_id=None, create_qa=False)
    workflow.claim_task(task_id, session_id)
    _create_minimal_round_1_evidence(isolated_project_env, task_id)

    from edison.cli.task.done import main as done_main

    rc = done_main(
        argparse.Namespace(
            record_id="12008",
            session=session_id,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    updated = TaskRepository(project_root=isolated_project_env).get(task_id)
    assert updated is not None
    assert updated.state == "done"


@pytest.mark.task
def test_task_done_requires_reason_when_skipping_context7(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.task.workflow import TaskQAWorkflow

    session_id = "sess-4"
    task_id = "ctx7-skip-reason"

    SessionRepository(isolated_project_env).create(Session.create(session_id, state="wip"))

    workflow = TaskQAWorkflow(isolated_project_env)
    workflow.create_task(task_id=task_id, title="Test", session_id=None, create_qa=False)
    workflow.claim_task(task_id, session_id)
    _create_minimal_round_1_evidence(isolated_project_env, task_id)

    from edison.cli.task.done import main as done_main

    rc = done_main(
        argparse.Namespace(
            record_id=task_id,
            session=session_id,
            json=True,
            repo_root=str(isolated_project_env),
            skip_context7=True,
            skip_context7_reason="",
        )
    )
    assert rc == 1
    captured = capsys.readouterr()
    assert "skip-context7" in (captured.out + captured.err).lower()
    assert "reason" in (captured.out + captured.err).lower()


@pytest.mark.task
def test_task_done_allows_context7_bypass_with_reason(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.task.repository import TaskRepository
    from edison.core.task.workflow import TaskQAWorkflow

    (isolated_project_env / ".edison" / "config" / "context7.yaml").write_text(
        """
context7:
  triggers:
    react: ["**/*.tsx"]
""".lstrip(),
        encoding="utf-8",
    )

    session_id = "sess-5"
    task_id = "ctx7-skip-ok"

    SessionRepository(isolated_project_env).create(Session.create(session_id, state="wip"))

    workflow = TaskQAWorkflow(isolated_project_env)
    workflow.create_task(task_id=task_id, title="Test", session_id=None, create_qa=False)
    workflow.claim_task(task_id, session_id)

    # Make Context7 detection trigger from the task spec (Primary Files / Areas).
    repo = TaskRepository(project_root=isolated_project_env)
    task_path = repo.get_path(task_id)
    task_path.write_text(
        task_path.read_text(encoding="utf-8")
        + "\n## Primary Files / Areas\n- ui/Widget.tsx\n",
        encoding="utf-8",
    )

    _create_minimal_round_1_evidence(isolated_project_env, task_id)

    from edison.cli.task.done import main as done_main

    rc = done_main(
        argparse.Namespace(
            record_id=task_id,
            session=session_id,
            json=True,
            repo_root=str(isolated_project_env),
            skip_context7=True,
            skip_context7_reason="verified false positive",
        )
    )
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["record_id"] == task_id
    assert payload.get("skip_context7") is True
    assert payload.get("skip_context7_reason") == "verified false positive"

@pytest.mark.task
def test_task_ready_with_record_id_delegates_to_done_with_warning(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.session.core.models import Session
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.task.repository import TaskRepository
    from edison.core.task.workflow import TaskQAWorkflow

    session_id = "sess-3"
    task_id = "12009-wave8-legacy"

    SessionRepository(isolated_project_env).create(Session.create(session_id, state="wip"))

    workflow = TaskQAWorkflow(isolated_project_env)
    workflow.create_task(task_id=task_id, title="Test", session_id=None, create_qa=False)
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

    captured = capsys.readouterr()
    assert "deprecated" in captured.err.lower()
    assert "edison task done" in captured.err.lower()

    updated = TaskRepository(project_root=isolated_project_env).get(task_id)
    assert updated is not None
    assert updated.state == "done"
