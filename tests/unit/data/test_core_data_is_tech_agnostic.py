from __future__ import annotations

import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "src" / "edison" / "data"
PACKS_DIR = DATA_DIR / "packs"


_BANNED_TECH_TOKENS = (
    # Frameworks / stacks extracted from prior projects (must not live in core)
    r"next\.js",
    r"\bnextjs\b",
    r"\breact\b",
    r"\btailwind\b",
    r"\bprisma\b",
    r"\bfastify\b",
    r"\bpnpm\b",
    r"\bvitest\b",
    r"\bjest\b",
    r"\bzod\b",
    r"\bmotion\b",
    # Language/tooling specifics (should come from packs)
    r"\bpytest\b",
    r"\btypescript\b",
    r"\bjavascript\b",
    r"\bnode\.?js\b",
    r"\bnpm\b",
    r"\byarn\b",
    # Stack file extensions that indicate tech-specific examples
    r"\.tsx\b",
    r"\.ts\b",
    r"\.jsx\b",
    r"\.js\b",
    # Known project remnants
    r"\bwilson\b",
)


def _iter_core_markdown_files() -> list[Path]:
    """Return all core markdown files excluding packs."""
    files: list[Path] = []
    for path in DATA_DIR.rglob("*.md"):
        if PACKS_DIR in path.parents:
            continue
        files.append(path)
    return sorted(files)


@pytest.mark.parametrize("path", _iter_core_markdown_files())
def test_core_data_markdown_is_technology_agnostic(path: Path) -> None:
    """
    Guardrail (PROMPT_DEVELOPMENT.md):
    - Core (non-pack) prompt/guideline/constitution markdown must be technology-agnostic.
    - Technology-specific guidance belongs in packs (src/edison/data/packs/*).
    """
    text = path.read_text(encoding="utf-8")

    # Allow generic pack placeholders like "<pack>" / "{pack}" and ".edison/packs/<pack>/..."
    # This test targets *literal* stack mentions that break portability.
    combined = re.compile("|".join(_BANNED_TECH_TOKENS), flags=re.IGNORECASE)
    match = combined.search(text)
    assert not match, (
        f"Technology/project-specific token '{match.group(0)}' found in core markdown: "
        f"{path.relative_to(ROOT)}"
    )



