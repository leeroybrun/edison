from __future__ import annotations

from pathlib import Path

from edison.core.composition.registries._types_manager import ComposableTypesManager


def test_templates_type_exists_and_legacy_types_removed(isolated_project_env: Path) -> None:
    manager = ComposableTypesManager(project_root=isolated_project_env)

    assert manager.get_type("templates") is not None
    assert manager.get_type("documents") is None
    assert manager.get_type("templates_documents") is None
    assert manager.get_type("templates_reports") is None


def test_compose_templates_writes_artifact_files(isolated_project_env: Path) -> None:
    manager = ComposableTypesManager(project_root=isolated_project_env)

    manager.write_type("templates")

    generated_root = isolated_project_env / ".edison" / "_generated" / "templates"

    task_tpl = generated_root / "TASK.md"
    qa_tpl = generated_root / "QA.md"
    impl_tpl = generated_root / "IMPLEMENTATION_REPORT.md"

    assert task_tpl.exists()
    assert qa_tpl.exists()
    assert impl_tpl.exists()

    assert "<!-- REQUIRED FILL: AcceptanceCriteria -->" in task_tpl.read_text(encoding="utf-8")
    assert "<!-- REQUIRED FILL: ValidationDimensions -->" in qa_tpl.read_text(encoding="utf-8")
    assert "<!-- REQUIRED FILL: TestsAndEvidence -->" in impl_tpl.read_text(encoding="utf-8")

