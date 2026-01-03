"""Tests for OpenCode project config template generation (task 080)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _parse_setup_args(repo_root: Path, *argv: str):
    from edison.cli.opencode.setup import register_args

    parser = argparse.ArgumentParser()
    register_args(parser)
    return parser.parse_args([*argv, "--repo-root", str(repo_root), "--json"])


def test_opencode_setup_generates_opencode_json(isolated_project_env: Path) -> None:
    """Setup with --config should generate opencode.json in project root."""
    from edison.cli.opencode.setup import main

    args = _parse_setup_args(isolated_project_env, "--yes", "--config")
    rc = main(args)
    assert rc == 0

    config_path = isolated_project_env / "opencode.json"
    assert config_path.exists(), "opencode.json should be created"

    content = json.loads(config_path.read_text(encoding="utf-8"))
    assert "$schema" in content, "Should include $schema for validation"


def test_opencode_setup_generates_plugin_package_json(isolated_project_env: Path) -> None:
    """Setup with --plugin-deps should generate .opencode/package.json."""
    from edison.cli.opencode.setup import main

    args = _parse_setup_args(isolated_project_env, "--yes", "--plugin-deps")
    rc = main(args)
    assert rc == 0

    pkg_path = isolated_project_env / ".opencode" / "package.json"
    assert pkg_path.exists(), ".opencode/package.json should be created"

    content = json.loads(pkg_path.read_text(encoding="utf-8"))
    assert "name" in content
    assert "dependencies" in content or "devDependencies" in content or content.get("private") is True


def test_opencode_setup_all_includes_config_files(isolated_project_env: Path) -> None:
    """Setup with --all should include opencode.json and plugin package.json."""
    from edison.cli.opencode.setup import main

    args = _parse_setup_args(isolated_project_env, "--yes", "--all")
    rc = main(args)
    assert rc == 0

    # Plugin should exist
    assert (isolated_project_env / ".opencode" / "plugin" / "edison.ts").exists()

    # Agents should exist
    assert (isolated_project_env / ".opencode" / "agent" / "edison-orchestrator.md").exists()

    # Commands should exist
    assert (isolated_project_env / ".opencode" / "command" / "edison-session-next.md").exists()

    # Config should exist
    assert (isolated_project_env / "opencode.json").exists()

    # Plugin deps should exist
    assert (isolated_project_env / ".opencode" / "package.json").exists()


def test_opencode_json_has_safe_defaults(isolated_project_env: Path) -> None:
    """opencode.json should have minimal safe defaults (no aggressive permissions)."""
    from edison.cli.opencode.setup import main

    args = _parse_setup_args(isolated_project_env, "--yes", "--config")
    rc = main(args)
    assert rc == 0

    config_path = isolated_project_env / "opencode.json"
    content = json.loads(config_path.read_text(encoding="utf-8"))

    # Should not auto-approve dangerous operations
    permissions = content.get("permissions", {})
    assert permissions.get("auto_approve_everything") is not True
    # Should have sensible defaults or be empty/minimal
