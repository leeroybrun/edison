from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest


@pytest.mark.qa
def test_qa_bundle_json_includes_scope_and_resolves_bundle_root(
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
    task_repo = TaskRepository(project_root=isolated_project_env)

    root = Task.create("T-ROOT", "Root", state=wf.get_semantic_state("task", "done"))
    a = Task.create("T-A", "A", state=wf.get_semantic_state("task", "done"))
    b = Task.create("T-B", "B", state=wf.get_semantic_state("task", "done"))
    task_repo.save(root)
    task_repo.save(a)
    task_repo.save(b)

    rel = TaskRelationshipService(project_root=isolated_project_env)
    rel.add(task_id="T-A", rel_type="bundle_root", target_id="T-ROOT", force=True)
    rel.add(task_id="T-B", rel_type="bundle_root", target_id="T-ROOT", force=True)

    from edison.cli.qa.bundle import main as bundle_main

    rc = bundle_main(
        argparse.Namespace(
            task_id="T-A",
            scope="bundle",
            session=None,
            json=True,
            repo_root=str(isolated_project_env),
        )
    )
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload.get("rootTask") == "T-ROOT"
    assert payload.get("scope") == "bundle"
    tasks = payload.get("tasks") or []
    assert {t.get("taskId") for t in tasks} == {"T-ROOT", "T-A", "T-B"}

    # Bundle summary is written at the resolved root.
    bundle_path = (
        isolated_project_env
        / ".project"
        / "qa"
        / "validation-evidence"
        / "T-ROOT"
        / "round-1"
        / "validation-summary.md"
    )
    assert bundle_path.exists()
