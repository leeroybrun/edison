"""End-to-end verification of the generic MCP workflow.

This suite exercises the Edison CLI entrypoints to validate that the MCP
setup, configuration, and initialization flows work together. The tests avoid
mocks and source all expectations from the YAML configuration to ensure
coherence with the shipped defaults.
"""

from __future__ import annotations

import json
import os
import sys
import argparse
from pathlib import Path

import pytest

from edison.data import read_yaml
from edison.core.utils.subprocess import run_with_timeout


_MCP_CFG = (read_yaml("config", "mcp.yml") or {}).get("mcp") or {}
_SERVERS = _MCP_CFG.get("servers") or {}

if not _SERVERS:
    raise RuntimeError("mcp.yml must declare at least one server")

DEFAULT_SERVER_ID = next(iter(_SERVERS.keys()))
CONFIG_FILE_NAME = str(_MCP_CFG.get("config_file", ".mcp.json"))
COMMAND = str((_SERVERS.get(DEFAULT_SERVER_ID) or {}).get("command", ""))
COMMAND_ARGS = [str(arg) for arg in (_SERVERS.get(DEFAULT_SERVER_ID) or {}).get("args", [])]


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


def test_mcp_setup_check_reports_status(repo_root: Path):
    """mcp setup --check should report status without failing."""

    code, stdout, stderr = run_edison(repo_root, ["mcp", "setup", "--check"], cwd=repo_root)

    assert code == 0
    combined = (stdout + stderr).lower()
    assert "mcp" in combined


def test_mcp_configure_dry_run_outputs_server_entry(repo_root: Path, project_dir: Path):
    """Dry-run configure prints JSON without touching disk."""

    from edison.core.mcp.config import configure_mcp_json

    payload = configure_mcp_json(project_dir, dry_run=True)
    assert "mcpServers" in payload
    for server_id in _SERVERS.keys():
        assert server_id in payload["mcpServers"]

    target = project_dir / CONFIG_FILE_NAME
    assert not target.exists()


def test_mcp_configure_writes_mcp_json(repo_root: Path, project_dir: Path):
    """configure writes .mcp.json using YAML-driven values."""

    from edison.cli.mcp import configure as mcp_configure
    args = argparse.Namespace(
        project_path=str(project_dir),
        dry_run=False,
        config_file=None,
        servers=None,
    )
    code = mcp_configure.main(args)

    assert code == 0

    target = project_dir / CONFIG_FILE_NAME
    assert target.exists()

    config = json.loads(target.read_text())
    for server_id in _SERVERS.keys():
        assert server_id in config.get("mcpServers", {})
        server_cfg = config["mcpServers"][server_id]
        src_cfg = _SERVERS[server_id]
        assert server_cfg["command"] == src_cfg["command"]
        assert server_cfg.get("args") == src_cfg.get("args")
    assert config["mcpServers"][DEFAULT_SERVER_ID].get("env", {}).get("ZEN_WORKING_DIR") == str(project_dir.resolve())


def test_mcp_configure_preserves_existing_servers(repo_root: Path, project_dir: Path):
    """Existing MCP servers remain alongside the configured entries."""

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

    from edison.cli.mcp import configure as mcp_configure
    args = argparse.Namespace(
        project_path=str(project_dir),
        dry_run=False,
        config_file=None,
        servers=None,
    )
    code = mcp_configure.main(args)

    assert code == 0

    updated = json.loads(target.read_text())
    assert existing_id in updated.get("mcpServers", {})
    for server_id in _SERVERS.keys():
        assert server_id in updated.get("mcpServers", {})


def test_init_configures_mcp_by_default(repo_root: Path, project_dir: Path):
    """edison init should scaffold .edison and configure MCP servers."""

    from edison.cli.commands import init as init_cmd
    args = argparse.Namespace(project_path=str(project_dir), skip_mcp=False, mcp_script=False)
    code = init_cmd.main(args)
    assert code == 0

    config_root = project_dir / ".edison"
    assert config_root.exists()
    assert (config_root / "config").exists()

    target = project_dir / CONFIG_FILE_NAME
    assert target.exists()
    config = json.loads(target.read_text())
    for server_id in _SERVERS.keys():
        assert server_id in config.get("mcpServers", {})


def test_init_can_skip_mcp(repo_root: Path, project_dir: Path):
    """--skip-mcp should avoid writing MCP configuration."""

    from edison.cli.commands import init as init_cmd
    args = argparse.Namespace(project_path=str(project_dir), skip_mcp=True, mcp_script=False)
    code = init_cmd.main(args)
    assert code == 0

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
    assert "setup verification".lower() in result.stdout.lower()
