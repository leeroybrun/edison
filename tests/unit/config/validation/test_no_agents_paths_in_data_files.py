"""
Test that ALL files in src/edison/data directory use .edison/ paths, not .agents/ paths.

This is part of T-015 migration task to replace hardcoded .agents/ references with .edison/.

Following STRICT TDD:
- RED: This test should FAIL initially (102 occurrences in 37 files)
- GREEN: After replacing all .agents/ with .edison/, test should PASS
- REFACTOR: Ensure DRY principles and clean implementation
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from edison.data import get_data_path
from tests.helpers.paths import get_repo_root


def get_all_data_files() -> list[Path]:
    """
    Recursively get all text files in src/edison/data directory.

    Returns:
        List of Path objects for all .md, .yml, .yaml, .json files
    """
    # Get the base data directory
    data_root = get_repo_root() / "src" / "edison" / "data"

    # Collect all relevant file types
    extensions = {".md", ".yml", ".yaml", ".json"}
    all_files = []

    for ext in extensions:
        all_files.extend(data_root.rglob(f"*{ext}"))

    return sorted(all_files)


def check_file_for_agents_path(file_path: Path) -> list[tuple[int, str]]:
    """
    Check a file for .agents/ path references.

    Args:
        file_path: Path to the file to check

    Returns:
        List of (line_number, line_content) tuples for lines containing .agents/
    """
    # Pattern to match .agents/ in any context
    pattern = re.compile(r'\.agents/')

    violations = []
    try:
        content = file_path.read_text(encoding="utf-8")
        for line_num, line in enumerate(content.splitlines(), start=1):
            if pattern.search(line):
                violations.append((line_num, line.strip()))
    except Exception as e:
        pytest.fail(f"Failed to read {file_path}: {e}")

    return violations


def test_no_agents_paths_in_data_directory():
    """
    CRITICAL: Verify that NO files in src/edison/data contain .agents/ path references.

    All paths must use .edison/ or be properly configurable through templates.
    This is part of the Edison migration (T-015) to eliminate hardcoded legacy paths.

    This test follows STRICT TDD:
    - RED: Should FAIL initially (102 occurrences across 37 files)
    - GREEN: Will PASS after replacing all .agents/ with .edison/
    - REFACTOR: Ensures clean, maintainable code
    """
    all_files = get_all_data_files()

    # Ensure we're actually testing something
    assert len(all_files) > 0, "No data files found to test!"

    # Track all violations
    all_violations = {}

    for file_path in all_files:
        violations = check_file_for_agents_path(file_path)
        if violations:
            # Store relative path for cleaner output
            rel_path = file_path.relative_to(get_repo_root())
            all_violations[str(rel_path)] = violations

    # Build detailed error message if violations found
    if all_violations:
        error_lines = [
            "\n" + "=" * 80,
            "FOUND .agents/ PATH REFERENCES IN DATA FILES",
            "=" * 80,
            f"\nTotal files with violations: {len(all_violations)}",
            f"Total files checked: {len(all_files)}",
            "\nViolations by file:",
            "-" * 80,
        ]

        total_occurrences = 0
        for file_path, violations in sorted(all_violations.items()):
            error_lines.append(f"\n{file_path} ({len(violations)} occurrences):")
            for line_num, line_content in violations:
                error_lines.append(f"  Line {line_num}: {line_content}")
                total_occurrences += 1

        error_lines.extend([
            "\n" + "-" * 80,
            f"TOTAL: {total_occurrences} occurrences of .agents/ found",
            "=" * 80,
            "\nAll .agents/ references must be replaced with .edison/ paths.",
            "This is required for T-015 Edison migration task.",
            "=" * 80,
        ])

        pytest.fail("\n".join(error_lines))


def test_data_files_exist():
    """Sanity check that we have data files to test."""
    all_files = get_all_data_files()
    assert len(all_files) > 30, f"Expected at least 30 data files, found {len(all_files)}"


def test_file_checker_works():
    """Verify that our file checker can detect .agents/ patterns."""
    # Create a temporary test to verify our pattern works
    test_cases = [
        ("path: .agents/config.yml", True),
        ("path: .edison/config.yml", False),
        ('".agents/rules"', True),
        ("reference .agents/ here", True),
        ("no legacy path here", False),
    ]

    pattern = re.compile(r'\.agents/')
    for test_line, should_match in test_cases:
        matches = pattern.search(test_line) is not None
        assert matches == should_match, f"Pattern check failed for: {test_line}"
