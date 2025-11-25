from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent


SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"


def _write_minimal_compose_config(root: Path) -> None:
    """Seed a tiny config surface so compose commands can run in isolation."""

    core_config = root / ".edison" / "core" / "config"
    core_config.mkdir(parents=True, exist_ok=True)

    (core_config / "commands.yaml").write_text(
        dedent(
            """
            commands:
              enabled: true
              platforms: [claude, cursor, codex]
              definitions:
                - id: demo-cmd
                  domain: demo
                  command: demo
                  short_desc: "Demo compose command"
                  full_desc: "Full demo description"
                  cli: "edison demo"
                  args: []
                  when_to_use: "When validating compose CLI"
                  related_commands: []
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    (core_config / "hooks.yaml").write_text(
        dedent(
            """
            hooks:
              enabled: true
              platforms: [claude]
              definitions:
                sample-hook:
                  enabled: true
                  description: "Sample hook for tests"
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    (core_config / "settings.yaml").write_text(
        dedent(
            """
            settings:
              enabled: true
              platforms: [claude]
              claude:
                generate: true
                permissions:
                  allow: ["Read(./**)"]
                  deny: []
                  ask: []
                env: {TEST_ENV: "1"}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    # Hooks templates directory (may remain empty, but path should exist)
    (root / ".edison" / "core" / "templates" / "hooks").mkdir(parents=True, exist_ok=True)


def _run(script: str, args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(cwd)
    cmd = [sys.executable, str(SCRIPTS_DIR / script), *args]
    return subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True)


def test_compose_commands_list_and_generate(isolated_project_env: Path):
    _write_minimal_compose_config(isolated_project_env)

    listed = _run("compose/commands.py", ["--list"], isolated_project_env)
    assert listed.returncode == 0, listed.stderr
    assert "demo-cmd" in listed.stdout

    generated = _run("compose/commands.py", ["--platform", "claude"], isolated_project_env)
    assert generated.returncode == 0, generated.stderr

    out_file = isolated_project_env / ".claude" / "commands" / "demo-cmd.md"
    assert out_file.exists(), "expected Claude command file to be created"
    contents = out_file.read_text(encoding="utf-8")
    assert "# demo" in contents.lower()


def test_compose_all_dry_run_skips_writes(isolated_project_env: Path):
    _write_minimal_compose_config(isolated_project_env)

    proc = _run("compose/all.py", ["--dry-run", "--platforms", "claude"], isolated_project_env)
    assert proc.returncode == 0, proc.stderr
    assert "dry-run" in proc.stdout.lower()

    assert not (isolated_project_env / ".claude" / "commands").exists()


def test_compose_settings_outputs_json(isolated_project_env: Path):
    _write_minimal_compose_config(isolated_project_env)

    proc = _run("compose/settings.py", [], isolated_project_env)
    assert proc.returncode == 0, proc.stderr

    settings_path = isolated_project_env / ".claude" / "settings.json"
    assert settings_path.exists()
    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    assert payload.get("permissions", {}).get("allow") == ["Read(./**)"]


def test_compose_validate_honors_schema_warnings(isolated_project_env: Path):
    _write_minimal_compose_config(isolated_project_env)

    proc = _run("compose/validate.py", [], isolated_project_env)
    assert proc.returncode == 0, proc.stderr
    assert "valid" in proc.stdout.lower()

