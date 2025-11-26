import json
import os
import subprocess
import sys
from pathlib import Path


def run_edison_init(args: list[str], env: dict[str, str], cwd: Path) -> subprocess.CompletedProcess:
    """Execute ``edison init`` via the commands.init module."""

    env = env.copy()
    env.setdefault("PYTHONPATH", os.getcwd() + "/src")

    cmd = [sys.executable, "-m", "edison.cli.commands.init", *args]
    return subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        env=env,
        cwd=cwd,
        check=False,
    )


def _base_env(project_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(project_root)
    return env


def test_init_configures_zen_by_default(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()

    result = run_edison_init([], _base_env(project), project)

    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)

    mcp_path = project / ".mcp.json"
    assert mcp_path.exists()

    data = json.loads(mcp_path.read_text())
    assert "edison-zen" in data.get("mcpServers", {})
    env = data["mcpServers"]["edison-zen"].get("env", {})
    assert env.get("ZEN_WORKING_DIR") == str(project.resolve())


def test_init_can_skip_zen_setup(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()

    result = run_edison_init(["--skip-zen"], _base_env(project), project)

    assert result.returncode == 0, result.stderr
    assert not (project / ".mcp.json").exists()


def test_init_zen_script_option_uses_run_script(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()

    result = run_edison_init(["--zen-script"], _base_env(project), project)

    assert result.returncode == 0, result.stderr

    data = json.loads((project / ".mcp.json").read_text())
    server = data["mcpServers"]["edison-zen"]
    assert server["command"].endswith("run-server.sh")


def test_init_handles_mcp_config_error(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()

    bad_mcp = project / ".mcp.json"
    bad_mcp.write_text("[]")

    result = run_edison_init([], _base_env(project), project)

    assert result.returncode == 0  # should not crash init
    combined = (result.stdout + result.stderr).lower()
    assert "warning" in combined or "could not configure" in combined
    assert bad_mcp.read_text() == "[]"
