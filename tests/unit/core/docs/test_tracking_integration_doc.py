"""Tests for the tracking integration documentation.

This suite enforces the presence and baseline content of
src/edison/data/docs/TRACKING_INTEGRATION.md.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers.paths import get_repo_root


@pytest.fixture(scope="module")
def doc_path() -> Path:
    return get_repo_root() / "src" / "edison" / "data" / "docs" / "TRACKING_INTEGRATION.md"


@pytest.fixture(scope="module")
def doc_text(doc_path: Path) -> str:
    assert doc_path.exists(), f"Documentation file missing: {doc_path}"
    return doc_path.read_text(encoding="utf-8").lower()


def test_document_exists(doc_path: Path) -> None:
    """Doc file should be present at the expected path."""
    assert doc_path.exists(), "TRACKING_INTEGRATION.md must exist under src/edison/data/docs/"


def test_lists_supported_systems(doc_text: str) -> None:
    """Doc should list supported trackers such as Linear and GitHub Issues."""
    assert "supported tracking systems" in doc_text, "Document should include a 'Supported tracking systems' section"
    assert "linear" in doc_text, "Linear support must be documented"
    assert "github issues" in doc_text or "github" in doc_text, "GitHub Issues support must be documented"


def test_configuration_section(doc_text: str) -> None:
    """Doc should explain how to configure tracking integration via YAML."""
    assert "configure" in doc_text or "configuration" in doc_text, "Configuration steps must be described"
    assert "yaml" in doc_text, "Configuration must be YAML-driven, not hardcoded"
    assert ".edison" in doc_text, "Doc should reference .edison config location"


def test_status_sync_section(doc_text: str) -> None:
    """Doc should explain how task status syncs with external trackers."""
    assert "status sync" in doc_text or "sync status" in doc_text, "Status sync behavior must be described"
    assert "external tracker" in doc_text or "tracking system" in doc_text, "External tracker interaction must be noted"


def test_custom_extension_guidance(doc_text: str) -> None:
    """Doc should guide extending Edison for custom tracking systems."""
    assert "custom tracking" in doc_text or "custom tracking system" in doc_text, "Custom integration guidance must be present"
    assert "extend" in doc_text or "extension" in doc_text, "Document should describe how to extend the integration"


def test_troubleshooting_section(doc_text: str) -> None:
    """Doc should include a troubleshooting section with common issues."""
    assert "troubleshooting" in doc_text, "Troubleshooting section must exist"
    assert "common issues" in doc_text or "common problems" in doc_text, "Troubleshooting should mention common issues"
