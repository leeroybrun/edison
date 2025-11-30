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
from edison.cli._dispatcher import discover_domains, discover_commands
from tests.helpers.env_setup import clear_path_caches


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

    (repo / ".git").mkdir()
    assert is_git_repository(repo)


def test_get_git_root(tmp_path: Path) -> None:
    """Test git root detection."""
    root = tmp_path / "project"
    (root / ".git").mkdir(parents=True, exist_ok=True)
    nested = root / "a" / "b"
    nested.mkdir(parents=True, exist_ok=True)

    git_root = get_git_root(nested)
    assert git_root == root
