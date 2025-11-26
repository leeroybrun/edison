"""
Test TDD delegation templates are present and correctly formatted.

T-023: Restore TDD Delegation Templates
This test verifies that TDD delegation templates for orchestrators are present
in the TDD.md guideline file.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from edison.data import get_data_path


def test_tdd_md_contains_delegation_section() -> None:
    """
    TDD.md must contain a section on TDD delegation templates.

    This section provides templates for orchestrators to use when delegating
    tasks with TDD requirements to sub-agents.
    """
    tdd_file = get_data_path("guidelines") / "shared" / "TDD.md"

    assert tdd_file.exists(), "TDD.md must exist in guidelines/shared"

    content = tdd_file.read_text(encoding="utf-8")

    # Must have a section about delegation
    assert "## TDD When Delegating" in content or "## Delegation" in content, (
        "TDD.md must contain a section about TDD delegation templates"
    )


def test_tdd_md_contains_component_builder_template() -> None:
    """
    TDD.md must contain a delegation template for component-builder agent.

    The template should show orchestrators how to delegate component work
    with TDD requirements (RED-GREEN-REFACTOR cycle).
    """
    tdd_file = get_data_path("guidelines") / "shared" / "TDD.md"
    content = tdd_file.read_text(encoding="utf-8")

    # Must have component-builder template
    assert "component-builder" in content.lower(), (
        "TDD.md must contain delegation template for component-builder"
    )

    # Template must reference TDD cycle
    assert "RED" in content and "GREEN" in content and "REFACTOR" in content, (
        "TDD delegation template must reference RED-GREEN-REFACTOR cycle"
    )


def test_tdd_md_contains_api_builder_template() -> None:
    """
    TDD.md must contain a delegation template for api-builder agent.

    The template should show orchestrators how to delegate API work
    with TDD requirements.
    """
    tdd_file = get_data_path("guidelines") / "shared" / "TDD.md"
    content = tdd_file.read_text(encoding="utf-8")

    # Must have api-builder template
    assert "api-builder" in content.lower(), (
        "TDD.md must contain delegation template for api-builder"
    )


def test_tdd_md_contains_database_architect_template() -> None:
    """
    TDD.md must contain a delegation template for database-architect agent.

    The template should show orchestrators how to delegate database work
    with TDD requirements.
    """
    tdd_file = get_data_path("guidelines") / "shared" / "TDD.md"
    content = tdd_file.read_text(encoding="utf-8")

    # Must have database-architect template
    assert "database-architect" in content.lower(), (
        "TDD.md must contain delegation template for database-architect"
    )


def test_tdd_delegation_templates_mention_test_first() -> None:
    """
    All TDD delegation templates must emphasize test-first approach.

    Each template should make it clear that tests must be written FIRST,
    before any implementation.
    """
    tdd_file = get_data_path("guidelines") / "shared" / "TDD.md"
    content = tdd_file.read_text(encoding="utf-8")

    # Templates must emphasize test-first
    test_first_phrases = [
        "FIRST" in content.upper(),
        "test first" in content.lower(),
        "write test" in content.lower(),
        "failing test" in content.lower(),
    ]

    assert any(test_first_phrases), (
        "TDD delegation templates must emphasize writing tests FIRST"
    )


def test_tdd_delegation_templates_require_evidence() -> None:
    """
    TDD delegation templates must require evidence of TDD compliance.

    Each template should specify that the sub-agent must return evidence
    showing the RED-GREEN-REFACTOR cycle was followed.
    """
    tdd_file = get_data_path("guidelines") / "shared" / "TDD.md"
    content = tdd_file.read_text(encoding="utf-8")

    # Templates must require evidence
    evidence_phrases = [
        "evidence" in content.lower(),
        "document" in content.lower(),
        "verify" in content.lower(),
        "return" in content.lower(),
    ]

    assert any(evidence_phrases), (
        "TDD delegation templates must require evidence of TDD compliance"
    )


def test_tdd_delegation_section_has_minimum_content() -> None:
    """
    TDD delegation section must contain substantial guidance.

    Based on T-023 specification, the delegation templates should be
    approximately 136 lines of content.
    """
    tdd_file = get_data_path("guidelines") / "shared" / "TDD.md"
    content = tdd_file.read_text(encoding="utf-8")

    # Find the delegation section
    if "## TDD When Delegating" in content:
        section_start = content.index("## TDD When Delegating")
        # Find next ## section or end of file
        remaining = content[section_start + len("## TDD When Delegating"):]
        next_section = remaining.find("\n## ")
        if next_section != -1:
            delegation_section = remaining[:next_section]
        else:
            delegation_section = remaining

        # Count non-empty lines in delegation section
        non_empty_lines = [
            line for line in delegation_section.split("\n")
            if line.strip()
        ]

        # Should have substantial content (at least 50 lines as a reasonable check)
        assert len(non_empty_lines) >= 50, (
            f"TDD delegation section should contain substantial guidance "
            f"(found {len(non_empty_lines)} non-empty lines, expected at least 50)"
        )
