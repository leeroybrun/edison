"""Security validator guideline must document pack-aware security context."""
from __future__ import annotations

from pathlib import Path


GUIDELINE_PATH = Path("src/edison/data/validators/critical/security.md")


def test_security_doc_is_pack_aware() -> None:
    """Security guideline should explain how pack rules integrate with core rules."""

    content = GUIDELINE_PATH.read_text(encoding="utf-8").lower()

    required_phrases = (
        "## pack context",  # Section anchor
        "pack-specific security rules",  # Explicit pack context
        "pack rule registries",  # Reference to pack registries (t-032)
        ".edison/packs/<pack>/rules/registry.yml",  # Registry path hint
        "rulesregistry",  # Loader used by validators
        "merge core + pack security rules",  # Guidance on merging
    )

    for phrase in required_phrases:
        assert phrase in content, f"Missing pack-aware guidance: {phrase}"
