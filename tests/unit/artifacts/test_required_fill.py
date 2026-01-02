from __future__ import annotations


def test_required_fill_returns_empty_when_no_markers_present() -> None:
    from edison.core.artifacts.required_fill import find_missing_required_sections

    content = (
        "---\n"
        "id: t-1\n"
        "title: Test\n"
        "---\n"
        "\n"
        "# Test\n"
        "\n"
        "Some body.\n"
    )

    assert find_missing_required_sections(content) == []


def test_required_fill_detects_placeholder_token_in_marked_section() -> None:
    from edison.core.artifacts.required_fill import find_missing_required_sections

    content = (
        "# Test\n"
        "\n"
        "<!-- REQUIRED FILL: AcceptanceCriteria -->\n"
        "## Acceptance Criteria\n"
        "\n"
        "- [ ] <<FILL: acceptance criterion>>\n"
        "\n"
        "## Notes\n"
        "ok\n"
    )

    assert find_missing_required_sections(content) == ["AcceptanceCriteria"]


def test_required_fill_treats_marked_section_as_filled_when_no_placeholder_and_nonempty() -> None:
    from edison.core.artifacts.required_fill import find_missing_required_sections

    content = (
        "# Test\n"
        "\n"
        "<!-- REQUIRED FILL: AcceptanceCriteria -->\n"
        "## Acceptance Criteria\n"
        "\n"
        "- [ ] Task is complete when validators pass.\n"
        "\n"
        "## Notes\n"
        "ok\n"
    )

    assert find_missing_required_sections(content) == []

