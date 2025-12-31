from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

from tests.helpers.io_utils import write_minimal_compose_config
from tests.helpers.paths import get_repo_root


EDISON_ROOT = get_repo_root()


def _run_command(domain: str, command: str, args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Execute a CLI command using python -m edison.cli.<domain>.<command>."""
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(cwd)
    cmd = [sys.executable, "-m", f"edison.cli.{domain}.{command}", *args]
    return subprocess.run(cmd, cwd=EDISON_ROOT, env=env, text=True, capture_output=True)


def test_compose_commands_list_and_generate(isolated_project_env: Path):
    write_minimal_compose_config(isolated_project_env, platforms=["claude", "cursor", "codex"], include_env=True)

    listed = _run_command("compose", "commands", ["--list"], isolated_project_env)
    assert listed.returncode == 0, listed.stderr
    assert "demo-cmd" in listed.stdout

    generated = _run_command("compose", "commands", ["--platform", "claude"], isolated_project_env)
    assert generated.returncode == 0, generated.stderr

    out_file = isolated_project_env / ".claude" / "commands" / "demo-cmd.md"
    assert out_file.exists(), "expected Claude command file to be created"
    contents = out_file.read_text(encoding="utf-8")
    assert "# demo" in contents.lower()


def test_compose_all_dry_run_skips_writes(isolated_project_env: Path):
    write_minimal_compose_config(isolated_project_env, platforms=["claude", "cursor", "codex"], include_env=True)

    proc = _run_command("compose", "all", ["--dry-run", "--claude"], isolated_project_env)
    assert proc.returncode == 0, proc.stderr
    assert "dry-run" in proc.stdout.lower()

    assert not (isolated_project_env / ".claude" / "commands").exists()


def test_compose_settings_outputs_json(isolated_project_env: Path):
    write_minimal_compose_config(isolated_project_env, platforms=["claude", "cursor", "codex"], include_env=True)

    proc = _run_command("compose", "settings", [], isolated_project_env)
    assert proc.returncode == 0, proc.stderr

    settings_path = isolated_project_env / ".claude" / "settings.json"
    assert settings_path.exists()
    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    assert payload.get("permissions", {}).get("allow") == ["Read(./**)"]


def test_compose_validate_honors_schema_warnings(isolated_project_env: Path):
    write_minimal_compose_config(isolated_project_env, platforms=["claude", "cursor", "codex"], include_env=True)

    proc = _run_command("compose", "validate", [], isolated_project_env)
    assert proc.returncode == 0, proc.stderr
    assert "valid" in proc.stdout.lower()
