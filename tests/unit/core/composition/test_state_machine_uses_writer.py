"""Tests that state_machine generates files with the expected content."""

from pathlib import Path

from edison.core.composition.generators.state_machine import StateMachineGenerator


def test_generate_state_machine_creates_file(tmp_path: Path) -> None:
    """Test that StateMachineGenerator creates the state machine file."""
    # Setup minimal Edison structure
    config_dir = tmp_path / ".edison" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Generate state machine doc
    output_dir = tmp_path / ".edison" / "_generated"
    generator = StateMachineGenerator(project_root=tmp_path)
    result_path = generator.write(output_dir)

    # Verify the file exists
    assert result_path.exists(), "State machine doc should be created"


def test_generate_state_machine_has_expected_content(tmp_path: Path) -> None:
    """Test that generated state machine doc has expected header."""
    config_dir = tmp_path / ".edison" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    output_dir = tmp_path / ".edison" / "_generated"
    generator = StateMachineGenerator(project_root=tmp_path)
    result_path = generator.write(output_dir)

    content = result_path.read_text(encoding="utf-8")
    assert "# State Machine" in content, "State machine doc should have expected header"


def test_generate_state_machine_content_is_utf8(tmp_path: Path) -> None:
    """Test that generated file is properly UTF-8 encoded."""
    config_dir = tmp_path / ".edison" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    output_dir = tmp_path / ".edison" / "_generated"
    generator = StateMachineGenerator(project_root=tmp_path)
    result_path = generator.write(output_dir)

    # Reading with explicit UTF-8 encoding should not raise
    content = result_path.read_text(encoding="utf-8")
    assert len(content) > 0
