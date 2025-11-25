from __future__ import annotations

from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _load_yaml(rel_path: str) -> dict:
    path = PROJECT_ROOT / rel_path
    assert path.exists(), f"missing config file: {path}"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_validators_yaml_uses_nextjs_and_prisma():
    data = _load_yaml("core/config/validators.yaml")
    specialized = data["validation"]["roster"]["specialized"]

    ids = {v["id"] for v in specialized}
    blob = "\n".join(str(v) for v in specialized)

    assert "nextjs" in ids, "specialized validators must include nextjs"
    assert "prisma" in ids, "specialized validators must include prisma"
    assert "webapp" not in blob, "legacy webapp validator should be removed"
    assert "ormsuite" not in blob, "legacy prisma validator should be removed"


def test_defaults_yaml_updates_context_and_delegation():
    data = _load_yaml("core/defaults.yaml")
    specialized = data["validation"]["roster"]["specialized"]
    file_rules = data["delegation"]["filePatternRules"]

    ids = {v["id"] for v in specialized}
    blob = "\n".join(str(v) for v in specialized)

    assert "nextjs" in ids, "defaults must expose nextjs validator"
    assert "prisma" in ids, "defaults must expose prisma validator"
    assert "webapp" not in blob, "defaults should not contain webapp"
    assert "ormsuite" not in blob, "defaults should not contain ormsuite"

    assert "schema.prisma" in file_rules, "delegation should route prisma schema files"
    assert "prisma/migrations/**/*" in file_rules, "delegation should route prisma migrations"
    assert "schema.ormsuite" not in file_rules
    assert "ormsuite/migrations/**/*" not in file_rules


def test_delegation_yaml_routes_prisma_and_nextjs():
    data = _load_yaml("core/config/delegation.yaml")
    file_rules = data["delegation"]["filePatternRules"]

    assert "schema.prisma" in file_rules
    assert "prisma/migrations/**/*" in file_rules

    # App Router files should use nextjs-specific agent
    for key in ("**/layout.tsx", "**/page.tsx", "**/loading.tsx", "**/error.tsx"):
        assert file_rules[key]["subAgentType"].startswith("component-builder-nextjs")
