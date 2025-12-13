from __future__ import annotations

from pathlib import Path

import pytest

PRISMA_OVERLAY_PATH = Path("src/edison/data/packs/prisma/agents/overlays/database-architect.md")


def _load_prisma_overlay() -> str:
    assert PRISMA_OVERLAY_PATH.exists(), f"Missing Prisma overlay: {PRISMA_OVERLAY_PATH}"
    return PRISMA_OVERLAY_PATH.read_text(encoding="utf-8")


def test_schema_template_section_present() -> None:
    content = _load_prisma_overlay()
    assert "## Prisma Schema Patterns" in content
    assert "## Migration Workflow" in content


def test_prisma_model_example_includes_relations_and_indexes() -> None:
    content = _load_prisma_overlay()
    assert "model Record" in content
    assert "@relation(fields: [userId], references: [id])" in content
    assert "@@index([status])" in content
    assert "@@index([userId])" in content
    assert "@@index([createdAt])" in content


def test_template_includes_enum_and_migration_workflow() -> None:
    content = _load_prisma_overlay()
    assert "## Migration Workflow" in content
    assert "<prisma-migrate-command>" in content
