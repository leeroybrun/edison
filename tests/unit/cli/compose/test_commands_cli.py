"""Tests for `edison compose commands` CLI.

NO MOCKS - real subprocess calls, real file I/O, real CLI execution.
"""
from __future__ import annotations

import json
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


def _parse_frontmatter(md: str) -> dict:
    lines = md.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return {}
    return yaml.safe_load("\n".join(lines[1:end])) or {}


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

    # File name should respect platform prefix from commands.yaml ("edison.").
    cmd_file = out_dir / "edison.session-next.md"
    assert cmd_file.exists(), f"Expected command file at {cmd_file}"

    text = cmd_file.read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    assert isinstance(fm.get("description"), str) and fm["description"]
    assert fm.get("edison-generated") is True

    claim_file = out_dir / "edison.task-claim.md"
    assert claim_file.exists(), f"Expected command file at {claim_file}"

    status_file = out_dir / "edison.task-status.md"
    assert status_file.exists(), f"Expected command file at {status_file}"
    assert status_file.read_text(encoding="utf-8").strip()


def test_compose_commands_writes_cursor_commands(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    out_dir = project / ".cursor" / "commands"
    args = ["--platform", "cursor", "--repo-root", str(project)]
    result = run_compose_commands(args, env=_base_env(project), cwd=project)
    assert result.returncode == 0, f"Command failed:\n{result.stdout}\n{result.stderr}"

    cmd_file = out_dir / "edison.session-next.md"
    assert cmd_file.exists(), f"Expected command file at {cmd_file}"
    assert cmd_file.read_text(encoding="utf-8").strip()


def test_compose_commands_writes_codex_prompts_with_valid_frontmatter(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    out_dir = project / ".codex" / "prompts"
    args = ["--platform", "codex", "--output", str(out_dir), "--repo-root", str(project)]
    result = run_compose_commands(args, env=_base_env(project), cwd=project)
    assert result.returncode == 0, f"Command failed:\n{result.stdout}\n{result.stderr}"

    cmd_file = out_dir / "edison.session-next.md"
    assert cmd_file.exists(), f"Expected command file at {cmd_file}"
    text = cmd_file.read_text(encoding="utf-8")

    # Codex prompts are YAML-frontmatter + markdown. The YAML must be parseable.
    fm = _parse_frontmatter(text)
    assert isinstance(fm.get("edison-platform"), str) and fm["edison-platform"]
    assert fm.get("edison-id") == "session-next"
    assert text.strip()


def test_compose_commands_prunes_stale_generated_files(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    out_dir = project / ".claude" / "commands"
    out_dir.mkdir(parents=True, exist_ok=True)

    stale_generated = out_dir / "edison.stale-generated.md"
    stale_generated.write_text(
        "---\n"
        "description: \"stale\"\n"
        "edison-generated: true\n"
        "---\n"
        "\n"
        "# stale\n",
        encoding="utf-8",
    )
    assert stale_generated.exists()

    stale_legacy_generated = out_dir / "edison.stale-legacy.md"
    stale_legacy_generated.write_text(
        "---\n"
        "description: \"legacy\"\n"
        "---\n"
        "\n"
        "# edison.stale-legacy\n"
        "\n"
        "## Related Commands\n"
        "- /edison.session-next\n",
        encoding="utf-8",
    )
    assert stale_legacy_generated.exists()

    keep_user_file = out_dir / "edison.keep-user.md"
    keep_user_file.write_text("# user file\n", encoding="utf-8")
    assert keep_user_file.exists()

    args = ["--platform", "claude", "--repo-root", str(project)]
    result = run_compose_commands(args, env=_base_env(project), cwd=project)
    assert result.returncode == 0, f"Command failed:\n{result.stdout}\n{result.stderr}"

    assert not stale_generated.exists(), "Expected Edison to prune stale generated command file"
    assert not stale_legacy_generated.exists(), "Expected Edison to prune stale legacy Edison command file"
    assert keep_user_file.exists(), "Expected Edison not to delete user-created command files"


def test_compose_commands_prunes_legacy_prefix_files(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    out_dir = project / ".claude" / "commands"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Legacy Edison used `edison-` as a filename prefix. When the configured
    # prefix changes to `edison.`, the composer should still prune those old
    # Edison-generated files so stale commands don't stick around.
    stale_legacy_prefix = out_dir / "edison-stale-prefix.md"
    stale_legacy_prefix.write_text(
        "---\n"
        "description: \"legacy-prefix\"\n"
        "edison-generated: true\n"
        "---\n"
        "\n"
        "# edison-stale-prefix\n",
        encoding="utf-8",
    )
    assert stale_legacy_prefix.exists()

    keep_user_legacy_prefix = out_dir / "edison-keep-user.md"
    keep_user_legacy_prefix.write_text("# user file\n", encoding="utf-8")
    assert keep_user_legacy_prefix.exists()

    args = ["--platform", "claude", "--repo-root", str(project)]
    result = run_compose_commands(args, env=_base_env(project), cwd=project)
    assert result.returncode == 0, f"Command failed:\n{result.stdout}\n{result.stderr}"

    assert not stale_legacy_prefix.exists(), "Expected Edison to prune legacy-prefix generated command file"
    assert keep_user_legacy_prefix.exists(), "Expected Edison not to delete user-created legacy-prefix files"
