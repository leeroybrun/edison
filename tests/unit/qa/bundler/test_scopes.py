from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.qa
def test_build_validation_manifest_bundle_scope_uses_bundle_root_cluster(
    isolated_project_env: Path,
) -> None:
    from edison.core.config.domains.workflow import WorkflowConfig
    from edison.core.task.models import Task
    from edison.core.task.repository import TaskRepository
    from edison.core.task.relationships.service import TaskRelationshipService

    wf = WorkflowConfig(repo_root=isolated_project_env)
    task_repo = TaskRepository(project_root=isolated_project_env)

    root = Task.create("T-ROOT", "Root", state=wf.get_semantic_state("task", "done"))
    task_repo.save(root)
    a = Task.create("T-A", "A", state=wf.get_semantic_state("task", "done"))
    b = Task.create("T-B", "B", state=wf.get_semantic_state("task", "done"))
    task_repo.save(a)
    task_repo.save(b)

    rel = TaskRelationshipService(project_root=isolated_project_env)
    rel.add(task_id="T-A", rel_type="bundle_root", target_id="T-ROOT", force=True)
    rel.add(task_id="T-B", rel_type="bundle_root", target_id="T-ROOT", force=True)

    from edison.core.qa.bundler.manifest import build_validation_manifest

    manifest = build_validation_manifest("T-A", scope="bundle", project_root=isolated_project_env)
    assert manifest["rootTask"] == "T-ROOT"
    assert manifest["scope"] == "bundle"

    task_ids = {t["taskId"] for t in (manifest.get("tasks") or [])}
    assert task_ids == {"T-ROOT", "T-A", "T-B"}


@pytest.mark.qa
def test_build_validation_manifest_auto_prefers_bundle_over_hierarchy(
    isolated_project_env: Path,
) -> None:
    from edison.core.config.domains.workflow import WorkflowConfig
    from edison.core.task.models import Task
    from edison.core.task.repository import TaskRepository
    from edison.core.task.relationships.service import TaskRelationshipService

    wf = WorkflowConfig(repo_root=isolated_project_env)
    task_repo = TaskRepository(project_root=isolated_project_env)

    root = Task.create("T-ROOT", "Root", state=wf.get_semantic_state("task", "done"))
    task_repo.save(root)
    member = Task.create("T-MEMBER", "Member", state=wf.get_semantic_state("task", "done"))
    task_repo.save(member)

    rel = TaskRelationshipService(project_root=isolated_project_env)
    rel.add(task_id="T-MEMBER", rel_type="bundle_root", target_id="T-ROOT", force=True)

    from edison.core.qa.bundler.manifest import build_validation_manifest

    manifest = build_validation_manifest("T-ROOT", scope="auto", project_root=isolated_project_env)
    assert manifest["rootTask"] == "T-ROOT"
    assert manifest["scope"] == "bundle"


@pytest.mark.qa
def test_build_validation_manifest_uses_config_default_scope_when_scope_omitted(
    isolated_project_env: Path,
) -> None:
    (isolated_project_env / ".edison" / "config" / "validation.yaml").write_text(
        "\n".join(
            [
                "validation:",
                "  bundles:",
                "    defaultScope: bundle",
                "",
            ]
        ),
        encoding="utf-8",
    )

    from edison.core.config.domains.workflow import WorkflowConfig
    from edison.core.task.models import Task
    from edison.core.task.repository import TaskRepository
    from edison.core.task.relationships.service import TaskRelationshipService

    wf = WorkflowConfig(repo_root=isolated_project_env)
    task_repo = TaskRepository(project_root=isolated_project_env)

    root = Task.create("T-ROOT", "Root", state=wf.get_semantic_state("task", "done"))
    child = Task.create("T-CHILD", "Child", state=wf.get_semantic_state("task", "done"))
    task_repo.save(root)
    task_repo.save(child)

    TaskRelationshipService(project_root=isolated_project_env).add(
        task_id="T-CHILD",
        rel_type="parent",
        target_id="T-ROOT",
        force=True,
    )

    from edison.core.qa.bundler.manifest import build_validation_manifest

    # Without config defaultScope=bundle, AUTO would select hierarchy (root has children).
    manifest = build_validation_manifest("T-ROOT", scope=None, project_root=isolated_project_env)
    assert manifest["rootTask"] == "T-ROOT"
    assert manifest["scope"] == "bundle"
    assert [t["taskId"] for t in (manifest.get("tasks") or [])] == ["T-ROOT"]
