from __future__ import annotations

import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "src" / "edison" / "data"
PACKS_DIR = DATA_DIR / "packs"


# Core (non-pack) text assets must remain technology-agnostic.
# Tech-specific guidance belongs in packs/*.
_BANNED_TECH_TOKENS = (
    # Frameworks / stacks
    r"next\.js",
    r"\bnextjs\b",
    r"\breact\b",
    r"\btailwind\b",
    r"\bprisma\b",
    r"\bfastify\b",
    r"\bvitest\b",
    r"\bjest\b",
    r"\bzod\b",
    r"\bmotion\b",
    # Package managers / tooling
    r"\bpnpm\b",
    r"\bnpm\b",
    r"\byarn\b",
    r"\bnode\.?js\b",
    r"\btypescript\b",
    r"\bjavascript\b",
    r"\bpytest\b",
    r"\bprettier\b",
    r"\beslint\b",
    r"\btsc\b",
    # File extensions that indicate stack-specific examples
    r"\.tsx\b",
    r"\.ts\b",
    r"\.jsx\b",
    r"\.js\b",
    # Known project remnants
    r"\bwilson\b",
)


def _iter_core_text_files() -> list[Path]:
    """Return non-pack text assets likely to embed prompt/config instructions."""
    exts = {".md", ".mdc", ".yaml", ".yml", ".template"}
    files: list[Path] = []
    for path in DATA_DIR.rglob("*"):
        if path.is_dir():
            continue
        if PACKS_DIR in path.parents:
            continue
        if path.suffix.lower() not in exts:
            continue
        files.append(path)
    return sorted(files)


@pytest.mark.parametrize("path", _iter_core_text_files())
def test_core_nonpack_text_is_technology_agnostic(path: Path) -> None:
    """
    Guardrail (PROMPT_DEVELOPMENT.md):
    - Core prompt/config/templates must be technology-agnostic.
    - Technology-specific guidance belongs in packs (src/edison/data/packs/*).
    """
    text = path.read_text(encoding="utf-8")

    combined = re.compile("|".join(_BANNED_TECH_TOKENS), flags=re.IGNORECASE)
    match = combined.search(text)
    assert not match, (
        f"Technology/project-specific token '{match.group(0)}' found in core non-pack text: "
        f"{path.relative_to(ROOT)}"
    )

