from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
DATA_DIR = ROOT / "src" / "edison" / "data"


def _read(rel: str) -> str:
    return (DATA_DIR / rel).read_text(encoding="utf-8")


def _include_sections(text: str) -> list[str]:
    return re.findall(r"\{\{include-section:([^}]+)\}\}", text)


def test_agents_base_includes_only_agent_sections() -> None:
    text = _read("constitutions/agents-base.md")
    includes = _include_sections(text)
    assert includes, "Expected include-section directives in agents-base.md"
    # agents must not load validator/orchestrator-only execution sections
    assert not any("#validator-" in inc or "#orchestrator-" in inc for inc in includes)


def test_validators_base_includes_only_validator_sections() -> None:
    text = _read("constitutions/validators-base.md")
    includes = _include_sections(text)
    assert includes, "Expected include-section directives in validators-base.md"
    assert not any("#agent-" in inc or "#orchestrator-" in inc for inc in includes)


def test_orchestrators_base_includes_only_orchestrator_sections() -> None:
    text = _read("constitutions/orchestrators-base.md")
    includes = _include_sections(text)
    assert includes, "Expected include-section directives in orchestrators-base.md"
    assert not any("#agent-" in inc or "#validator-" in inc for inc in includes)


