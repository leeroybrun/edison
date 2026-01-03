from __future__ import annotations

from pathlib import Path

import argparse

import pytest


def _parse_setup_args(repo_root: Path, *argv: str):
    from edison.cli.opencode.setup import register_args

    parser = argparse.ArgumentParser()
    register_args(parser)
    return parser.parse_args([*argv, "--repo-root", str(repo_root), "--json"])


def test_opencode_setup_dry_run_does_not_write_files(isolated_project_env: Path) -> None:
    from edison.cli.opencode.setup import main

    args = _parse_setup_args(isolated_project_env, "--dry-run")
    rc = main(args)
    assert rc == 0
    assert not (isolated_project_env / ".opencode").exists()


def test_opencode_setup_yes_creates_plugin_file(isolated_project_env: Path) -> None:
    from edison.cli.opencode.setup import main

    args = _parse_setup_args(isolated_project_env, "--yes")
    rc = main(args)
    assert rc == 0

    plugin_path = isolated_project_env / ".opencode" / "plugin" / "edison.ts"
    assert plugin_path.exists()
    content = plugin_path.read_text(encoding="utf-8")
    assert "Edison" in content


def test_opencode_setup_requires_force_to_overwrite(isolated_project_env: Path) -> None:
    from edison.cli.opencode.setup import main

    plugin_path = isolated_project_env / ".opencode" / "plugin" / "edison.ts"
    plugin_path.parent.mkdir(parents=True, exist_ok=True)
    plugin_path.write_text("// local edits\n", encoding="utf-8")

    args_no_force = _parse_setup_args(isolated_project_env, "--yes")
    rc = main(args_no_force)
    assert rc != 0
    assert plugin_path.read_text(encoding="utf-8") == "// local edits\n"

    args_force = _parse_setup_args(isolated_project_env, "--yes", "--force")
    rc = main(args_force)
    assert rc == 0
    assert plugin_path.read_text(encoding="utf-8") != "// local edits\n"
