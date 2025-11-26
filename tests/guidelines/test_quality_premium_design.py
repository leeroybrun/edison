from __future__ import annotations

from edison.data import get_data_path


def _read_quality_guide() -> str:
    """Read the bundled QUALITY guideline content."""

    return get_data_path("guidelines/shared", "QUALITY.md").read_text(encoding="utf-8")


def test_quality_guideline_includes_premium_design_section() -> None:
    """QUALITY guideline must document premium design standards."""

    content = _read_quality_guide()

    assert "## Premium Design Standards" in content


def test_quality_guideline_lists_required_premium_subsections() -> None:
    """All premium design subsections must be present for coherence."""

    content = _read_quality_guide()

    required_headings = [
        "### Design Token System",
        "### Micro-interactions",
        "### Loading & Empty States",
        "### Responsive Design",
        "### Accessibility (WCAG AA)",
        "### Dark Mode Support",
    ]

    missing = [heading for heading in required_headings if heading not in content]

    assert not missing, f"Missing premium design subsections: {missing}"


def test_quality_guideline_details_premium_design_requirements() -> None:
    """Premium design section must include the concrete requirements and examples."""

    content = _read_quality_guide()

    expectations = [
        "--spacing-1: 0.25rem",
        "--color-primary: theme('colors.blue.600')",
        "focus:ring-2 focus:ring-primary-light",
        "active:scale-95",
        "Skeleton count={5}",
        "sm:grid-cols-2",
        "prefers-reduced-motion",
        "dark:bg-gray-900",
    ]

    missing = [snippet for snippet in expectations if snippet not in content]

    assert not missing, f"Premium design requirements missing snippets: {missing}"


def test_quality_guideline_has_balanced_code_fences() -> None:
    """Markdown fences should be balanced to keep the guide valid."""

    content = _read_quality_guide()

    fence_count = content.count("```")

    assert fence_count > 0, "QUALITY guideline should use fenced code blocks"
    assert fence_count % 2 == 0, "Unbalanced fenced code blocks in QUALITY guideline"
