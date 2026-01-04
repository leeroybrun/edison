from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.task
def test_task_repository_decodes_legacy_fields_into_canonical_relationships_and_writes_canonical(
    isolated_project_env: Path,
) -> None:
    root = isolated_project_env

    task_id = "010-legacy"
    p = root / ".project" / "tasks" / "todo" / f"{task_id}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        """---
id: 010-legacy
title: Legacy
parent_id: 010-parent
child_ids: [010-child]
depends_on: [010-dep]
blocks_tasks: [010-blocked]
related: [010-related]
---

# Legacy
""",
        encoding="utf-8",
    )

    from edison.core.task.repository import TaskRepository

    repo = TaskRepository(project_root=root)
    task = repo.get(task_id)
    assert task is not None

    edges = {(e["type"], e["target"]) for e in (task.relationships or [])}
    assert ("parent", "010-parent") in edges
    assert ("child", "010-child") in edges
    assert ("depends_on", "010-dep") in edges
    assert ("blocks", "010-blocked") in edges
    assert ("related", "010-related") in edges

    # Saving should write canonical `relationships:` and preserve legacy fields
    # for back-compat / human readability.
    repo.save(task)
    content = p.read_text(encoding="utf-8")
    from edison.core.utils.text import parse_frontmatter

    fm = parse_frontmatter(content).frontmatter
    assert isinstance(fm.get("relationships"), list)
    assert fm.get("parent_id") == "010-parent"
    assert fm.get("child_ids") == ["010-child"]
    assert fm.get("depends_on") == ["010-dep"]
    assert fm.get("blocks_tasks") == ["010-blocked"]
    assert fm.get("related") == ["010-related"]
