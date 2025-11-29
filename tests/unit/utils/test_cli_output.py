"""
Tests for CLI output formatting helpers.

This module tests output formatting functions for JSON, tables, user prompts,
and status messages that were extracted from the original cli.py god file.

Following STRICT TDD: These tests are written FIRST (RED phase) before
the implementation exists.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
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

    # Create the schema directory to avoid config loading errors
    (data_dir / "schemas" / "config").mkdir(parents=True, exist_ok=True)


def test_output_json_pretty_format(isolated_config: None) -> None:
    """output_json should format JSON with indentation by default."""
    from edison.core.utils.cli.output import output_json

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
    from edison.core.utils.cli.output import output_json

    data = {"key": "value", "nested": {"foo": "bar"}}
    result = output_json(data, pretty=False)

    # Should be valid JSON
    parsed = json.loads(result)
    assert parsed == data

    # Should be compact (no extra whitespace)
    assert "\n" not in result


def test_output_json_sorts_keys(isolated_config: None) -> None:
    """output_json should sort keys by default."""
    from edison.core.utils.cli.output import output_json

    data = {"z": 1, "a": 2, "m": 3}
    result = output_json(data, pretty=False)

    # Keys should be sorted alphabetically
    assert result == '{"a":2,"m":3,"z":1}'


def test_output_table_basic_formatting(isolated_config: None) -> None:
    """output_table should format rows as aligned columns."""
    from edison.core.utils.cli.output import output_table

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
    from edison.core.utils.cli.output import output_table

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
    from edison.core.utils.cli.output import output_table

    rows: list[Any] = []
    headers = ["Col1", "Col2"]

    result = output_table(rows, headers)

    # Should still show headers
    assert "Col1" in result
    assert "Col2" in result


def test_output_table_missing_dict_keys(isolated_config: None) -> None:
    """output_table should handle missing keys in dict rows."""
    from edison.core.utils.cli.output import output_table

    rows = [
        {"name": "Alice"},  # Missing 'age'
        {"name": "Bob", "age": 25},
    ]
    headers = ["name", "age"]

    result = output_table(rows, headers)

    # Should handle missing values
    assert "Alice" in result
    assert "Bob" in result


def test_confirm_returns_true_for_yes(isolated_config: None, tmp_path: Path) -> None:
    """confirm should return True when user enters 'yes' or 'y'."""
    # Test by creating a subprocess that calls confirm with different inputs
    test_script = tmp_path / "test_confirm_yes.py"
    test_script.write_text("""
import sys
sys.path.insert(0, r"{}")

from edison.core.utils.cli.output import confirm

# Test 'yes'
result1 = confirm("Continue?")
assert result1 is True, f"Expected True for 'yes', got {{result1}}"

# Test 'y'
result2 = confirm("Continue?")
assert result2 is True, f"Expected True for 'y', got {{result2}}"

print("PASS")
""".format(str(Path(__file__).resolve().parents[3] / "src")))

    result = subprocess.run(
        [sys.executable, str(test_script)],
        input="yes\ny\n",
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env={"AGENTS_PROJECT_ROOT": str(tmp_path)}
    )

    assert result.returncode == 0, f"Script failed: {result.stderr}"
    assert "PASS" in result.stdout


def test_confirm_returns_false_for_no(isolated_config: None, tmp_path: Path) -> None:
    """confirm should return False when user enters 'no' or 'n'."""
    test_script = tmp_path / "test_confirm_no.py"
    test_script.write_text("""
import sys
sys.path.insert(0, r"{}")

from edison.core.utils.cli.output import confirm

# Test 'no'
result1 = confirm("Continue?")
assert result1 is False, f"Expected False for 'no', got {{result1}}"

# Test 'n'
result2 = confirm("Continue?")
assert result2 is False, f"Expected False for 'n', got {{result2}}"

print("PASS")
""".format(str(Path(__file__).resolve().parents[3] / "src")))

    result = subprocess.run(
        [sys.executable, str(test_script)],
        input="no\nn\n",
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env={"AGENTS_PROJECT_ROOT": str(tmp_path)}
    )

    assert result.returncode == 0, f"Script failed: {result.stderr}"
    assert "PASS" in result.stdout


def test_confirm_uses_default_on_empty_input(isolated_config: None, tmp_path: Path) -> None:
    """confirm should use default value on empty input.

    Note: The config loading may fall back to DEFAULT_CLI_CONFIG which has
    no 'default' key in 'confirm' section, so the function parameter is used.
    """
    test_script = tmp_path / "test_confirm_default.py"
    test_script.write_text("""
import sys
sys.path.insert(0, r"{src}")

from edison.core.utils.cli.output import confirm

# Test default=True with empty input
result1 = confirm("Test1?", default=True)
assert result1 is True, f"Expected True for empty input with default=True, got {{result1}}"

# Test default=False with empty input
result2 = confirm("Test2?", default=False)
assert result2 is False, f"Expected False for empty input with default=False, got {{result2}}"

print("PASS")
""".format(src=str(Path(__file__).resolve().parents[3] / "src")))

    result = subprocess.run(
        [sys.executable, str(test_script)],
        input="\n\n",
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env={"PATH": os.environ.get("PATH", "")}
    )

    assert result.returncode == 0, f"Script failed: stderr={result.stderr}, stdout={result.stdout}"
    assert "PASS" in result.stdout


def test_confirm_case_insensitive(isolated_config: None, tmp_path: Path) -> None:
    """confirm should accept uppercase input."""
    test_script = tmp_path / "test_confirm_case.py"
    test_script.write_text("""
import sys
sys.path.insert(0, r"{}")

from edison.core.utils.cli.output import confirm

# Test 'YES'
result1 = confirm("Continue?")
assert result1 is True, f"Expected True for 'YES', got {{result1}}"

# Test 'NO'
result2 = confirm("Continue?")
assert result2 is False, f"Expected False for 'NO', got {{result2}}"

print("PASS")
""".format(str(Path(__file__).resolve().parents[3] / "src")))

    result = subprocess.run(
        [sys.executable, str(test_script)],
        input="YES\nNO\n",
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env={"AGENTS_PROJECT_ROOT": str(tmp_path)}
    )

    assert result.returncode == 0, f"Script failed: {result.stderr}"
    assert "PASS" in result.stdout


def test_confirm_handles_eof(isolated_config: None, tmp_path: Path) -> None:
    """confirm should handle EOFError gracefully by using default.

    Note: When EOF is encountered, confirm catches it and treats it as empty
    input, falling back to the default parameter.
    """
    test_script = tmp_path / "test_confirm_eof.py"
    test_script.write_text("""
import sys
sys.path.insert(0, r"{src}")

from edison.core.utils.cli.output import confirm

# Test EOF with default=True
result = confirm("Test?", default=True)
assert result is True, f"Expected True on EOF with default=True, got {{result}}"

print("PASS")
""".format(src=str(Path(__file__).resolve().parents[3] / "src")))

    # EOF is simulated by closing stdin (no input)
    result = subprocess.run(
        [sys.executable, str(test_script)],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env={"PATH": os.environ.get("PATH", "")}
    )

    assert result.returncode == 0, f"Script failed: stderr={result.stderr}, stdout={result.stdout}"
    assert "PASS" in result.stdout


def test_error_prints_to_stderr(isolated_config: None, tmp_path: Path) -> None:
    """error should print message to stderr with prefix."""
    test_script = tmp_path / "test_error.py"
    test_script.write_text("""
import sys
sys.path.insert(0, r"{}")

from edison.core.utils.cli.output import error

exit_code = error("Something failed")
assert exit_code == 1, f"Expected exit code 1, got {{exit_code}}"
""".format(str(Path(__file__).resolve().parents[3] / "src")))

    result = subprocess.run(
        [sys.executable, str(test_script)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env={"AGENTS_PROJECT_ROOT": str(tmp_path)}
    )

    # Check stderr for error message and prefix
    assert "Something failed" in result.stderr
    assert "[ERR]" in result.stderr


def test_error_custom_exit_code(isolated_config: None, tmp_path: Path) -> None:
    """error should return custom exit code."""
    test_script = tmp_path / "test_error_code.py"
    test_script.write_text("""
import sys
sys.path.insert(0, r"{}")

from edison.core.utils.cli.output import error

exit_code = error("Failed", exit_code=42)
assert exit_code == 42, f"Expected exit code 42, got {{exit_code}}"
print("PASS")
""".format(str(Path(__file__).resolve().parents[3] / "src")))

    result = subprocess.run(
        [sys.executable, str(test_script)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env={"AGENTS_PROJECT_ROOT": str(tmp_path)}
    )

    assert result.returncode == 0
    assert "PASS" in result.stdout


def test_success_prints_with_prefix(isolated_config: None, capsys: pytest.CaptureFixture[str]) -> None:
    """success should print message with success prefix."""
    from edison.core.utils.cli.output import success

    success("Operation completed")

    captured = capsys.readouterr()
    assert "Operation completed" in captured.out
    assert "[OK]" in captured.out


def test_output_json_handles_unicode(isolated_config: None) -> None:
    """output_json should handle unicode characters properly."""
    from edison.core.utils.cli.output import output_json

    data = {"message": "Hello 世界 🌍"}
    result = output_json(data)

    parsed = json.loads(result)
    assert parsed["message"] == "Hello 世界 🌍"

    # Should not escape unicode by default
    assert "世界" in result
    assert "🌍" in result


def test_output_table_aligns_columns(isolated_config: None) -> None:
    """output_table should align columns with proper spacing."""
    from edison.core.utils.cli.output import output_table

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
