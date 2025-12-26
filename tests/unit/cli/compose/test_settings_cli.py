"""Tests for `edison compose settings` CLI.

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


def run_compose_settings(args: list[str], *, env: dict[str, str], cwd: Path) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "edison.cli.compose.settings", *args]
    return subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        env=env,
        cwd=cwd,
        check=False,
    )


def test_compose_settings_json_writes_settings(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    result = run_compose_settings(["--json", "--repo-root", str(project)], env=_base_env(project), cwd=project)
    assert result.returncode == 0, f"Command failed:\n{result.stdout}\n{result.stderr}"

    payload = json.loads(result.stdout)
    assert isinstance(payload, dict)
    assert "settings" in payload

    settings_path = project / ".claude" / "settings.json"
    assert settings_path.exists(), f"Expected settings.json at {settings_path}"

