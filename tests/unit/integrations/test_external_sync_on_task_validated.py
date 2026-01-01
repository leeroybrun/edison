import pytest


def _init_min_project_root(project_root):
    (project_root / ".project").mkdir(parents=True, exist_ok=True)
    (project_root / "edison.yaml").write_text("project:\n  name: test-project\n", encoding="utf-8")


def _write_min_implementation_report(project_root, task_id: str) -> None:
    report = (
        project_root
        / ".project"
        / "qa"
        / "validation-evidence"
        / task_id
        / "round-1"
        / "implementation-report.md"
    )
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("---\nreport_type: implementation\n---\n\nok: true\n", encoding="utf-8")


def test_task_validated_action_marks_speckit_task_checkbox(tmp_path, monkeypatch):
    project_root = tmp_path / "proj"
    project_root.mkdir()
    _init_min_project_root(project_root)

    # SpecKit source artifact
    (project_root / "specs" / "auth").mkdir(parents=True)
    tasks_md = project_root / "specs" / "auth" / "tasks.md"
    tasks_md.write_text(
        "## Phase 1: Setup\n\n- [ ] T001 Create project structure\n- [ ] T002 Initialize deps\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(project_root))
    monkeypatch.chdir(project_root)

    from edison.core.task.repository import TaskRepository
    from edison.core.task.models import Task
    from edison.core.entity import EntityMetadata

    repo = TaskRepository(project_root=project_root)
    task = Task(
        id="auth-T001",
        state="done",
        title="Create project structure",
        description="",
        tags=["speckit", "auth"],
        metadata=EntityMetadata.create(created_by="test"),
        integration={
            "kind": "speckit",
            "speckit": {"tasks_md": "specs/auth/tasks.md", "task_id": "T001"},
        },
    )
    repo.save(task)
    _write_min_implementation_report(project_root, task.id)

    # Transition should trigger external sync on validated.
    repo.transition(task.id, "validated", context={"session": {"id": "S1"}})

    updated = tasks_md.read_text(encoding="utf-8")
    assert "- [x] T001 Create project structure" in updated


def test_task_validated_action_marks_all_openspec_task_checkboxes(tmp_path, monkeypatch):
    project_root = tmp_path / "proj"
    project_root.mkdir()
    _init_min_project_root(project_root)

    # OpenSpec source artifacts
    change_dir = project_root / "openspec" / "changes" / "add-thing"
    change_dir.mkdir(parents=True)
    (change_dir / "proposal.md").write_text("# Add thing\n", encoding="utf-8")
    tasks_md = change_dir / "tasks.md"
    tasks_md.write_text(
        "## 1. Implementation\n- [ ] 1.1 Do first\n  - [ ] 1.1.1 Nested\n- [ ] 1.2 Do second\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(project_root))
    monkeypatch.chdir(project_root)

    from edison.core.task.repository import TaskRepository
    from edison.core.task.models import Task
    from edison.core.entity import EntityMetadata

    repo = TaskRepository(project_root=project_root)
    task = Task(
        id="openspec-add-thing",
        state="done",
        title="Add thing",
        description="",
        tags=["openspec", "openspec-change"],
        metadata=EntityMetadata.create(created_by="test"),
        integration={
            "kind": "openspec",
            "openspec": {"change_id": "add-thing", "tasks_md": "openspec/changes/add-thing/tasks.md"},
        },
    )
    repo.save(task)
    _write_min_implementation_report(project_root, task.id)

    repo.transition(task.id, "validated", context={"session": {"id": "S1"}})

    updated = tasks_md.read_text(encoding="utf-8")
    assert "- [x] 1.1 Do first" in updated
    assert "- [x] 1.1.1 Nested" in updated
    assert "- [x] 1.2 Do second" in updated
