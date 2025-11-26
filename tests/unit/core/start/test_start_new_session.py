from pathlib import Path


SESSION_PATH = Path("src/edison/core/start/START_NEW_SESSION.md")


def read_session_text() -> str:
    return SESSION_PATH.read_text(encoding="utf-8")


def test_session_file_exists():
    assert SESSION_PATH.exists(), "START_NEW_SESSION.md must be created"


def test_includes_pre_session_checklist():
    content = read_session_text()
    assert "Pre-Session Checklist" in content
    assert "Read your constitution" in content
    assert "Load available agents" in content
    assert "Load available validators" in content
    assert "Confirm the human's request explicitly" in content


def test_includes_session_initialization_command():
    content = read_session_text()
    assert "Session Initialization" in content
    assert "edison session start" in content
    assert "Create a new session ID" in content
    assert "Initialize the session directory" in content
    assert "Set up git worktree" in content


def test_includes_intake_protocol_steps():
    content = read_session_text()
    assert "Intake Protocol" in content
    for phrase in (
        "Confirm Request",
        "Check Stale Work",
        "Shared QA Rule",
        "Reclaim Stale Tasks",
        "Select Work",
    ):
        assert phrase in content


def test_references_orchestrator_constitution():
    content = read_session_text()
    assert "constitutions/ORCHESTRATORS.md" in content
