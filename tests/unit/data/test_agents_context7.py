from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]

AGENT_PATHS = [
    ROOT / "src/edison/data/agents/api-builder.md",
    ROOT / "src/edison/data/agents/code-reviewer.md",
    ROOT / "src/edison/data/agents/component-builder.md",
    ROOT / "src/edison/data/agents/database-architect.md",
    ROOT / "src/edison/data/agents/feature-implementer.md",
    ROOT / "src/edison/data/agents/test-engineer.md",
]


@pytest.mark.parametrize("agent_path", AGENT_PATHS)
def test_agents_include_context7_examples(agent_path: Path) -> None:
    content = agent_path.read_text(encoding="utf-8")

    assert "## Context7 Knowledge Refresh (MANDATORY)" in content

    # Agents should load the canonical snippet via include-section (single source of truth).
    assert "{{include-section:guidelines/includes/CONTEXT7.md#agent}}" in content
