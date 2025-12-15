from __future__ import annotations

from pathlib import Path


def test_build_validation_manifest_includes_descendants(isolated_project_env: Path) -> None:
    from edison.core.config.domains.workflow import WorkflowConfig
    from edison.core.task.models import Task
    from edison.core.task.repository import TaskRepository
    from edison.core.qa.models import QARecord
    from edison.core.qa.workflow.repository import QARepository

    wf = WorkflowConfig(repo_root=isolated_project_env)

    task_repo = TaskRepository(project_root=isolated_project_env)
    qa_repo = QARepository(project_root=isolated_project_env)

    parent = Task.create("T-PARENT", "Parent", state=wf.get_semantic_state("task", "done"))
    task_repo.save(parent)

    child = Task.create(
        "T-CHILD",
        "Child",
        state=wf.get_semantic_state("task", "done"),
        parent_id="T-PARENT",
    )
    task_repo.save(child)

    qa_state = wf.get_semantic_state("qa", "done")
    qa_repo.save(
        QARecord(
            id="T-PARENT-qa",
            task_id="T-PARENT",
            state=qa_state,
            title="QA parent",
            session_id=None,
            metadata=parent.metadata,
        )
    )
    qa_repo.save(
        QARecord(
            id="T-CHILD-qa",
            task_id="T-CHILD",
            state=qa_state,
            title="QA child",
            session_id=None,
            metadata=child.metadata,
        )
    )

    from edison.core.qa.bundler.manifest import build_validation_manifest

    manifest = build_validation_manifest("T-PARENT", project_root=isolated_project_env)
    assert manifest["rootTask"] == "T-PARENT"

    task_ids = {t["taskId"] for t in (manifest.get("tasks") or [])}
    assert task_ids == {"T-PARENT", "T-CHILD"}
