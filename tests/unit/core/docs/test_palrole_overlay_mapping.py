"""
Tests for the palRole to project overlay documentation.

This suite enforces the presence and minimum content of
src/edison/data/docs/PALROLE_OVERLAY_MAPPING.md.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers.paths import get_repo_root


@pytest.fixture(scope="module")
def doc_path() -> Path:
    return get_repo_root() / "src" / "edison" / "data" / "docs" / "PALROLE_OVERLAY_MAPPING.md"


@pytest.fixture(scope="module")
def doc_text(doc_path: Path) -> str:
    assert doc_path.exists(), f"Documentation file missing: {doc_path}"
    return doc_path.read_text(encoding="utf-8").lower()


def test_document_exists(doc_path: Path) -> None:
    """Doc file should be present at the expected path."""
    assert doc_path.exists(), "PALROLE_OVERLAY_MAPPING.md must exist under src/edison/data/docs/"


def test_explains_palroles_concept(doc_text: str) -> None:
    """Doc should explicitly describe what palRoles are."""
    assert "what are palroles" in doc_text, "Document should include a 'What are palRoles' section"
    assert "how they work" in doc_text or "permissions" in doc_text or "capabilities" in doc_text, (
        "Document should explain how palRoles operate, not just list them"
    )


def test_explains_overlay_mechanism(doc_text: str) -> None:
    """Doc should explain project overlays and mapping behavior."""
    assert "project overlays" in doc_text, "Project overlay section should be present"
    assert "mapping" in doc_text and "overlay" in doc_text, "Mapping from palRole to overlay must be described"
    assert ".edison" in doc_text, "Document should reference .edison/ overlay directory usage"


def test_includes_custom_role_guidance(doc_text: str) -> None:
    """Doc should provide instructions for defining custom palRoles."""
    assert "create custom palroles" in doc_text or "defining custom palroles" in doc_text, (
        "Document should guide users on creating project-specific palRoles"
    )
    assert "yaml" in doc_text, "Configuration should be YAML-driven, not hardcoded"


def test_includes_examples_without_wilson(doc_text: str) -> None:
    """Doc should show examples without hardcoded wilson references."""
    assert "examples" in doc_text, "Document should include example configurations"
    assert "wilson" not in doc_text, "Document must avoid hardcoded wilson-* palRoles"
