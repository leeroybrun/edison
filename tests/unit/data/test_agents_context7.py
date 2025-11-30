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

    assert "mcp__context7__resolve-library-id({" in content
    assert 'libraryName: "next.js"' in content
    assert "react, tailwindcss, prisma, zod, motion" in content

    assert "mcp__context7__get-library-docs({" in content
    assert 'context7CompatibleLibraryID: "/vercel/next.js"' in content
    # Topics can be in JSON array format or as comma-separated values
    assert '"route handlers"' in content or "route handlers" in content

    assert "config/context7.yaml" in content

    # Version info can be in list format or inline
    assert "Next.js 16" in content
    assert "React 19" in content
    assert "Tailwind CSS 4" in content
    assert "Prisma 6" in content
