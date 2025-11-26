"""End-to-end verification of the Zen MCP workflow.

This suite exercises the real Edison CLI entrypoints to validate that the
Zen setup, configuration, and initialization flows work together. The tests
avoid mocks and source all expectations from the YAML configuration to ensure
coherence with the shipped defaults.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from edison.data import read_yaml
from edison.core.utils.subprocess import run_with_timeout


# Configuration is loaded from the shipped YAML to avoid hardcoded values.
_ZEN_CFG = read_yaml("config", "zen.yaml") or {}
_MCP_CFG = (_ZEN_CFG.get("zen") or {}).get("mcp") or {}

_REQUIRED_KEYS = {"server_id", "command", "args", "config_file"}
_missing = _REQUIRED_KEYS - set(_MCP_CFG.keys())
if _missing:
    raise RuntimeError(f"Missing required zen.mcp keys: {', '.join(sorted(_missing))}")

SERVER_ID = str(_MCP_CFG["server_id"])
CONFIG_FILE_NAME = str(_MCP_CFG["config_file"])
COMMAND = str(_MCP_CFG["command"])
COMMAND_ARGS = [str(arg) for arg in (_MCP_CFG.get("args") or [])]


def _cli_env(repo_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", f"{repo_root / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}")
    env.setdefault("PROJECT_ROOT", str(repo_root))
    env.setdefault("AGENTS_PROJECT_ROOT", str(repo_root))
    return env


def run_edison(repo_root: Path, args: list[str], cwd: Path) -> tuple[int, str, str]:
    """Execute Edison CLI with repository-local sources."""

    result = run_with_timeout(
        [sys.executable, "-m", "edison", *args],
        cwd=cwd,
        env=_cli_env(repo_root),
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Isolated project root for CLI commands."""

    root = tmp_path / "zen-project"
    root.mkdir()
    return root


def test_zen_setup_check_reports_status(repo_root: Path):
    """zen setup --check should report status without failing."""

    code, stdout, stderr = run_edison(repo_root, ["zen", "setup", "--check"], cwd=repo_root)

    assert code == 0
    combined = (stdout + stderr).lower()
    assert "zen-mcp-server" in combined or "uvx" in combined


def test_zen_configure_dry_run_outputs_server_entry(repo_root: Path, project_dir: Path):
    """Dry-run configure prints JSON without touching disk."""

    code, stdout, _stderr = run_edison(
        repo_root,
        ["zen", "configure", str(project_dir), "--dry-run"],
        cwd=project_dir,
    )

    assert code == 0

    payload = json.loads(stdout)
    assert "mcpServers" in payload
    assert SERVER_ID in payload["mcpServers"]
    server_cfg = payload["mcpServers"][SERVER_ID]
    assert server_cfg["command"] == COMMAND
    assert server_cfg.get("args") == COMMAND_ARGS

    target = project_dir / CONFIG_FILE_NAME
    assert not target.exists()


def test_zen_configure_writes_mcp_json(repo_root: Path, project_dir: Path):
    """configure writes .mcp.json using YAML-driven values."""

    code, _stdout, stderr = run_edison(
        repo_root,
        ["zen", "configure", str(project_dir)],
        cwd=project_dir,
    )

    assert code == 0, stderr

    target = project_dir / CONFIG_FILE_NAME
    assert target.exists()

    config = json.loads(target.read_text())
    assert SERVER_ID in config.get("mcpServers", {})
    server_cfg = config["mcpServers"][SERVER_ID]
    assert server_cfg["command"] == COMMAND
    assert server_cfg.get("args") == COMMAND_ARGS
    assert server_cfg.get("env", {}).get("ZEN_WORKING_DIR") == str(project_dir.resolve())


def test_zen_configure_preserves_existing_servers(repo_root: Path, project_dir: Path):
    """Existing MCP servers remain alongside the Zen entry."""

    existing_id = "existing-server"
    initial = {
        "mcpServers": {
            existing_id: {
                "command": "existing",
                "args": ["--stay"],
                "env": {},
            }
        }
    }
    target = project_dir / CONFIG_FILE_NAME
    target.write_text(json.dumps(initial))

    code, _stdout, stderr = run_edison(
        repo_root,
        ["zen", "configure", str(project_dir)],
        cwd=project_dir,
    )

    assert code == 0, stderr

    updated = json.loads(target.read_text())
    assert existing_id in updated.get("mcpServers", {})
    assert SERVER_ID in updated.get("mcpServers", {})


def test_init_configures_zen_by_default(repo_root: Path, project_dir: Path):
    """edison init should scaffold .edison and configure Zen."""

    code, stdout, stderr = run_edison(
        repo_root,
        ["init", str(project_dir)],
        cwd=project_dir,
    )

    assert code == 0, f"stdout: {stdout}\nstderr: {stderr}"
    combined = (stdout + stderr).lower()
    assert "error" not in combined

    config_root = project_dir / ".edison"
    assert config_root.exists()
    assert (config_root / "config").exists()

    target = project_dir / CONFIG_FILE_NAME
    assert target.exists()
    config = json.loads(target.read_text())
    assert SERVER_ID in config.get("mcpServers", {})


def test_init_can_skip_zen(repo_root: Path, project_dir: Path):
    """--skip-zen should avoid writing MCP configuration."""

    code, stdout, stderr = run_edison(
        repo_root,
        ["init", str(project_dir), "--skip-zen"],
        cwd=project_dir,
    )

    assert code == 0, f"stdout: {stdout}\nstderr: {stderr}"

    assert (project_dir / ".edison").exists()
    assert not (project_dir / CONFIG_FILE_NAME).exists()


def test_verification_script_runs(repo_root: Path, tmp_path: Path):
    """Shell verification script should succeed end-to-end in a temp workspace."""

    script = (repo_root / "scripts" / "verify_zen_setup.sh").resolve()
    assert script.exists(), "verification script must be present"

    target_env = _cli_env(repo_root)
    target_env["ZEN_VERIFY_SKIP_SERVER"] = "1"
    target_env["TMPDIR"] = str(tmp_path)

    result = run_with_timeout(
        ["bash", str(script)],
        cwd=repo_root,
        env=target_env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"
    assert "Zen setup verification".lower() in result.stdout.lower()
