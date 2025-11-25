from __future__ import annotations

from pathlib import Path

import yaml

CORE_ROOT = Path(__file__).resolve().parents[2]
CONFIG = CORE_ROOT / "config" / "validators.yaml"


def test_specialized_validators_are_nextjs_and_prisma_specific() -> None:
    """Specialized roster should use technology-specific ids and drop generic webapp/database."""
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    specialized = cfg["validation"]["roster"]["specialized"]
    ids = {v["id"] for v in specialized}

    assert "nextjs" in ids, "Expect Next.js validator id"
    assert "prisma" in ids, "Expect Prisma validator id"

    assert "webapp" not in ids, "Legacy webapp validator should be removed"
    assert "database" not in ids, "Generic database validator should be replaced with Prisma-specific one"

    nextjs = next(v for v in specialized if v["id"] == "nextjs")
    prisma = next(v for v in specialized if v["id"] == "prisma")

    assert any("route.ts" in p or "page.tsx" in p for p in nextjs["triggers"]), "Next.js validator should watch app router files"
    assert any("schema.prisma" in p for p in prisma["triggers"]), "Prisma validator should watch Prisma schema files"
