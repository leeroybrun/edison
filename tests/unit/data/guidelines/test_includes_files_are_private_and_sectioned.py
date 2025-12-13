from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
INCLUDES_DIR = ROOT / "src" / "edison" / "data" / "guidelines" / "includes"


def test_includes_guidelines_are_marked_private() -> None:
    """Include-only guidelines must clearly declare they are not directly readable."""
    files = sorted(INCLUDES_DIR.glob("*.md"))
    assert files, "Expected include-only guideline files under guidelines/includes/"

    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "include-section" in text.lower(), f"Expected include-section hint in {path.name}"
        assert "do not read directly" in text.lower(), f"Expected privacy warning in {path.name}"


def test_includes_guidelines_define_sections() -> None:
    """Include-only guidelines must be SECTIONed so roles can include specific parts."""
    files = sorted(INCLUDES_DIR.glob("*.md"))
    assert files, "Expected include-only guideline files under guidelines/includes/"

    for path in files:
        text = path.read_text(encoding="utf-8")
        # Markers are case-insensitive, but project standard is lowercase.
        assert "<!-- section:" in text, f"Expected at least one section marker in {path.name}"
        assert "<!-- /section:" in text, f"Expected at least one section end marker in {path.name}"


