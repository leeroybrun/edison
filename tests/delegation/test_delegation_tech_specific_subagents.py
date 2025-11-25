from __future__ import annotations

from pathlib import Path

import pytest
import yaml

CORE_ROOT = Path(__file__).resolve().parents[2]
CONFIG = CORE_ROOT / "config" / "delegation.yaml"


@pytest.mark.skip(reason="Deprecated: Old config/delegation.yaml removed, functionality moved to project .agents/config/delegation.yml")
def test_nextjs_and_prisma_file_patterns_use_tech_specific_agents() -> None:
    """TSX/JSX should delegate to the Next.js component builder; Prisma files to the Prisma DB architect."""
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    rules = cfg["delegation"]["filePatternRules"]

    assert rules["*.tsx"]["subAgentType"] == "component-builder-nextjs"
    assert rules["*.jsx"]["subAgentType"] == "component-builder-nextjs"

    assert "schema.prisma" in rules, "Prisma schema pattern must be present"
    assert rules["schema.prisma"]["subAgentType"] == "database-architect-prisma"

    assert "prisma/migrations/**/*" in rules, "Prisma migration glob must be present"
    assert rules["prisma/migrations/**/*"]["subAgentType"] == "database-architect-prisma"

    # Guard against lingering generic/legacy identifiers
    legacy_agents = {rules["*.tsx"]["subAgentType"], rules["*.jsx"]["subAgentType"], rules["schema.prisma"]["subAgentType"]}
    assert "component-builder" not in legacy_agents
    assert "database-architect" not in legacy_agents
