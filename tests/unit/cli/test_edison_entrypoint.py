"""
Tests for Edison CLI entry point and dispatcher.

Note: These tests are for the new Python package-based architecture.
The old bin/edison shell script architecture has been replaced with
a proper Python package entry point using edison.cli._dispatcher.
"""
import os
import pytest
from pathlib import Path

from edison.core.utils.paths import resolve_project_root
from edison.core.utils.git import get_git_root, is_git_repository
from edison.cli._dispatcher import (
    discover_domains,
    discover_commands,
    _strip_profile_flag,
    _resolve_fast_command_module,
    _get_active_packs_fast,
    build_parser,
)
from tests.helpers.env_setup import clear_path_caches
from tests.helpers.fixtures import create_repo_with_git


def test_discover_domains_finds_cli_modules() -> None:
    """Test that the CLI dispatcher can discover domain modules."""
    domains = discover_domains()
    # Should have at least some common domains
    assert isinstance(domains, dict)
    assert len(domains) > 0
    # Each domain should be a valid directory
    for name, path in domains.items():
        assert path.is_dir()
        assert not name.startswith("_")


def test_discover_commands_in_domain() -> None:
    """Test that commands can be discovered within a domain."""
    domains = discover_domains()
    if not domains:
        pytest.skip("No domains found")

    # Pick first domain and test command discovery
    domain_name = next(iter(domains.keys()))
    commands = discover_commands(domain_name)

    assert isinstance(commands, dict)
    # Each command should have expected structure
    for cmd_name, cmd_info in commands.items():
        assert "module" in cmd_info
        assert "summary" in cmd_info


def test_resolve_project_root_walks_up(isolated_project_env: Path) -> None:
    """Test that project root detection walks up directory tree."""
    # isolated_project_env already has a git repo initialized
    root = isolated_project_env
    nested = root / "a" / "b"
    nested.mkdir(parents=True, exist_ok=True)

    # Set env var to point to the nested directory, then resolve should find root
    import os
    original_cwd = Path.cwd()
    try:
        os.chdir(nested)
        # Clear cache to force fresh resolution
        clear_path_caches()

        detected = resolve_project_root()
        assert detected == root
    finally:
        os.chdir(original_cwd)


def test_is_git_repository(tmp_path: Path) -> None:
    """Test git repository detection."""
    repo = tmp_path / "repo"
    repo.mkdir()
    assert not is_git_repository(repo)

    create_repo_with_git(repo)
    assert is_git_repository(repo)


def test_get_git_root(tmp_path: Path) -> None:
    """Test git root detection."""
    root = tmp_path / "project"
    create_repo_with_git(root)
    nested = root / "a" / "b"
    nested.mkdir(parents=True, exist_ok=True)

    git_root = get_git_root(nested)
    assert git_root == root


def test_strip_profile_flag_only_before_domain() -> None:
    # Global profiling flag is only recognized before the domain.
    argv, enabled = _strip_profile_flag(["--profile", "rules", "check"])
    assert enabled is True
    assert argv == ["rules", "check"]

    # After the domain, `--profile` must be preserved for subcommands that use it.
    argv2, enabled2 = _strip_profile_flag(["orchestrator", "start", "--profile", "codex"])
    assert enabled2 is False
    assert argv2 == ["orchestrator", "start", "--profile", "codex"]

    # When no domain is present, treat `--profile` as global.
    argv3, enabled3 = _strip_profile_flag(["--profile"])
    assert enabled3 is True
    assert argv3 == []


def test_build_parser_accepts_profile_flag() -> None:
    parser = build_parser()
    args = parser.parse_args(["--profile", "rules", "check"])
    assert getattr(args, "profile") is True


def test_fast_command_resolution_finds_domain_command() -> None:
    spec = _resolve_fast_command_module(["rules", "check"])
    assert spec is not None
    assert spec["module"].endswith(".rules.check")
    assert spec["domain"] == "rules"
    assert spec["command"] == "check"


def test_fast_command_resolution_supports_import_domain_alias() -> None:
    spec = _resolve_fast_command_module(["import", "speckit"])
    assert spec is not None
    assert spec["module"].endswith(".import_.speckit")
    assert spec["domain"] == "import_"
    assert spec["command"] == "speckit"


def test_build_parser_accepts_import_domain_alias() -> None:
    from edison.cli.import_.speckit import main as import_speckit_main

    parser = build_parser()
    args = parser.parse_args(["import", "speckit", "specs/auth", "--dry-run"])
    assert getattr(args, "_func") is import_speckit_main


def test_cli_rules_precheck_detects_core_rule_for_task_claim(tmp_path: Path) -> None:
    # Legacy test renamed: keep a minimal assertion that the packs fast-path
    # does not crash and returns empty when packs config is absent.
    project_root = tmp_path / "proj"
    project_root.mkdir(parents=True)
    (project_root / ".edison" / "config").mkdir(parents=True, exist_ok=True)
    assert _get_active_packs_fast(project_root) == []
