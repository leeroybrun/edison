from pathlib import Path


SESSION_PATH = Path("src/edison/core/start/START_VALIDATE_SESSION.md")


def read_session_text() -> str:
    return SESSION_PATH.read_text(encoding="utf-8")


def test_session_file_exists():
    assert SESSION_PATH.exists(), "START_VALIDATE_SESSION.md must be created"


def test_includes_pre_validation_checklist():
    content = read_session_text()
    assert "Pre-Validation Checklist" in content
    assert "Read validator constitution" in content
    assert "Load validator roster" in content


def test_includes_validation_protocol_with_waves():
    content = read_session_text()
    assert "Validation Protocol" in content
    assert "Wave 1: Global validators" in content
    assert "Wave 2: Critical validators" in content
    assert "Wave 3: Specialized validators" in content


def test_references_validator_constitution():
    content = read_session_text()
    assert "constitutions/VALIDATORS.md" in content
