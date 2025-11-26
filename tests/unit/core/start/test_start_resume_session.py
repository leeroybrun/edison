from pathlib import Path


SESSION_PATH = Path("src/edison/core/start/START_RESUME_SESSION.md")


def read_session_text() -> str:
    return SESSION_PATH.read_text(encoding="utf-8")


def test_session_file_exists():
    assert SESSION_PATH.exists(), "START_RESUME_SESSION.md must be created"


def test_includes_session_id_placeholder():
    content = read_session_text()
    assert "{{session_id}}" in content
    assert "edison session resume {{session_id}}" in content


def test_includes_recovery_checklist():
    content = read_session_text()
    required_items = [
        "Re-read your constitution",
        "Check session state",
        "Review in-progress tasks",
        "Check for blocked tasks",
    ]
    for item in required_items:
        assert item in content


def test_references_constitution():
    content = read_session_text()
    assert "constitutions/ORCHESTRATORS.md" in content
