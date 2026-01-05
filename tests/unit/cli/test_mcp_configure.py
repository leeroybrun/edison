import json
import os
import subprocess
import sys
from pathlib import Path


def run_mcp_configure(args: list[str], env: dict, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Execute ``mcp configure`` command as a module."""

    env = env.copy()
    repo_root = Path(__file__).resolve().parents[3]
    env["PYTHONPATH"] = str(repo_root / "src")

    cmd = [sys.executable, "-m", "edison.cli.mcp.configure", *args]
    return subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        env=env,
        cwd=cwd,
        check=False,
    )


def test_mcp_configure_command_module_exists():
    """Command module is importable and exposes CLI hooks."""
    import importlib

    module = importlib.import_module("edison.cli.mcp.configure")

    assert hasattr(module, "SUMMARY")
    assert callable(module.register_args)
    assert callable(module.main)


def test_configure_creates_mcp_json_with_all_servers(tmp_path: Path):
    """Creates .mcp.json with all configured servers when missing."""

    project_root = tmp_path / "project"
    project_root.mkdir()

    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(project_root)

    result = run_mcp_configure([str(project_root)], env)

    assert result.returncode == 0, result.stdout + result.stderr

    mcp_path = project_root / ".mcp.json"
    assert mcp_path.exists()

    data = json.loads(mcp_path.read_text())
    servers = data["mcpServers"]
    assert "edison-pal" in servers
    assert "context7" in servers
    assert servers["edison-pal"]["env"]["PAL_WORKING_DIR"] == str(project_root.resolve())
    # Pal MCP server must be locked down to avoid context bloat.
    # We only need clink (plus essential listmodels/version which cannot be disabled upstream).
    assert "DISABLED_TOOLS" in servers["edison-pal"]["env"]
    # pal-mcp-server currently requires at least one provider configured at startup.
    assert "CUSTOM_API_URL" in servers["edison-pal"]["env"]
    assert servers["edison-pal"]["args"][-1] == "pal-mcp-server"


def test_configure_updates_existing_without_clobbering(tmp_path: Path):
    """Existing user servers remain while Edison-managed entries are updated."""

    project_root = tmp_path / "project"
    project_root.mkdir()

    mcp_path = project_root / ".mcp.json"
    preexisting = {
        "version": 1,
        "mcpServers": {
            "other": {"command": "other", "args": ["run"], "env": {}},
            # Any existing `edison-*` entry not present in current config should be removed.
            "edison-legacy": {"command": "legacy", "args": [], "env": {}},
        },
    }
    mcp_path.write_text(json.dumps(preexisting, indent=2))

    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(project_root)

    result = run_mcp_configure([str(project_root)], env)

    assert result.returncode == 0, result.stdout + result.stderr

    data = json.loads(mcp_path.read_text())
    assert "other" in data["mcpServers"]
    assert "edison-pal" in data["mcpServers"]
    assert "context7" in data["mcpServers"]
    assert data["mcpServers"]["other"]["command"] == "other"
    assert data["mcpServers"]["edison-pal"]["command"] != "legacy"
    assert "edison-legacy" not in data["mcpServers"]


def test_configure_dry_run_does_not_write(tmp_path: Path):
    """--dry-run prints configuration without writing file."""

    project_root = tmp_path / "project"
    project_root.mkdir()

    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(project_root)

    result = run_mcp_configure(["--dry-run", str(project_root)], env)

    assert result.returncode == 0, result.stderr
    assert ".mcp.json" not in {p.name for p in project_root.iterdir()}
    assert "mcpServers" in result.stdout
    assert "edison-pal" in result.stdout


def test_configure_rejects_invalid_existing_config(tmp_path: Path):
    """Invalid existing .mcp.json triggers a validation error."""

    project_root = tmp_path / "project"
    project_root.mkdir()

    mcp_path = project_root / ".mcp.json"
    mcp_path.write_text("[]")  # invalid structure

    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(project_root)

    result = run_mcp_configure([str(project_root)], env)

    assert result.returncode != 0
    assert "invalid" in result.stderr.lower() or "invalid" in result.stdout.lower()
    # Existing file should remain unchanged
    assert mcp_path.read_text() == "[]"
