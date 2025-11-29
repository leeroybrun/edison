from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from tests.helpers.paths import get_repo_root

CORE_ROOT = get_repo_root()
CONFIG = CORE_ROOT / "src" / "edison" / "data" / "config" / "validators.yaml"


@pytest.mark.skipif(
    not CONFIG.exists(),
    reason="Config file not found"
)
def test_specialized_validators_are_nextjs_and_prisma_specific() -> None:
    """Specialized roster should have technology-specific validators like nextjs and database/prisma."""
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    specialized = cfg.get("validation", {}).get("roster", {}).get("specialized", [])

    if not specialized:
        pytest.skip("No specialized validators defined yet")

    ids = {v["id"] for v in specialized}

    # Verify key technology-specific validators exist
    assert "nextjs" in ids, "Expect Next.js validator id"
    # Accept either 'prisma' or 'database' for Prisma/DB validation
    assert "prisma" in ids or "database" in ids, "Expect Prisma or database validator id"

    assert "webapp" not in ids, "Legacy webapp validator should be removed"

    nextjs = next(v for v in specialized if v["id"] == "nextjs")
    assert any("route.ts" in p or "page.tsx" in p for p in nextjs["triggers"]), "Next.js validator should watch app router files"

    # Check either prisma or database validator for schema triggers
    db_validator = next((v for v in specialized if v["id"] in ("prisma", "database")), None)
    if db_validator:
        assert any("schema" in p.lower() or "prisma" in p.lower() for p in db_validator["triggers"]), (
            "Database/Prisma validator should watch schema files"
        )
