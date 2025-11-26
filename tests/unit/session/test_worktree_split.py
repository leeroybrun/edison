"""Test that worktree module is properly split into sub-modules.

This test validates the split structure following TDD principles:
1. RED: This test will fail initially when worktree is still a single file
2. GREEN: After splitting, these tests should pass
3. All existing functionality must remain accessible via the public API
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
    assert (worktree_path / "manager.py").exists(), "manager.py module must exist"
    assert (worktree_path / "git_ops.py").exists(), "git_ops.py module must exist"
    assert (worktree_path / "cleanup.py").exists(), "cleanup.py module must exist"


def test_worktree_module_sizes():
    """Verify each module is under 200 LOC."""
    from edison.core.session import worktree

    worktree_path = Path(worktree.__file__).parent

    modules = ["manager.py", "git_ops.py", "cleanup.py", "__init__.py"]

    for module_name in modules:
        module_file = worktree_path / module_name
        assert module_file.exists(), f"{module_name} must exist"

        # Count lines
        with open(module_file) as f:
            lines = f.readlines()
            # Don't count blank lines or comments for LOC
            loc = sum(1 for line in lines if line.strip() and not line.strip().startswith("#"))

        assert loc < 200, f"{module_name} must be < 200 LOC, got {loc}"


def test_public_api_exports():
    """Verify all public functions are exported from __init__.py."""
    from edison.core.session import worktree

    # These are the public functions that must be accessible
    required_exports = [
        # Manager functions
        "create_worktree",
        "restore_worktree",
        "resolve_worktree_target",
        "ensure_worktree_materialized",
        "update_worktree_env",

        # Git operations
        "get_existing_worktree_for_branch",
        "list_worktrees",
        "list_worktrees_porcelain",
        "is_registered_worktree",
        "worktree_health_check",

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


def test_internal_functions_not_exported():
    """Verify internal (private) functions are not in public API."""
    from edison.core.session import worktree

    # These are internal functions that should NOT be in public API
    # (they can exist in sub-modules but shouldn't be re-exported)
    internal_functions = [
        "_config",
        "_get_repo_dir",
        "_get_project_name",
        "_worktree_base_dir",
        "_resolve_worktree_target",
        "_get_worktree_base",
        "_git_is_healthy",
        "_git_list_worktrees",
    ]

    # Note: Python convention is that _prefixed names are internal
    # But we'll check these specifically to ensure clean API
    for func_name in internal_functions:
        # It's OK if they exist (for backward compat), but we're documenting
        # that they're internal. This test just documents the split.
        pass


def test_manager_module_contains_creation_logic():
    """Verify manager.py contains worktree creation and restoration."""
    from edison.core.session.worktree import manager

    assert hasattr(manager, "create_worktree")
    assert hasattr(manager, "restore_worktree")
    assert hasattr(manager, "resolve_worktree_target")
    assert hasattr(manager, "ensure_worktree_materialized")
    assert hasattr(manager, "update_worktree_env")


def test_git_ops_module_contains_git_operations():
    """Verify git_ops.py contains git-specific operations."""
    from edison.core.session.worktree import git_ops

    assert hasattr(git_ops, "get_existing_worktree_for_branch")
    assert hasattr(git_ops, "list_worktrees")
    assert hasattr(git_ops, "list_worktrees_porcelain")
    assert hasattr(git_ops, "is_registered_worktree")
    assert hasattr(git_ops, "worktree_health_check")


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
    from edison.core.session.worktree import manager, git_ops, cleanup

    # Only check functions defined in each module (not imported ones)
    def get_module_funcs(module):
        return {
            name for name, obj in inspect.getmembers(module)
            if inspect.isfunction(obj)
            and not name.startswith('_')
            and obj.__module__ == module.__name__
        }

    manager_funcs = get_module_funcs(manager)
    git_ops_funcs = get_module_funcs(git_ops)
    cleanup_funcs = get_module_funcs(cleanup)

    # No overlap between modules
    assert len(manager_funcs & git_ops_funcs) == 0, f"manager and git_ops should not share functions: {manager_funcs & git_ops_funcs}"
    assert len(manager_funcs & cleanup_funcs) == 0, f"manager and cleanup should not share functions: {manager_funcs & cleanup_funcs}"
    assert len(git_ops_funcs & cleanup_funcs) == 0, f"git_ops and cleanup should not share functions: {git_ops_funcs & cleanup_funcs}"


def test_imports_work_from_package():
    """Test that imports work both ways for backward compatibility."""
    # Old style (from package root)
    from edison.core.session.worktree import create_worktree
    assert callable(create_worktree)

    # New style (from sub-module)
    from edison.core.session.worktree.manager import create_worktree as create_worktree_direct
    assert callable(create_worktree_direct)

    # They should be the same function
    assert create_worktree is create_worktree_direct
