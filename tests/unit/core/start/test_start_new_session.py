from pathlib import Path


SESSION_PATH = Path("src/edison/data/start/START_NEW_SESSION.md")


def read_session_text() -> str:
    return SESSION_PATH.read_text(encoding="utf-8")


def test_session_file_exists():
    assert SESSION_PATH.exists(), "START_NEW_SESSION.md must be created"


def test_has_minimum_orchestrator_start_contract():
    content = read_session_text()
    # The START templates are intentionally short; they must still provide a minimal contract.
    assert "You are starting a fresh work session as an **ORCHESTRATOR**." in content
    assert "## Immediate Actions" in content
    assert "Load Constitution" in content
    assert "edison session status" in content
    assert "edison task status" in content


def test_mentions_creating_a_session_record():
    content = read_session_text()
    assert "edison session create" in content


def test_mentions_state_machine_reference():
    content = read_session_text()
    assert ".edison/_generated/STATE_MACHINE.md" in content


def test_references_orchestrator_constitution():
    content = read_session_text()
    assert "constitutions/ORCHESTRATOR.md" in content
