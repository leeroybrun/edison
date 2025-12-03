"""Test that state_machine.py uses CompositionFileWriter instead of direct write_text.

Following TDD principle: Write tests FIRST to verify state_machine uses the unified writer.
"""
import pytest
from pathlib import Path
from unittest.mock import patch
from edison.core.composition.output.state_machine import generate_state_machine_doc
from edison.core.composition.output.writer import CompositionFileWriter


def test_generate_state_machine_uses_composition_file_writer(tmp_path):
    """Test that generate_state_machine_doc uses CompositionFileWriter.write_text."""
    # Setup minimal Edison structure
    config_dir = tmp_path / ".edison" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Track all write_text calls
    original_write_text = CompositionFileWriter.write_text
    write_calls = []

    def track_write_text(self, path, content, encoding=None):
        write_calls.append((path, content, encoding))
        return original_write_text(self, path, content, encoding)

    with patch.object(CompositionFileWriter, 'write_text', track_write_text):
        # Generate state machine doc
        output_path = tmp_path / ".edison" / "_generated" / "STATE_MACHINE.md"
        result_path = generate_state_machine_doc(output_path, repo_root=tmp_path)

    # Verify that CompositionFileWriter.write_text was called
    assert len(write_calls) > 0, "CompositionFileWriter.write_text should be called by generate_state_machine_doc"

    # Verify the file exists
    assert result_path.exists(), "State machine doc should be created"
    content = result_path.read_text(encoding="utf-8")
    assert "# State Machine" in content, "State machine doc should have expected header"
