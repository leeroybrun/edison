"""Tests for START_RALPH_LOOP start prompt.

This prompt enables Ralph Loop (hard continuation) mode for a session.
"""

from pathlib import Path

from edison.core.utils.paths import PathResolver

SESSION_PATH = PathResolver.resolve_project_root() / "src/edison/data/start/START_RALPH_LOOP.md"


def read_session_text() -> str:
    return SESSION_PATH.read_text(encoding="utf-8")


def test_session_file_exists():
    assert SESSION_PATH.exists(), "START_RALPH_LOOP.md must be created"


def test_explains_ralph_loop_purpose():
    """The prompt must explain what Ralph Loop (hard continuation) is and when to use it."""
    content = read_session_text()
    # Must explain the concept
    assert "Ralph Loop" in content or "hard continuation" in content
    # Must explain it's opt-in
    assert "opt-in" in content.lower() or "optional" in content.lower()


def test_includes_enablement_command():
    """The prompt must show how to enable hard continuation mode."""
    content = read_session_text()
    # Must reference the Edison-native command
    assert "edison session continuation set" in content
    assert "--mode hard" in content


def test_references_session_next():
    """The prompt must reference the session next command for the loop driver."""
    content = read_session_text()
    assert "edison session next" in content


def test_is_model_agnostic():
    """The prompt must not mention client-specific details like OpenCode."""
    content = read_session_text()
    # Should not mention OpenCode-specific details
    assert "OpenCode" not in content
    assert "toast" not in content.lower()


def test_does_not_mention_promise_markers():
    """The prompt must not mention transcript promise markers (Edison-native approach)."""
    content = read_session_text()
    assert "<promise>" not in content.lower()
    assert "</promise>" not in content.lower()


def test_is_short_and_focused():
    """The prompt must be concise, not a 'kitchen sink'."""
    content = read_session_text()
    # Should be reasonably short (under 100 lines)
    lines = content.strip().split("\n")
    assert len(lines) < 100, f"Prompt is too long: {len(lines)} lines"


def test_includes_session_id_placeholder_or_reference():
    """The prompt must reference session identification (either placeholder or instruction)."""
    content = read_session_text()
    # Either uses a placeholder or explains how to get session id
    assert "{{session_id}}" in content or "session id" in content.lower() or "<sid>" in content or "<session-id>" in content


def test_includes_state_machine_reference():
    """The prompt must reference the session state machine include."""
    content = read_session_text()
    # Must include the state machine reference (via include directive)
    assert "SESSION_STATE_MACHINE.md" in content or "STATE_MACHINE.md" in content
