from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "src" / "edison" / "data"
PRISMA_OVERLAY_PATH = DATA_DIR / "packs" / "prisma" / "agents" / "overlays" / "database-architect.md"


_INCLUDE_SECTION_RE = re.compile(r"\{\{include-section:([^#}]+)#([^}]+)\}\}")


def _load_prisma_overlay() -> str:
    assert PRISMA_OVERLAY_PATH.exists(), f"Missing Prisma overlay: {PRISMA_OVERLAY_PATH}"
    return PRISMA_OVERLAY_PATH.read_text(encoding="utf-8")


def test_schema_template_section_present() -> None:
    content = _load_prisma_overlay()
    # Overlay should wire in canonical include-only sections, not inline a huge template.
    include_sections = _INCLUDE_SECTION_RE.findall(content)
    assert include_sections, "Expected include-section directives in prisma database-architect overlay"

    expected = {
        ("packs/prisma/guidelines/includes/prisma/schema-design.md", "patterns"),
        ("packs/prisma/guidelines/includes/prisma/relationships.md", "patterns"),
        ("packs/prisma/guidelines/includes/prisma/migrations.md", "patterns"),
        ("packs/prisma/guidelines/includes/prisma/query-optimization.md", "patterns"),
        ("packs/prisma/guidelines/includes/prisma/TESTING.md", "patterns"),
    }
    found = {(p, s) for (p, s) in include_sections}
    assert expected.issubset(found)


def test_prisma_model_example_includes_relations_and_indexes() -> None:
    schema_path = DATA_DIR / "packs" / "prisma" / "guidelines" / "includes" / "prisma" / "schema-design.md"
    text = schema_path.read_text(encoding="utf-8")
    assert "model Record" in text
    assert "@relation(fields: [userId], references: [id]" in text
    assert "enum RecordStatus" in text
    assert "@@index([userId])" in text
    assert "@@index([status])" in text


def test_template_includes_enum_and_migration_workflow() -> None:
    migrations_path = DATA_DIR / "packs" / "prisma" / "guidelines" / "includes" / "prisma" / "migrations.md"
    text = migrations_path.read_text(encoding="utf-8")
    assert "<!-- section: patterns -->" in text
    assert "nullable → required" in text or "nullable \u2192 required" in text
