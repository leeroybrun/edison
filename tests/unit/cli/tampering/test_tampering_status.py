"""TDD tests for `edison tampering status` command.

These tests verify that the tampering status command:
1. Shows current tampering protection status
2. Returns correct JSON output when --json flag is set
3. Returns correct text output in default mode
4. Shows mode and protected directory information
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest
import yaml


def test_tampering_status_shows_disabled_by_default(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """`edison tampering status` should show disabled when no config exists."""
    from edison.cli.tampering.status import main, register_args

    (tmp_path / ".edison" / "config").mkdir(parents=True, exist_ok=True)

    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args(["--repo-root", str(tmp_path)])

    exit_code = main(args)

    assert exit_code == 0, f"Command failed with exit code {exit_code}"

    captured = capsys.readouterr()
    # Text output should mention status
    assert "disabled" in captured.out.lower() or "false" in captured.out.lower()


def test_tampering_status_shows_enabled(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """`edison tampering status` should show enabled when config is set."""
    from edison.cli.tampering.status import main, register_args

    config_dir = tmp_path / ".edison" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "tampering.yaml").write_text("tampering:\n  enabled: true\n")

    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args(["--repo-root", str(tmp_path)])

    exit_code = main(args)

    assert exit_code == 0, f"Command failed with exit code {exit_code}"

    captured = capsys.readouterr()
    assert "enabled" in captured.out.lower() or "true" in captured.out.lower()


def test_tampering_status_json_output(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """`edison tampering status --json` should return valid JSON with full status."""
    from edison.cli.tampering.status import main, register_args

    config_dir = tmp_path / ".edison" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "tampering.yaml").write_text(
        "tampering:\n  enabled: true\n  mode: deny-all\n"
    )

    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args(["--json", "--repo-root", str(tmp_path)])

    exit_code = main(args)

    assert exit_code == 0, f"Command failed with exit code {exit_code}"

    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["enabled"] is True
    assert output["mode"] == "deny-all"
    assert "protectedDir" in output


def test_tampering_status_json_includes_all_fields(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """`edison tampering status --json` should include all status fields."""
    from edison.cli.tampering.status import main, register_args

    (tmp_path / ".edison" / "config").mkdir(parents=True, exist_ok=True)

    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args(["--json", "--repo-root", str(tmp_path)])

    exit_code = main(args)

    assert exit_code == 0, f"Command failed with exit code {exit_code}"

    captured = capsys.readouterr()
    output = json.loads(captured.out)
    # Verify all expected fields are present
    assert "enabled" in output
    assert "mode" in output
    assert "protectedDir" in output


def test_tampering_status_default_mode(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """`edison tampering status` should show default mode when not configured."""
    from edison.cli.tampering.status import main, register_args

    config_dir = tmp_path / ".edison" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "tampering.yaml").write_text("tampering:\n  enabled: true\n")

    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args(["--json", "--repo-root", str(tmp_path)])

    exit_code = main(args)

    assert exit_code == 0, f"Command failed with exit code {exit_code}"

    captured = capsys.readouterr()
    output = json.loads(captured.out)
    # Default mode should be deny-write
    assert output["mode"] == "deny-write"
