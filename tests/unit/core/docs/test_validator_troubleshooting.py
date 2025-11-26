"""Tests for the validator troubleshooting guide documentation.

This suite enforces the presence and minimum content of
src/edison/data/docs/VALIDATOR_TROUBLESHOOTING.md.
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
    return _project_root() / "src" / "edison" / "data" / "docs" / "VALIDATOR_TROUBLESHOOTING.md"


@pytest.fixture(scope="module")
def doc_text(doc_path: Path) -> str:
    assert doc_path.exists(), f"Documentation file missing: {doc_path}"
    return doc_path.read_text(encoding="utf-8").lower()


def test_document_exists(doc_path: Path) -> None:
    """Doc file should be present at the expected path."""
    assert doc_path.exists(), "VALIDATOR_TROUBLESHOOTING.md must exist under src/edison/data/docs/"


def test_common_errors_section(doc_text: str) -> None:
    """Doc should enumerate common validator errors with solutions."""
    assert "common validator errors" in doc_text, "Document should list common validator errors"
    assert "solution" in doc_text, "Common errors section must describe solutions, not just symptoms"


def test_debugging_guidance(doc_text: str) -> None:
    """Doc should explain how to debug validator failures."""
    assert "debug validator failures" in doc_text or "debugging validator failures" in doc_text, (
        "Document should include a debugging workflow for validator failures"
    )
    assert "logs" in doc_text or "trace" in doc_text, "Debugging section should mention reviewing logs or traces"


def test_manual_run_instructions(doc_text: str) -> None:
    """Doc should explain how to run validators manually."""
    assert "run validators manually" in doc_text or "manual validator run" in doc_text, (
        "Document should explain how to invoke validators outside automation"
    )
    assert "command" in doc_text, "Manual run instructions should include concrete commands"


def test_configuration_checks(doc_text: str) -> None:
    """Doc should instruct how to check validator configuration."""
    assert "check validator configuration" in doc_text or "validate configuration" in doc_text, (
        "Document should show how to inspect validator YAML configuration"
    )
    assert "yaml" in doc_text, "Configuration guidance must point to YAML sources, not hardcoded values"


def test_custom_validator_guidance(doc_text: str) -> None:
    """Doc should describe adding custom validators."""
    assert "add custom validators" in doc_text or "custom validator" in doc_text, (
        "Document should explain how to extend the validator set"
    )
    assert "register" in doc_text or "configure" in doc_text, "Custom validator steps should include registration/configuration"


def test_faq_section(doc_text: str) -> None:
    """Doc should include an FAQ section for quick answers."""
    assert "faq" in doc_text, "Document should contain an FAQ section"
    assert "?" in doc_text, "FAQ section should contain questions users might ask"
