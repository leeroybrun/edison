"""TDD tests for `edison tampering disable` command.

These tests verify that the tampering disable command:
1. Disables tampering protection in the config
2. Returns correct JSON output when --json flag is set
3. Returns correct text output in default mode
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest
import yaml


def test_tampering_disable_updates_config_file(tmp_path: Path) -> None:
    """`edison tampering disable` should set enabled=false in tampering.yaml."""
    from edison.cli.tampering.disable import main, register_args

    # Setup minimal Edison project structure with tampering enabled
    config_dir = tmp_path / ".edison" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    # First enable tampering
    (config_dir / "tampering.yaml").write_text("tampering:\n  enabled: true\n")

    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args(["--repo-root", str(tmp_path)])

    exit_code = main(args)

    assert exit_code == 0, f"Command failed with exit code {exit_code}"

    # Verify config file was updated with enabled=false
    config = yaml.safe_load((config_dir / "tampering.yaml").read_text())
    assert config["tampering"]["enabled"] is False


def test_tampering_disable_json_output(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """`edison tampering disable --json` should return valid JSON with status."""
    from edison.cli.tampering.disable import main, register_args

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
    assert output["enabled"] is False
    assert "configPath" in output


def test_tampering_disable_text_output(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """`edison tampering disable` should print success message in text mode."""
    from edison.cli.tampering.disable import main, register_args

    config_dir = tmp_path / ".edison" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "tampering.yaml").write_text("tampering:\n  enabled: true\n")

    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args(["--repo-root", str(tmp_path)])

    exit_code = main(args)

    assert exit_code == 0, f"Command failed with exit code {exit_code}"

    captured = capsys.readouterr()
    assert "disabled" in captured.out.lower() or "tampering" in captured.out.lower()


def test_tampering_disable_idempotent(tmp_path: Path) -> None:
    """`edison tampering disable` should be idempotent."""
    from edison.cli.tampering.disable import main, register_args

    config_dir = tmp_path / ".edison" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    parser = argparse.ArgumentParser()
    register_args(parser)

    # Run disable twice
    for _ in range(2):
        args = parser.parse_args(["--repo-root", str(tmp_path)])
        exit_code = main(args)
        assert exit_code == 0, f"Command failed with exit code {exit_code}"

    # Verify config is still disabled
    config_path = config_dir / "tampering.yaml"
    config = yaml.safe_load(config_path.read_text())
    assert config["tampering"]["enabled"] is False


def test_tampering_disable_creates_config_if_missing(tmp_path: Path) -> None:
    """`edison tampering disable` should create config file if it doesn't exist."""
    from edison.cli.tampering.disable import main, register_args

    (tmp_path / ".edison" / "config").mkdir(parents=True, exist_ok=True)

    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args(["--repo-root", str(tmp_path)])

    exit_code = main(args)

    assert exit_code == 0, f"Command failed with exit code {exit_code}"

    config_path = tmp_path / ".edison" / "config" / "tampering.yaml"
    assert config_path.exists()
    config = yaml.safe_load(config_path.read_text())
    assert config["tampering"]["enabled"] is False
