"""Verification test to ensure no legacy import patterns remain in the codebase.

This test ensures that:
1. No legacy import patterns exist in src/
2. All imports use canonical locations
3. No deprecated aliases are being used
"""
import re
from pathlib import Path
import pytest


# Project root
PROJECT_ROOT = Path(__file__).parent.parent


# Legacy import patterns that should NOT exist in src/
LEGACY_PATTERNS = [
    # QARecord/QARepository should be imported from edison.core.qa, not task
    (r"from edison\.core\.task\.models import.*QARecord", "QARecord should be imported from edison.core.qa.models"),
    (r"from edison\.core\.task\.repository import.*QARepository", "QARepository should be imported from edison.core.qa.repository"),

    # Session store module has been deleted - use repository/manager/graph instead
    (r"from edison\.core\.session\.store import", "edison.core.session.store has been deleted - use SessionRepository, manager, or graph"),
    (r"from edison\.core\.session import store", "edison.core.session.store has been deleted - use SessionRepository, manager, or graph"),

    # Legacy task modules that no longer exist
    (r"from edison\.core\.task\.io import", "edison.core.task.io has been deleted"),
    (r"from edison\.core\.task\.finder import", "edison.core.task.finder has been deleted"),
    (r"from edison\.core\.task\.context7 import", "edison.core.task.context7 has been moved to edison.core.qa.context7"),

    # Deprecated session ID functions (use validate_session_id instead)
    (r"\bsanitize_session_id\(", "Use validate_session_id instead of sanitize_session_id"),
    (r"\bnormalize_session_id\(", "Use validate_session_id instead of normalize_session_id"),

    # Evidence manager/helpers have been reorganized
    (r"from edison\.core\.qa\.evidence\.manager import", "edison.core.qa.evidence.manager has been reorganized"),
    (r"from edison\.core\.qa\.evidence\.helpers import", "edison.core.qa.evidence.helpers has been reorganized"),
]


def find_pattern_in_files(directory: Path, pattern: str, exclude_patterns=None) -> list[tuple[Path, int, str]]:
    """Find a regex pattern in all Python files under directory.

    Returns list of (file_path, line_number, line_content) tuples.
    """
    if exclude_patterns is None:
        exclude_patterns = []

    matches = []
    regex = re.compile(pattern)

    for py_file in directory.rglob("*.py"):
        # Skip excluded patterns
        if any(re.search(excl, str(py_file)) for excl in exclude_patterns):
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
            for line_num, line in enumerate(content.splitlines(), 1):
                if regex.search(line):
                    matches.append((py_file, line_num, line.strip()))
        except Exception:
            # Skip files that can't be read
            continue

    return matches


@pytest.mark.fast
def test_no_legacy_imports_in_src():
    """Ensure no legacy import patterns exist in src/."""
    src_dir = PROJECT_ROOT / "src"
    failures = []

    for pattern, reason in LEGACY_PATTERNS:
        matches = find_pattern_in_files(src_dir, pattern)

        if matches:
            failure_msg = f"\n❌ Found legacy pattern: {pattern}\n   Reason: {reason}\n   Matches:\n"
            for file_path, line_num, line in matches:
                rel_path = file_path.relative_to(PROJECT_ROOT)
                failure_msg += f"     {rel_path}:{line_num}: {line}\n"
            failures.append(failure_msg)

    if failures:
        pytest.fail(f"\n{'='*80}\nLegacy import patterns found in src/:\n{'='*80}{''.join(failures)}")


@pytest.mark.fast
def test_no_legacy_imports_in_tests():
    """Ensure test files use proper imports (excluding deliberate legacy pattern tests)."""
    tests_dir = PROJECT_ROOT / "tests"

    # These patterns should not appear in tests
    test_legacy_patterns = [
        (r"\bstore_sanitize_session_id\(", "Undefined function - import validate_session_id from edison.core.session.id"),
        (r"\bsession_store_sanitize_session_id\(", "Undefined function - use validate_session_id"),
        (r"\bstore_save_session\(", "Undefined function - import save_session from edison.core.session.graph"),
        (r"\bstore_load_session\(", "Undefined function - import get_session from edison.core.session.manager"),
        (r"\bstore_get_session_json_path\(", "Undefined function - use SessionRepository().get_session_json_path()"),
        (r"\bsession_store_SessionNotFoundError", "Undefined - import SessionNotFoundError from edison.core.exceptions"),
    ]

    # Files that are allowed to have legacy patterns (they test for them)
    exclude_patterns = [
        r"test_no_legacy_imports\.py$",  # This file!
        r"test_no_legacy_modules\.py$",  # Tests that verify legacy modules don't exist
    ]

    failures = []

    for pattern, reason in test_legacy_patterns:
        matches = find_pattern_in_files(tests_dir, pattern, exclude_patterns=exclude_patterns)

        if matches:
            failure_msg = f"\n❌ Found legacy pattern: {pattern}\n   Reason: {reason}\n   Files:\n"
            for file_path, line_num, line in matches:
                rel_path = file_path.relative_to(PROJECT_ROOT)
                failure_msg += f"     {rel_path}:{line_num}: {line}\n"
            failures.append(failure_msg)

    if failures:
        pytest.fail(f"\n{'='*80}\nLegacy patterns found in test files:\n{'='*80}{''.join(failures)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
