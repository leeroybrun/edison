"""Unit tests for session layout detection helpers."""
from pathlib import Path

import pytest

from edison.core.session.core.layout import detect_layout, get_session_base_path


def test_detect_flat_when_parent_contains_session_id():
    session = {"id": "sess-test-1", "parent": "/tmp/project/.project/sessions/wip/sess-test-1"}
    assert detect_layout(session) == "flat"
    assert get_session_base_path(session) == Path("/tmp/project/.project/sessions/wip/sess-test-1").resolve()


def test_detect_nested_when_parent_is_state_dir():
    session = {"id": "sess-test-1", "parent": "/tmp/project/.project/sessions/wip"}
    assert detect_layout(session) == "nested"
    assert get_session_base_path(session) == Path("/tmp/project/.project/sessions/wip/sess-test-1").resolve()


def test_detect_uses_session_path_when_parent_missing():
    session = {"id": "sid-123"}
    session_path = Path("/var/tmp/.project/sessions/active/sid-123/session.json")
    assert detect_layout(session, session_path=session_path) == "flat"
    assert get_session_base_path(session, session_path=session_path) == session_path.parent.resolve()


def test_detect_handles_legacy_flat_json_path():
    session = {"id": "legacy-1"}
    session_path = Path("/var/tmp/.project/sessions/wip/legacy-1.json")
    assert detect_layout(session, session_path=session_path) == "nested"
    assert get_session_base_path(session, session_path=session_path) == Path("/var/tmp/.project/sessions/wip/legacy-1").resolve()

