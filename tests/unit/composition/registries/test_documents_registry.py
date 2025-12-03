from __future__ import annotations

from pathlib import Path

from edison.core.composition.registries.documents import DocumentTemplateRegistry


def test_write_composed_filters_by_category(tmp_path: Path) -> None:
    core_dir = tmp_path / "core" / "documents"
    core_dir.mkdir(parents=True, exist_ok=True)

    # Two templates: client and task
    (core_dir / "clients-claude.md").write_text("# Client Claude\n", encoding="utf-8")
    (core_dir / "TASK.md").write_text("# Task Doc\n", encoding="utf-8")

    registry = DocumentTemplateRegistry(project_root=tmp_path)
    # Point core_dir to our temp core documents
    registry.core_dir = tmp_path / "core"
    written = registry.write_composed(category="clients")

    # Should only write the clients-claude doc
    assert len(written) == 1
    assert written[0].stem == "clients-claude"
