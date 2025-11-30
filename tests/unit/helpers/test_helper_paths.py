"""Tests for test path helper utilities."""
from __future__ import annotations

from pathlib import Path
import pytest


def test_get_repo_root_exists():
    """Test that get_repo_root() can be imported and returns a valid Path."""
    from helpers.paths import get_repo_root

    repo_root = get_repo_root()

    # Should return a Path object
    assert isinstance(repo_root, Path)

    # Should be an absolute path
    assert repo_root.is_absolute()

    # Should have a .git directory
    assert (repo_root / ".git").exists()

    # Should be the outermost git root (not nested .edison)
    # If we're in a nested repo, the parent should NOT have .git
    # OR this should be the true project root
    parent = repo_root.parent
    if (parent / ".git").exists():
        # We found another .git above us, which means we should have returned that one
        pytest.fail(f"get_repo_root() returned {repo_root} but {parent} also has .git")


def test_get_repo_root_consistency():
    """Test that get_repo_root() returns consistent results."""
    from helpers.paths import get_repo_root

    root1 = get_repo_root()
    root2 = get_repo_root()

    assert root1 == root2


def test_get_core_root_exists():
    """Test that get_core_root() returns the .edison/core directory."""
    from helpers.paths import get_core_root

    core_root = get_core_root()

    # Should return a Path object
    assert isinstance(core_root, Path)

    # Should be an absolute path
    assert core_root.is_absolute()

    # Should end with .edison/core
    assert core_root.name == "core"
    assert core_root.parent.name == ".edison"


def test_get_core_root_relative_to_repo_root():
    """Test that get_core_root() is correctly derived from get_repo_root()."""
    from helpers.paths import get_repo_root, get_core_root

    repo_root = get_repo_root()
    core_root = get_core_root()

    # core_root should be repo_root / .edison / core
    expected = repo_root / ".edison" / "core"
    assert core_root == expected


def test_get_repo_root_matches_conftest_repo_root():
    """Test that get_repo_root() matches the REPO_ROOT from conftest.py."""
    from helpers.paths import get_repo_root
    from tests.conftest import REPO_ROOT

    # Should match the canonical REPO_ROOT
    assert get_repo_root() == REPO_ROOT


def test_get_repo_root_idempotent():
    """Test that calling get_repo_root() multiple times returns the same object."""
    from helpers.paths import get_repo_root

    # Call multiple times
    results = [get_repo_root() for _ in range(5)]

    # All should be equal
    assert all(r == results[0] for r in results)
