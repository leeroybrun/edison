from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
DATA_DIR = ROOT / "src" / "edison" / "data"


def _read(rel: str) -> str:
    return (DATA_DIR / rel).read_text(encoding="utf-8")


def _include_sections(text: str) -> list[str]:
    return re.findall(r"\{\{include-section:([^}]+)\}\}", text)


def test_agents_constitution_includes_only_agent_sections() -> None:
    """Agent constitution should not include validator/orchestrator-specific sections."""
    text = _read("constitutions/agents.md")
    includes = _include_sections(text)
    assert includes, "Expected include-section directives in agents.md"
    # agents must not load validator/orchestrator-only execution sections
    assert not any("#validator-" in inc or "#orchestrator-" in inc for inc in includes)


def test_validators_constitution_includes_only_validator_sections() -> None:
    """Validator constitution should not include agent/orchestrator-specific sections."""
    text = _read("constitutions/validators.md")
    includes = _include_sections(text)
    assert includes, "Expected include-section directives in validators.md"
    assert not any("#agent-" in inc or "#orchestrator-" in inc for inc in includes)


def test_orchestrator_constitution_includes_only_orchestrator_sections() -> None:
    """Orchestrator constitution should not include agent/validator-specific sections."""
    text = _read("constitutions/orchestrator.md")
    includes = _include_sections(text)
    assert includes, "Expected include-section directives in orchestrator.md"
    assert not any("#agent-" in inc or "#validator-" in inc for inc in includes)
