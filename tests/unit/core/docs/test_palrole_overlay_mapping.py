"""
Tests for the Pal role conventions documentation.

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
    """Doc should describe role naming conventions and how Pal discovers prompts."""
    assert "roles" in doc_text
    assert "agent-" in doc_text and "validator-" in doc_text, "Doc should mention agent-/validator- role conventions"
    assert "cli_clients" in doc_text or "clink" in doc_text, "Doc should mention clink + cli_clients discovery"


def test_explains_overlay_mechanism(doc_text: str) -> None:
    """Doc should explain the project-local prompt/config layout."""
    assert ".pal" in doc_text, "Doc should reference the .pal directory layout"
    assert "systemprompts" in doc_text, "Doc should mention system prompt file locations"


def test_includes_custom_role_guidance(doc_text: str) -> None:
    """Doc should explain how to add custom roles/prompts."""
    assert "custom" in doc_text, "Doc should guide users on adding custom roles"
    assert "yaml" in doc_text or "json" in doc_text, "Doc should mention YAML/JSON-driven configuration"


def test_includes_examples_without_wilson(doc_text: str) -> None:
    """Doc should show examples without hardcoded wilson references."""
    assert "examples" in doc_text, "Document should include example configurations"
    assert "wilson" not in doc_text, "Document must avoid hardcoded wilson-* palRoles"
