"""
Tests for the zenRole to project overlay documentation.

This suite enforces the presence and minimum content of
src/edison/core/docs/ZENROLE_OVERLAY_MAPPING.md.
"""
from __future__ import annotations

from pathlib import Path

import pytest


def _project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("Could not locate project root containing pyproject.toml")


@pytest.fixture(scope="module")
def doc_path() -> Path:
    return _project_root() / "src" / "edison" / "core" / "docs" / "ZENROLE_OVERLAY_MAPPING.md"


@pytest.fixture(scope="module")
def doc_text(doc_path: Path) -> str:
    assert doc_path.exists(), f"Documentation file missing: {doc_path}"
    return doc_path.read_text(encoding="utf-8").lower()


def test_document_exists(doc_path: Path) -> None:
    """Doc file should be present at the expected path."""
    assert doc_path.exists(), "ZENROLE_OVERLAY_MAPPING.md must exist under src/edison/core/docs/"


def test_explains_zenroles_concept(doc_text: str) -> None:
    """Doc should explicitly describe what zenRoles are."""
    assert "what are zenroles" in doc_text, "Document should include a 'What are zenRoles' section"
    assert "how they work" in doc_text or "permissions" in doc_text or "capabilities" in doc_text, (
        "Document should explain how zenRoles operate, not just list them"
    )


def test_explains_overlay_mechanism(doc_text: str) -> None:
    """Doc should explain project overlays and mapping behavior."""
    assert "project overlays" in doc_text, "Project overlay section should be present"
    assert "mapping" in doc_text and "overlay" in doc_text, "Mapping from zenRole to overlay must be described"
    assert ".edison" in doc_text, "Document should reference .edison/ overlay directory usage"


def test_includes_custom_role_guidance(doc_text: str) -> None:
    """Doc should provide instructions for defining custom zenRoles."""
    assert "create custom zenroles" in doc_text or "defining custom zenroles" in doc_text, (
        "Document should guide users on creating project-specific zenRoles"
    )
    assert "yaml" in doc_text, "Configuration should be YAML-driven, not hardcoded"


def test_includes_examples_without_wilson(doc_text: str) -> None:
    """Doc should show examples without hardcoded wilson references."""
    assert "examples" in doc_text, "Document should include example configurations"
    assert "wilson" not in doc_text, "Document must avoid hardcoded wilson-* zenRoles"

