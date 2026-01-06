from __future__ import annotations

import pytest


@pytest.mark.task
def test_migration_adds_relationships_and_removes_legacy_keys() -> None:
    from edison.core.task.relationships.migration import migrate_task_markdown_relationships
    from edison.core.utils.text import parse_frontmatter

    original = """---
id: 013-migrate
title: Migrate
parent_id: 013-parent
child_ids:
  - 013-child
depends_on: [013-dep-a, 013-dep-b]
blocks_tasks: []
related_tasks: [013-related]
bundle_root: 013-bundle
---

# Migrate

Hello
"""

    migrated = migrate_task_markdown_relationships(original)
    fm = parse_frontmatter(migrated).frontmatter

    edges = {(e["type"], e["target"]) for e in (fm.get("relationships") or [])}
    assert ("parent", "013-parent") in edges
    assert ("child", "013-child") in edges
    assert ("depends_on", "013-dep-a") in edges
    assert ("depends_on", "013-dep-b") in edges
    assert ("related", "013-related") in edges
    assert ("bundle_root", "013-bundle") in edges

    assert fm.get("parent_id") is None
    assert fm.get("child_ids") is None
    assert fm.get("depends_on") is None
    assert fm.get("blocks_tasks") is None
    assert fm.get("related") is None
    assert fm.get("related_tasks") is None
    assert fm.get("bundle_root") is None


@pytest.mark.task
def test_migration_is_idempotent() -> None:
    from edison.core.task.relationships.migration import migrate_task_markdown_relationships

    original = """---
id: 013-migrate
title: Migrate
parent_id: 013-parent
---

# Migrate
"""

    once = migrate_task_markdown_relationships(original)
    twice = migrate_task_markdown_relationships(once)
    assert twice == once


@pytest.mark.task
def test_migration_removes_legacy_keys_when_relationships_already_present() -> None:
    from edison.core.task.relationships.migration import migrate_task_markdown_relationships
    from edison.core.utils.text import parse_frontmatter

    original = """---
id: 013-migrate
title: Migrate
relationships:
  - type: parent
    target: 013-parent
parent_id: SHOULD-BE-REMOVED
---

# Migrate
"""

    migrated = migrate_task_markdown_relationships(original)
    fm = parse_frontmatter(migrated).frontmatter
    edges = {(e["type"], e["target"]) for e in (fm.get("relationships") or [])}
    assert ("parent", "013-parent") in edges
    assert fm.get("parent_id") is None


@pytest.mark.task
def test_migration_noops_when_no_frontmatter() -> None:
    from edison.core.task.relationships.migration import migrate_task_markdown_relationships

    original = "# No frontmatter\n"
    assert migrate_task_markdown_relationships(original) == original
