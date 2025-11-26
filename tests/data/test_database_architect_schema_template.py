from __future__ import annotations

from pathlib import Path

import pytest

from edison.data import get_data_path


def _load_agent_content() -> str:
    agents_dir = get_data_path("agents")
    path = agents_dir / "database-architect-core.md"
    assert path.exists(), f"Missing agent file: {path}"
    return path.read_text(encoding="utf-8")


def test_schema_template_section_present() -> None:
    content = _load_agent_content()
    assert "## Prisma Schema Patterns" in content
    assert "### Complete Model Template" in content


def test_prisma_model_example_includes_relations_and_indexes() -> None:
    content = _load_agent_content()
    assert "model Lead" in content
    assert "@relation(fields: [ownerId], references: [id])" in content
    assert "@@index([status])" in content
    assert "@@index([ownerId])" in content
    assert "@@index([createdAt])" in content


def test_template_includes_enum_and_migration_workflow() -> None:
    content = _load_agent_content()
    assert "enum LeadStatus" in content
    assert "### Migration Workflow" in content
    assert "npx prisma migrate dev" in content
