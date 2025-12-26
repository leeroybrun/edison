"""Tests for `edison compose hooks` CLI.

NO MOCKS - real subprocess calls, real file I/O, real CLI execution.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _base_env(project_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(project_root)
    env.setdefault("PYTHONPATH", os.getcwd() + "/src")
    return env


def run_compose_hooks(args: list[str], *, env: dict[str, str], cwd: Path) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "edison.cli.compose.hooks", *args]
    return subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        env=env,
        cwd=cwd,
        check=False,
    )


def test_compose_hooks_json_succeeds_and_writes_files(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    hooks_out = project / ".claude" / "hooks"
    args = ["--json", "--no-settings", "--output", str(hooks_out), "--repo-root", str(project)]
    result = run_compose_hooks(args, env=_base_env(project), cwd=project)
    assert result.returncode == 0, f"Command failed:\n{result.stdout}\n{result.stderr}"

    payload = json.loads(result.stdout)
    assert isinstance(payload, dict)
    assert payload.get("count", 0) > 0

    # Sanity: at least one core hook should be written.
    assert any(hooks_out.glob("*.sh")), f"Expected hook scripts in {hooks_out}"

