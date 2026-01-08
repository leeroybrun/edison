"""TDD tests for `edison tampering enable` command.

These tests verify that the tampering enable command:
1. Enables tampering protection in the config
2. Returns correct JSON output when --json flag is set
3. Returns correct text output in default mode
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest
import yaml


def test_tampering_enable_creates_config_file(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """`edison tampering enable` should create tampering.yaml with enabled=true."""
    from edison.cli.tampering.enable import main, register_args

    # Setup minimal Edison project structure
    (tmp_path / ".edison" / "config").mkdir(parents=True, exist_ok=True)

    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args(["--repo-root", str(tmp_path)])

    exit_code = main(args)

    assert exit_code == 0, f"Command failed with exit code {exit_code}"

    # Verify config file was created with enabled=true
    config_path = tmp_path / ".edison" / "config" / "tampering.yaml"
    assert config_path.exists(), "tampering.yaml was not created"

    config = yaml.safe_load(config_path.read_text())
    assert config["tampering"]["enabled"] is True


def test_tampering_enable_json_output(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """`edison tampering enable --json` should return valid JSON with status."""
    from edison.cli.tampering.enable import main, register_args

    (tmp_path / ".edison" / "config").mkdir(parents=True, exist_ok=True)

    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args(["--json", "--repo-root", str(tmp_path)])

    exit_code = main(args)

    assert exit_code == 0, f"Command failed with exit code {exit_code}"

    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["enabled"] is True
    assert "configPath" in output


def test_tampering_enable_text_output(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """`edison tampering enable` should print success message in text mode."""
    from edison.cli.tampering.enable import main, register_args

    (tmp_path / ".edison" / "config").mkdir(parents=True, exist_ok=True)

    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args(["--repo-root", str(tmp_path)])

    exit_code = main(args)

    assert exit_code == 0, f"Command failed with exit code {exit_code}"

    captured = capsys.readouterr()
    assert "enabled" in captured.out.lower() or "tampering" in captured.out.lower()


def test_tampering_enable_idempotent(tmp_path: Path) -> None:
    """`edison tampering enable` should be idempotent."""
    from edison.cli.tampering.enable import main, register_args

    (tmp_path / ".edison" / "config").mkdir(parents=True, exist_ok=True)

    parser = argparse.ArgumentParser()
    register_args(parser)

    # Run enable twice
    for _ in range(2):
        args = parser.parse_args(["--repo-root", str(tmp_path)])
        exit_code = main(args)
        assert exit_code == 0, f"Command failed with exit code {exit_code}"

    # Verify config is still enabled
    config_path = tmp_path / ".edison" / "config" / "tampering.yaml"
    config = yaml.safe_load(config_path.read_text())
    assert config["tampering"]["enabled"] is True
