from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest


@pytest.mark.task
def test_task_bundle_add_sets_bundle_root_and_qa_bundle_includes_members(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.config.domains.workflow import WorkflowConfig
    from edison.core.task.models import Task
    from edison.core.task.repository import TaskRepository

    wf = WorkflowConfig(repo_root=isolated_project_env)
    repo = TaskRepository(project_root=isolated_project_env)

    root_task_id = "T-ROOT"
    member_task_id = "T-MEMBER"

    repo.save(Task.create(root_task_id, "Root", state=wf.get_semantic_state("task", "done")))
    repo.save(Task.create(member_task_id, "Member", state=wf.get_semantic_state("task", "done")))

    from edison.cli.task.bundle.add import main as add_main

    rc = add_main(
        argparse.Namespace(
            root=root_task_id,
            members=[member_task_id],
            force=False,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload.get("rootTask") == root_task_id
    assert member_task_id in (payload.get("members") or [])

    member = repo.get(member_task_id)
    assert member is not None
    bundle_edges = [e for e in (member.relationships or []) if isinstance(e, dict) and e.get("type") == "bundle_root"]
    assert {e.get("target") for e in bundle_edges} == {root_task_id}

    # Bundle manifests should include the member when using bundle scope.
    from edison.cli.qa.bundle import main as qa_bundle_main

    rc2 = qa_bundle_main(
        argparse.Namespace(
            task_id=root_task_id,
            scope="bundle",
            session=None,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc2 == 0
    manifest = json.loads(capsys.readouterr().out)
    assert {t.get("taskId") for t in (manifest.get("tasks") or [])} == {root_task_id, member_task_id}


@pytest.mark.task
def test_task_bundle_remove_clears_bundle_root(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.config.domains.workflow import WorkflowConfig
    from edison.core.task.models import Task
    from edison.core.task.relationships.service import TaskRelationshipService
    from edison.core.task.repository import TaskRepository

    wf = WorkflowConfig(repo_root=isolated_project_env)
    repo = TaskRepository(project_root=isolated_project_env)

    root_task_id = "T-ROOT"
    member_task_id = "T-MEMBER"

    repo.save(Task.create(root_task_id, "Root", state=wf.get_semantic_state("task", "done")))
    repo.save(Task.create(member_task_id, "Member", state=wf.get_semantic_state("task", "done")))

    TaskRelationshipService(project_root=isolated_project_env).add(
        task_id=member_task_id,
        rel_type="bundle_root",
        target_id=root_task_id,
        force=True,
    )

    from edison.cli.task.bundle.remove import main as remove_main

    rc = remove_main(
        argparse.Namespace(
            members=[member_task_id],
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload.get("removed") and payload["removed"][0]["taskId"] == member_task_id

    member = repo.get(member_task_id)
    assert member is not None
    bundle_edges = [e for e in (member.relationships or []) if isinstance(e, dict) and e.get("type") == "bundle_root"]
    assert bundle_edges == []


@pytest.mark.task
def test_task_bundle_show_resolves_root_and_members(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.config.domains.workflow import WorkflowConfig
    from edison.core.task.models import Task
    from edison.core.task.relationships.service import TaskRelationshipService
    from edison.core.task.repository import TaskRepository

    wf = WorkflowConfig(repo_root=isolated_project_env)
    repo = TaskRepository(project_root=isolated_project_env)

    root_task_id = "T-ROOT"
    a = "T-A"
    b = "T-B"

    repo.save(Task.create(root_task_id, "Root", state=wf.get_semantic_state("task", "done")))
    repo.save(Task.create(a, "A", state=wf.get_semantic_state("task", "done")))
    repo.save(Task.create(b, "B", state=wf.get_semantic_state("task", "done")))

    rel = TaskRelationshipService(project_root=isolated_project_env)
    rel.add(task_id=a, rel_type="bundle_root", target_id=root_task_id, force=True)
    rel.add(task_id=b, rel_type="bundle_root", target_id=root_task_id, force=True)

    from edison.cli.task.bundle.show import main as show_main

    rc = show_main(
        argparse.Namespace(
            task_id=a,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload.get("rootTask") == root_task_id
    assert set(payload.get("members") or []) == {a, b}

