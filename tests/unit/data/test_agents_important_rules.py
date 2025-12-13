from pathlib import Path
import re

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
def test_agents_have_important_rules(agent_path: Path) -> None:
    content = agent_path.read_text(encoding="utf-8")

    assert "## IMPORTANT RULES" in content

    match = re.search(r"## IMPORTANT RULES\n+(.+?)(?:\n## |\Z)", content, flags=re.S)
    assert match, "IMPORTANT RULES section body missing"

    section = match.group(1)

    # Allow canonical include-section directive to supply the shared rules.
    canonical = "{{include-section:guidelines/includes/IMPORTANT_RULES.md#agents-common}}"
    if canonical in section:
        include_path = ROOT / "src/edison/data/guidelines/includes/IMPORTANT_RULES.md"
        inc = include_path.read_text(encoding="utf-8")
        # Extract the specific SECTION block content
        m = re.search(
            r"<!--\s*section:\s*agents-common\s*-->\n(.+?)\n<!--\s*/section:\s*agents-common\s*-->",
            inc,
            flags=re.S | re.I,
        )
        assert m, "Canonical IMPORTANT_RULES section 'agents-common' missing"
        section = section.replace(canonical, m.group(1).strip())

    rule_lines = [line for line in section.splitlines() if re.match(r"^\s*[-*]\s+\S", line)]
    assert len(rule_lines) >= 3, "IMPORTANT RULES must include at least 3 bullet rules"

    assert re.search(r"anti[- ]?patterns?", section, flags=re.I), "IMPORTANT RULES must mention anti-patterns"
