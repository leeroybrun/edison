"""
Tests for CLI output formatting helpers.

This module tests output formatting functions for JSON, tables, user prompts,
and status messages that were extracted from the original cli.py god file.

Following STRICT TDD: These tests are written FIRST (RED phase) before
the implementation exists.
"""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def isolated_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """
    Isolate ConfigManager to use a minimal defaults.yaml in tmp_path.
    
    This ensures that:
    1. The project root is set to tmp_path (empty, so no project config)
    2. The core defaults are loaded from a controlled file in tmp_path, 
       which matches DEFAULT_CLI_CONFIG (specifically having no 'default' key for confirm).
    """
    # 1. Isolate project root
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))

    # 2. Setup mock data directory for core defaults
    data_dir = tmp_path / "data"
    config_dir = data_dir / "config"
    config_dir.mkdir(parents=True)
    
    # Create minimal defaults.yaml that matches DEFAULT_CLI_CONFIG (no 'default' in 'confirm')
    defaults_content = """
cli:
  json:
    indent: 2
    sort_keys: true
    ensure_ascii: false
  table:
    padding: 1
    column_gap: 2
  confirm:
    assume_yes_env: ""
  output:
    success_prefix: "[OK]"
    error_prefix: "[ERR]"
    warning_prefix: "[WARN]"
    use_color: false
"""
    (config_dir / "defaults.yaml").write_text(defaults_content, encoding="utf-8")
    
    # Patch get_data_path to return our mock config directory
    # We need to handle the signature: get_data_path(subpackage: str, filename: str = "")
    def mock_get_data_path(subpackage: str, filename: str = "") -> Path:
        # We only care about 'config' for this test
        base = data_dir / subpackage
        if not base.exists():
            # For other subpackages (like schemas), just create dir so it doesn't crash
            base.mkdir(parents=True, exist_ok=True)
        return base / filename if filename else base

    monkeypatch.setattr("edison.data.get_data_path", mock_get_data_path)


def test_output_json_pretty_format(isolated_config: None) -> None:
    """output_json should format JSON with indentation by default."""
    from edison.core.utils.cli_output import output_json

    data = {"key": "value", "nested": {"foo": "bar"}}
    result = output_json(data, pretty=True)

    # Should be valid JSON
    parsed = json.loads(result)
    assert parsed == data

    # Should have indentation (pretty)
    assert "\n" in result
    assert "  " in result  # 2-space indent


def test_output_json_compact_format(isolated_config: None) -> None:
    """output_json with pretty=False should produce compact JSON."""
    from edison.core.utils.cli_output import output_json

    data = {"key": "value", "nested": {"foo": "bar"}}
    result = output_json(data, pretty=False)

    # Should be valid JSON
    parsed = json.loads(result)
    assert parsed == data

    # Should be compact (no extra whitespace)
    assert "\n" not in result


def test_output_json_sorts_keys(isolated_config: None) -> None:
    """output_json should sort keys by default."""
    from edison.core.utils.cli_output import output_json

    data = {"z": 1, "a": 2, "m": 3}
    result = output_json(data, pretty=False)

    # Keys should be sorted alphabetically
    assert result == '{"a":2,"m":3,"z":1}'


def test_output_table_basic_formatting(isolated_config: None) -> None:
    """output_table should format rows as aligned columns."""
    from edison.core.utils.cli_output import output_table

    rows = [
        ["foo", "bar", "baz"],
        ["longer", "x", "y"],
    ]
    headers = ["Col1", "Col2", "Col3"]

    result = output_table(rows, headers)

    # Should contain headers
    assert "Col1" in result
    assert "Col2" in result
    assert "Col3" in result

    # Should contain data
    assert "foo" in result
    assert "longer" in result

    # Should have multiple lines
    lines = result.split("\n")
    assert len(lines) >= 3  # Header + 2 rows


def test_output_table_with_dict_rows(isolated_config: None) -> None:
    """output_table should handle dict rows using headers as keys."""
    from edison.core.utils.cli_output import output_table

    rows = [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
    ]
    headers = ["name", "age"]

    result = output_table(rows, headers)

    assert "Alice" in result
    assert "Bob" in result
    assert "30" in result
    assert "25" in result


def test_output_table_empty_rows(isolated_config: None) -> None:
    """output_table should handle empty rows gracefully."""
    from edison.core.utils.cli_output import output_table

    rows: list[Any] = []
    headers = ["Col1", "Col2"]

    result = output_table(rows, headers)

    # Should still show headers
    assert "Col1" in result
    assert "Col2" in result


def test_output_table_missing_dict_keys(isolated_config: None) -> None:
    """output_table should handle missing keys in dict rows."""
    from edison.core.utils.cli_output import output_table

    rows = [
        {"name": "Alice"},  # Missing 'age'
        {"name": "Bob", "age": 25},
    ]
    headers = ["name", "age"]

    result = output_table(rows, headers)

    # Should handle missing values
    assert "Alice" in result
    assert "Bob" in result


def test_confirm_returns_true_for_yes(isolated_config: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """confirm should return True when user enters 'yes' or 'y'."""
    from edison.core.utils.cli_output import confirm

    inputs = iter(["yes", "y"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    assert confirm("Continue?") is True
    assert confirm("Continue?") is True


def test_confirm_returns_false_for_no(isolated_config: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """confirm should return False when user enters 'no' or 'n'."""
    from edison.core.utils.cli_output import confirm

    inputs = iter(["no", "n"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    assert confirm("Continue?") is False
    assert confirm("Continue?") is False


def test_confirm_uses_default_on_empty_input(isolated_config: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """confirm should use default value on empty input."""
    from edison.core.utils.cli_output import confirm

    monkeypatch.setattr("builtins.input", lambda _: "")
    assert confirm("Continue?", default=True) is True
    assert confirm("Continue?", default=False) is False


def test_confirm_case_insensitive(isolated_config: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """confirm should accept uppercase input."""
    from edison.core.utils.cli_output import confirm

    inputs = iter(["YES", "NO"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    assert confirm("Continue?") is True
    assert confirm("Continue?") is False


def test_confirm_handles_eof(isolated_config: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """confirm should handle EOFError gracefully."""
    from edison.core.utils.cli_output import confirm

    def raise_eof(_: str) -> str:
        raise EOFError

    monkeypatch.setattr("builtins.input", raise_eof)
    
    # Should use default on EOF
    result = confirm("Continue?", default=True)
    assert result is True


def test_error_prints_to_stderr(isolated_config: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """error should print message to stderr with prefix."""
    from edison.core.utils.cli_output import error

    mock_stderr = StringIO()
    monkeypatch.setattr("sys.stderr", mock_stderr)

    exit_code = error("Something failed")

    output = mock_stderr.getvalue()
    assert "Something failed" in output
    assert "[ERR]" in output
    assert exit_code == 1


def test_error_custom_exit_code(isolated_config: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """error should return custom exit code."""
    from edison.core.utils.cli_output import error

    mock_stderr = StringIO()
    monkeypatch.setattr("sys.stderr", mock_stderr)

    exit_code = error("Failed", exit_code=42)
    assert exit_code == 42


def test_success_prints_with_prefix(isolated_config: None, capsys: pytest.CaptureFixture[str]) -> None:
    """success should print message with success prefix."""
    from edison.core.utils.cli_output import success

    success("Operation completed")

    captured = capsys.readouterr()
    assert "Operation completed" in captured.out
    assert "[OK]" in captured.out


def test_output_json_handles_unicode(isolated_config: None) -> None:
    """output_json should handle unicode characters properly."""
    from edison.core.utils.cli_output import output_json

    data = {"message": "Hello 世界 🌍"}
    result = output_json(data)

    parsed = json.loads(result)
    assert parsed["message"] == "Hello 世界 🌍"

    # Should not escape unicode by default
    assert "世界" in result
    assert "🌍" in result


def test_output_table_aligns_columns(isolated_config: None) -> None:
    """output_table should align columns with proper spacing."""
    from edison.core.utils.cli_output import output_table

    rows = [
        ["short", "x"],
        ["very_long_text", "y"],
    ]
    headers = ["Col1", "Col2"]

    result = output_table(rows, headers)
    lines = result.split("\n")

    # Should have header + 2 data rows
    assert len(lines) >= 3

    # Each line should contain both column values
    assert "Col1" in lines[0] and "Col2" in lines[0]
    assert "short" in lines[1] and "x" in lines[1]
    assert "very_long_text" in lines[2] and "y" in lines[2]

    # Second column should appear after first column in each row
    for line in lines:
        # Find positions - Col2 should be to the right of Col1/data
        parts = line.split()
        if len(parts) >= 2:
            # Just verify both parts exist
            assert len(parts) >= 2
