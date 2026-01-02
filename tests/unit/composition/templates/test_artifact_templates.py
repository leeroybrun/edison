from __future__ import annotations

from pathlib import Path

from edison.core.composition.registries._types_manager import ComposableTypesManager
from edison.data import get_data_path


def test_templates_type_exists_and_legacy_types_removed(isolated_project_env: Path) -> None:
    manager = ComposableTypesManager(project_root=isolated_project_env)

    assert manager.get_type("templates") is not None
    assert manager.get_type("documents") is None
    assert manager.get_type("templates_documents") is None
    assert manager.get_type("templates_reports") is None


def test_compose_templates_writes_artifact_files(isolated_project_env: Path) -> None:
    # Bundled templates live under templates/artifacts/ so the templates root can
    # contain non-artifact templates (commands, hooks, etc.) without being
    # accidentally composed into `.edison/_generated/templates/`.
    assert (get_data_path("templates") / "artifacts" / "TASK.md").exists()
    assert (get_data_path("templates") / "artifacts" / "QA.md").exists()
    assert (get_data_path("templates") / "artifacts" / "IMPLEMENTATION_REPORT.md").exists()
    assert not (get_data_path("templates") / "TASK.md").exists()
    assert not (get_data_path("templates") / "QA.md").exists()
    assert not (get_data_path("templates") / "IMPLEMENTATION_REPORT.md").exists()

    manager = ComposableTypesManager(project_root=isolated_project_env)

    manager.write_type("templates")

    generated_root = isolated_project_env / ".edison" / "_generated" / "templates"

    task_tpl = generated_root / "TASK.md"
    qa_tpl = generated_root / "QA.md"
    impl_tpl = generated_root / "IMPLEMENTATION_REPORT.md"

    assert task_tpl.exists()
    assert qa_tpl.exists()
    assert impl_tpl.exists()

    # Exclude non-artifact markdown from the generated templates output.
    assert not (generated_root / "README.md").exists()

    assert "<!-- REQUIRED FILL: AcceptanceCriteria -->" in task_tpl.read_text(encoding="utf-8")
    assert "<!-- REQUIRED FILL: ValidationDimensions -->" in qa_tpl.read_text(encoding="utf-8")
    assert "<!-- REQUIRED FILL: TestsAndEvidence -->" in impl_tpl.read_text(encoding="utf-8")

    # Guard against accidental template truncation: these sections are part of the
    # expected Task/QA authoring workflow.
    task_text = task_tpl.read_text(encoding="utf-8")
    assert "## Primary Files / Areas" in task_text
    assert "## Notes" in task_text

    qa_text = qa_tpl.read_text(encoding="utf-8")
    assert "## Approval Status" in qa_text
    assert "## Follow-up Tasks" in qa_text
    assert "## Notes" in qa_text
