"""Tests for `edison init` (setup wizard).

NO MOCKS - real subprocess calls, real file I/O, real git when enabled.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import yaml


def _base_env(project_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(project_root)
    env.setdefault("PYTHONPATH", os.getcwd() + "/src")
    return env


def _run_init(args: list[str], *, env: dict[str, str], cwd: Path) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "edison.cli.commands.init", *args]
    return subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        env=env,
        cwd=cwd,
        check=False,
    )


def test_init_non_interactive_writes_config_and_disables_worktrees_by_default(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()

    result = _run_init(
        ["--non-interactive", "--skip-mcp", "--skip-compose", str(project)],
        env=_base_env(project),
        cwd=project,
    )
    assert result.returncode == 0, f"Command failed:\n{result.stdout}\n{result.stderr}"

    worktrees_cfg = project / ".edison" / "config" / "worktrees.yml"
    assert worktrees_cfg.exists(), f"Expected {worktrees_cfg} to be written"
    data = yaml.safe_load(worktrees_cfg.read_text(encoding="utf-8")) or {}
    assert (data.get("worktrees") or {}).get("enabled") is False


def test_init_non_interactive_enable_worktrees_runs_meta_init(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()

    # Initialize a minimal git repo; meta init requires git worktrees support.
    subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True, text=True)
    (project / "README.md").write_text("# proj\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=project, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=project, check=True, capture_output=True, text=True)

    result = _run_init(
        ["--non-interactive", "--enable-worktrees", "--skip-mcp", "--skip-compose", str(project)],
        env=_base_env(project),
        cwd=project,
    )
    assert result.returncode == 0, f"Command failed:\n{result.stdout}\n{result.stderr}"

    # Default meta path template: .worktrees/_meta
    meta_path = project / ".worktrees" / "_meta"
    assert meta_path.exists(), f"Expected meta worktree at {meta_path}"
    assert (project / ".project" / "tasks").is_symlink()
