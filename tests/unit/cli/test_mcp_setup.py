import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


def run_mcp_setup(args: list[str], env: dict, cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    """Execute ``mcp setup`` command."""
    env = env.copy()
    repo_root = Path(__file__).resolve().parents[3]
    env["PYTHONPATH"] = str(repo_root / "src")

    cmd = [sys.executable, "-m", "edison.cli.mcp.setup", *args]
    return subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        env=env,
        cwd=cwd,
        check=False,
    )


def test_mcp_setup_creates_config_for_all_servers(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()

    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(project_root)

    result = run_mcp_setup([str(project_root)], env, cwd=project_root)

    assert result.returncode == 0, result.stdout + result.stderr

    mcp_path = project_root / ".mcp.json"
    assert mcp_path.exists()
    data = json.loads(mcp_path.read_text())
    servers = data.get("mcpServers", {})
    assert "edison-zen" in servers
    assert "context7" in servers


def test_mcp_setup_preserves_user_defined_servers(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()

    existing = {
        "mcpServers": {
            "user-custom": {"command": "custom", "args": [], "env": {"X": "1"}},
            "edison-zen": {"command": "legacy", "args": [], "env": {}},
        }
    }
    (project_root / ".mcp.json").write_text(json.dumps(existing))

    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(project_root)

    result = run_mcp_setup([str(project_root)], env, cwd=project_root)

    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads((project_root / ".mcp.json").read_text())
    assert "user-custom" in data["mcpServers"]
    assert data["mcpServers"]["user-custom"]["command"] == "custom"
    assert data["mcpServers"]["edison-zen"]["command"] != "legacy"


def test_mcp_setup_dry_run_outputs_without_writing(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()

    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(project_root)

    result = run_mcp_setup(["--dry-run", str(project_root)], env, cwd=project_root)

    assert result.returncode == 0, result.stderr
    assert ".mcp.json" not in {p.name for p in project_root.iterdir()}
    assert "mcpServers" in result.stdout
