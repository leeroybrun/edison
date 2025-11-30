"""
Test that isolated_project_env fixture creates START.SESSION.md.

RED phase: This test should fail initially.
"""
from pathlib import Path
import pytest


def test_start_session_file_exists(isolated_project_env):
    """Verify START.SESSION.md is created in isolated test environment."""
    start_session = isolated_project_env / ".edison" / "core" / "guides" / "START.SESSION.md"

    assert start_session.exists(), (
        "START.SESSION.md must exist in .edison/core/guides/ for autostart tests"
    )

    # Verify it has content
    content = start_session.read_text(encoding="utf-8")
    assert len(content) > 0, "START.SESSION.md must not be empty"
    assert "Session" in content, "START.SESSION.md must contain session-related content"


def test_start_session_content_is_valid(isolated_project_env):
    """Verify START.SESSION.md has expected sections."""
    start_session = isolated_project_env / ".edison" / "core" / "guides" / "START.SESSION.md"

    if not start_session.exists():
        pytest.skip("START.SESSION.md not found")

    content = start_session.read_text(encoding="utf-8")

    # Should have basic session start instructions
    expected_keywords = [
        "session",
        "start",
        "task",
    ]

    for keyword in expected_keywords:
        assert keyword.lower() in content.lower(), (
            f"START.SESSION.md must contain '{keyword}'"
        )
