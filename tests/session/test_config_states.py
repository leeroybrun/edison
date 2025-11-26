import pytest
from pathlib import Path
from edison.core.config.domains import SessionConfig


def test_state_config_loading():
    """SessionConfig exposes rich state machine as simple helpers."""
    config = SessionConfig()

    # Verify Task States (rich format uses dict; helper returns list of keys)
    task_states = config.get_states("task")
    assert "todo" in task_states
    assert "done" in task_states

    # Verify Task Transitions collapse to allowed targets list
    transitions = config.get_transitions("task")
    assert "wip" in transitions["todo"]

    # Verify QA States
    assert "waiting" in config.get_states("qa")

    # Verify QA Transitions
    qa_transitions = config.get_transitions("qa")
    assert "todo" in qa_transitions["waiting"]


def test_invalid_transition():
    """Invalid transitions are rejected in the rich format."""
    config = SessionConfig()
    transitions = config.get_transitions("task")
    assert "todo" not in transitions["done"]


def test_session_config_loading():
    """Session-level defaults remain accessible."""
    config = SessionConfig()

    assert config.get_session_root_path() == ".project/sessions"
    assert config.get_max_id_length() == 64
    assert config.get_id_regex() == r"^[a-zA-Z0-9_\-\.]+$"

    states = config.get_session_states()
    # The config maps "active" to "wip" directory name, so verify the mapping is present
    assert "active" in states
    assert states["active"] == "wip"
