"""Tests for `edison compose commands` CLI.

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


def run_compose_commands(args: list[str], *, env: dict[str, str], cwd: Path) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "edison.cli.compose.commands", *args]
    return subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        env=env,
        cwd=cwd,
        check=False,
    )


def test_compose_commands_list_json_succeeds(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    result = run_compose_commands(["--list", "--json", "--repo-root", str(project)], env=_base_env(project), cwd=project)
    assert result.returncode == 0, f"Command failed:\n{result.stdout}\n{result.stderr}"

    payload = json.loads(result.stdout)
    assert isinstance(payload, dict)
    assert "commands" in payload
    assert any(c.get("id") == "session-next" for c in payload["commands"])


def test_compose_commands_writes_claude_commands(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    out_dir = project / ".claude" / "commands"
    args = ["--platform", "claude", "--repo-root", str(project)]
    result = run_compose_commands(args, env=_base_env(project), cwd=project)
    assert result.returncode == 0, f"Command failed:\n{result.stdout}\n{result.stderr}"

    # File name should respect platform prefix from commands.yaml ("edison-").
    cmd_file = out_dir / "edison-session-next.md"
    assert cmd_file.exists(), f"Expected command file at {cmd_file}"

    text = cmd_file.read_text(encoding="utf-8")
    # Claude SlashCommand tool only indexes commands with a description.
    assert "description:" in text
    # Edison default: commands are workflow guidance, not auto-executed bash.
    assert "edison session next" in text
    assert "!edison session next" not in text

    # Commands with args should expose an argument hint for ergonomics.
    claim_file = out_dir / "edison-task-claim.md"
    assert claim_file.exists(), f"Expected command file at {claim_file}"
    claim_text = claim_file.read_text(encoding="utf-8")
    assert "argument-hint:" in claim_text
    assert "task_id" in claim_text
