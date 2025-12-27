"""Test that worktree module is properly split into sub-modules.

This test validates the split structure following TDD principles:
1. Git operations are now centralized in edison.core.utils.git.worktree
2. Session-specific worktree operations remain in edison.core.session.worktree
3. All existing functionality must remain accessible via the appropriate public API
"""
import pytest
from pathlib import Path
import inspect


def test_worktree_package_structure_exists():
    """Verify worktree package directory structure exists."""
    from edison.core.session import worktree

    # Get the worktree module's file location
    worktree_path = Path(worktree.__file__).parent

    # Verify it's a package (has __init__.py)
    assert (worktree_path / "__init__.py").exists(), "worktree must be a package with __init__.py"

    # Verify sub-modules exist
    assert (worktree_path / "manager").is_dir(), "manager must be a package directory"
    assert (worktree_path / "manager" / "__init__.py").exists(), "manager must be a package with __init__.py"
    assert (worktree_path / "cleanup.py").exists(), "cleanup.py module must exist"
    assert (worktree_path / "config_helpers.py").exists(), "config_helpers.py module must exist"


def test_worktree_module_sizes():
    """Verify each module is under 250 LOC."""
    from edison.core.session import worktree

    worktree_path = Path(worktree.__file__).parent

    modules = [
        "cleanup.py",
        "config_helpers.py",
        "__init__.py",
        # manager is a package; keep each submodule small
        "manager/__init__.py",
        "manager/api.py",
        "manager/create.py",
        "manager/env.py",
        "manager/meta.py",
        "manager/post_install.py",
        "manager/refs.py",
    ]

    for module_name in modules:
        module_file = worktree_path / module_name
        assert module_file.exists(), f"{module_name} must exist"

        # Count lines
        with open(module_file) as f:
            lines = f.readlines()
            # Don't count blank lines or comments for LOC
            loc = sum(1 for line in lines if line.strip() and not line.strip().startswith("#"))

        assert loc < 250, f"{module_name} must be < 250 LOC, got {loc}"


def test_session_worktree_public_api_exports():
    """Verify all public functions are exported from session.worktree.__init__.py."""
    from edison.core.session import worktree

    # These are the public functions that must be accessible from session.worktree
    required_exports = [
        # Manager functions
        "create_worktree",
        "restore_worktree",
        "resolve_worktree_target",
        "ensure_worktree_materialized",
        "update_worktree_env",

        # Git operations (re-exported from utils.git.worktree)
        "list_worktrees",
        "list_worktrees_porcelain",
        "is_worktree_registered",
        "worktree_health_check",
        "check_worktree_health",
        "get_existing_worktree_path",

        # Cleanup functions
        "archive_worktree",
        "cleanup_worktree",
        "remove_worktree",
        "prune_worktrees",
        "list_archived_worktrees_sorted",
    ]

    for func_name in required_exports:
        assert hasattr(worktree, func_name), f"worktree.{func_name} must be accessible"
        func = getattr(worktree, func_name)
        assert callable(func), f"worktree.{func_name} must be callable"


def test_centralized_git_worktree_utilities():
    """Verify git worktree utilities are in utils.git.worktree."""
    from edison.core.utils.git import worktree as git_worktree

    # These are the centralized git operations
    required_exports = [
        "list_worktrees",
        "check_worktree_health",
        "get_existing_worktree_path",
        "is_worktree_registered",
        "get_worktree_info",
        "get_worktree_parent",
        "is_worktree",
    ]

    for func_name in required_exports:
        assert hasattr(git_worktree, func_name), f"git.worktree.{func_name} must be accessible"
        func = getattr(git_worktree, func_name)
        assert callable(func), f"git.worktree.{func_name} must be callable"


def test_manager_module_contains_creation_logic():
    """Verify manager.py contains worktree creation and restoration."""
    from edison.core.session.worktree import manager

    assert hasattr(manager, "create_worktree")
    assert hasattr(manager, "restore_worktree")
    assert hasattr(manager, "resolve_worktree_target")
    assert hasattr(manager, "ensure_worktree_materialized")
    assert hasattr(manager, "update_worktree_env")


def test_cleanup_module_contains_cleanup_operations():
    """Verify cleanup.py contains cleanup and archival operations."""
    from edison.core.session.worktree import cleanup

    assert hasattr(cleanup, "archive_worktree")
    assert hasattr(cleanup, "cleanup_worktree")
    assert hasattr(cleanup, "remove_worktree")
    assert hasattr(cleanup, "prune_worktrees")
    assert hasattr(cleanup, "list_archived_worktrees_sorted")


def test_no_code_duplication():
    """Verify no duplicate function definitions across modules."""
    from edison.core.session.worktree import manager, cleanup
    from edison.core.session.worktree import config_helpers

    # Only check functions defined in each module (not imported ones)
    def get_module_funcs(module):
        return {
            name for name, obj in inspect.getmembers(module)
            if inspect.isfunction(obj)
            and not name.startswith('_')
            and obj.__module__ == module.__name__
        }

    manager_funcs = get_module_funcs(manager)
    cleanup_funcs = get_module_funcs(cleanup)
    config_funcs = get_module_funcs(config_helpers)

    # No overlap between modules
    assert len(manager_funcs & cleanup_funcs) == 0, f"manager and cleanup should not share functions: {manager_funcs & cleanup_funcs}"
    assert len(manager_funcs & config_funcs) == 0, f"manager and config_helpers should not share functions: {manager_funcs & config_funcs}"
    assert len(cleanup_funcs & config_funcs) == 0, f"cleanup and config_helpers should not share functions: {cleanup_funcs & config_funcs}"


def test_imports_work_from_package():
    """Test that imports work both ways."""
    # From package root
    from edison.core.session.worktree import create_worktree
    assert callable(create_worktree)

    # From sub-module
    from edison.core.session.worktree.manager import create_worktree as create_worktree_direct
    assert callable(create_worktree_direct)

    # They should be the same function
    assert create_worktree is create_worktree_direct


def test_git_utilities_accessible_from_utils():
    """Test that git utilities are accessible from utils.git."""
    # Centralized git worktree utilities
    from edison.core.utils.git import list_worktrees, check_worktree_health
    assert callable(list_worktrees)
    assert callable(check_worktree_health)
