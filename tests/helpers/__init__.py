"""Test helper modules for Edison test suite.

This package provides test-focused helper functions that wrap canonical
Edison core modules with simplified APIs optimized for test scenarios.
"""

# Test environment classes
from .test_env import TestProjectDir, TestGitRepo, create_tdd_evidence

# Session helpers
from .session import (
    ensure_session,
    load_session,
    close_session,
    validate_session,
    transition_state,
    get_session_state,
    handle_timeout,
    check_recovery_auto_transition,
    create_worktree,
    create_session_database,
    drop_session_database,
    validation_transaction,
    recover_incomplete_validation_transactions,
)

# Delegation helpers
from .delegation import (
    get_role_mapping,
    map_role,
    route_task,
    delegate_task,
    aggregate_child_results,
)

# Command execution helpers
from .command_runner import (
    run_script,
    assert_command_success,
    assert_command_failure,
    assert_output_contains,
    assert_error_contains,
    assert_json_output,
)

# Custom assertions
from .assertions import (
    resolve_expected_path,
    read_file,
    assert_file_exists,
    assert_file_not_exists,
    assert_file_contains,
    assert_file_not_contains,
    assert_json_field,
    assert_json_has_field,
    assert_json_array_contains,
    assert_list_length,
    assert_list_contains,
    assert_list_not_contains,
    assert_directory_exists,
    assert_directory_empty,
    assert_directory_not_empty,
    assert_symlink_exists,
    assert_symlink_target,
)

# Git helpers
from .git_helpers import (
    git_init,
    git_commit,
    git_create_worktree,
    git_remove_worktree,
    git_list_worktrees,
    git_diff_files,
    git_current_branch,
    git_branch_exists,
    git_merge,
    git_status,
    git_log,
)

# TDD helpers
from .tdd_helpers import (
    _validate_refactor_cycle,
    _collect_commits_simple,
)

__all__ = [
    # Test environment
    "TestProjectDir",
    "TestGitRepo",
    "create_tdd_evidence",
    # Session operations
    "ensure_session",
    "load_session",
    "close_session",
    "validate_session",
    "transition_state",
    "get_session_state",
    "handle_timeout",
    "check_recovery_auto_transition",
    "create_worktree",
    "create_session_database",
    "drop_session_database",
    "validation_transaction",
    "recover_incomplete_validation_transactions",
    # Delegation
    "get_role_mapping",
    "map_role",
    "route_task",
    "delegate_task",
    "aggregate_child_results",
    # Command execution
    "run_script",
    "assert_command_success",
    "assert_command_failure",
    "assert_output_contains",
    "assert_error_contains",
    "assert_json_output",
    # Assertions
    "resolve_expected_path",
    "read_file",
    "assert_file_exists",
    "assert_file_not_exists",
    "assert_file_contains",
    "assert_file_not_contains",
    "assert_json_field",
    "assert_json_has_field",
    "assert_json_array_contains",
    "assert_list_length",
    "assert_list_contains",
    "assert_list_not_contains",
    "assert_directory_exists",
    "assert_directory_empty",
    "assert_directory_not_empty",
    "assert_symlink_exists",
    "assert_symlink_target",
    # Git operations
    "git_init",
    "git_commit",
    "git_create_worktree",
    "git_remove_worktree",
    "git_list_worktrees",
    "git_diff_files",
    "git_current_branch",
    "git_branch_exists",
    "git_merge",
    "git_status",
    "git_log",
    # TDD operations
    "_validate_refactor_cycle",
    "_collect_commits_simple",
]
