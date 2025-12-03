"""Test that includes.py uses CompositionFileWriter instead of direct write_text.

Following TDD principle: Write tests FIRST to verify includes uses the unified writer.
"""
import pytest
from pathlib import Path
from unittest.mock import patch
from edison.core.composition.includes import _write_cache
from edison.core.composition.output.writer import CompositionFileWriter


def test_write_cache_uses_composition_file_writer(tmp_path, monkeypatch):
    """Test that _write_cache uses CompositionFileWriter.write_text."""
    # Setup test environment
    monkeypatch.setattr("edison.core.composition.includes._repo_root", lambda: tmp_path)

    config_dir = tmp_path / ".edison" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Track all write_text calls
    original_write_text = CompositionFileWriter.write_text
    write_calls = []

    def track_write_text(self, path, content, encoding=None):
        write_calls.append((path, content, encoding))
        return original_write_text(self, path, content, encoding)

    with patch.object(CompositionFileWriter, 'write_text', track_write_text):
        # Call _write_cache
        validator_id = "test-validator"
        text = "Test validator content"
        deps = []
        content_hash = "abc123"

        result_path = _write_cache(validator_id, text, deps, content_hash)

    # Verify that CompositionFileWriter.write_text was called
    assert len(write_calls) > 0, "CompositionFileWriter.write_text should be called by _write_cache"

    # Verify the file exists and has correct content
    assert result_path.exists(), "Output file should be created"
    assert result_path.read_text(encoding="utf-8") == text, "File should contain expected text"
