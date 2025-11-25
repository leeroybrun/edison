from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[5]
core_path = REPO_ROOT / ".edison" / "core"
from edison.core.composition import CompositionEngine 
def test_database_validator_includes_pack_and_overlay() -> None:
    """Database validator should surface pack context and project overlay."""

    engine = CompositionEngine()
    result = engine.compose_validators(validator="database", enforce_dry=False)["database"]
    text = result.text

    # Order must be CORE -> PACKS -> PROJECT
    core_idx = text.index("# Core Edison Principles")
    pack_idx = text.index("# Tech-Stack Context (Packs)")
    overlay_idx = text.index("# Project-Specific Rules")
    assert core_idx < pack_idx < overlay_idx

    # Pack layer must be populated with Prisma guidance
    pack_section = text.split("# Tech-Stack Context (Packs)", 1)[1].split(
        "# Project-Specific Rules", 1
    )[0]
    assert pack_section.strip(), "Pack layer should not be empty"
    assert "Prisma Validation Context" in pack_section

    # Project overlay must be rendered (no missing overlay marker)
    overlay_section = text.split("# Project-Specific Rules", 1)[1]
    assert overlay_section.strip()
    assert "Lead Model Baseline" in overlay_section
    assert "Missing overlay" not in overlay_section
