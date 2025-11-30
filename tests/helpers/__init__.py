"""Test helper modules for Edison test suite.

This module consolidates all test helper utilities into a clean, DRY structure:
- env: TestProjectDir and TestGitRepo for test environment setup
- env_setup: Environment variable setup helpers (setup_project_root, etc.)
- fixtures: Reusable fixture factories (setup_isolated_repo, etc.)
- assertions: Custom assertion helpers for file, JSON, and path validation
- command_runner: CLI command execution helpers
- delegation: Task delegation and routing helpers
- session: Session management helpers
- tdd_helpers: TDD validation utilities
- path_utils: Path resolution and finding utilities
- json_utils: JSON traversal utilities
- file_utils: File operation utilities
- markdown_utils: Markdown parsing utilities
- io_utils: I/O utilities for writing YAML, JSON, and config files
- cache_utils: Cache reset utilities for test isolation
"""
from __future__ import annotations

# Core test environment classes
from tests.helpers.env import TestProjectDir, TestGitRepo, create_tdd_evidence

# Environment setup helpers (DRY - use these instead of direct monkeypatch.setenv)
from tests.helpers.env_setup import (
    setup_project_root,
    setup_test_environment,
    setup_session_environment,
    setup_task_environment,
    clear_path_caches,
)

# Fixture factories (DRY - use these for common test setup patterns)
from tests.helpers.fixtures import (
    create_repo_with_git,
    create_edison_config_structure,
    create_project_structure,
    setup_isolated_repo,
    reload_config_modules,
    reset_and_reload_config_modules,
    create_task_file,
    create_qa_file,
    CONFIG_MODULES,
    SESSION_MODULES,
)

# I/O utilities for writing test files
from tests.helpers.io_utils import (
    write_yaml,
    write_json,
    write_config,
    write_text,
    format_round_dir,
    create_round_dir,
)

# Cache utilities for test isolation
from tests.helpers.cache_utils import reset_edison_caches, reset_session_store_cache

# Markdown utilities for creating test files
from tests.helpers.markdown_utils import create_markdown_task

# Export main classes and functions - these are the primary interfaces for tests
__all__ = [
    # Core environment
    "TestProjectDir",
    "TestGitRepo",
    "create_tdd_evidence",
    # Environment setup (USE THESE - DRY principle)
    "setup_project_root",
    "setup_test_environment",
    "setup_session_environment",
    "setup_task_environment",
    "clear_path_caches",
    # Fixture factories (USE THESE - DRY principle)
    "create_repo_with_git",
    "create_edison_config_structure",
    "create_project_structure",
    "setup_isolated_repo",
    "reload_config_modules",
    "reset_and_reload_config_modules",
    "create_task_file",
    "create_qa_file",
    "CONFIG_MODULES",
    "SESSION_MODULES",
    # I/O utilities
    "write_yaml",
    "write_json",
    "write_config",
    "write_text",
    "format_round_dir",
    "create_round_dir",
    # Cache utilities
    "reset_edison_caches",
    "reset_session_store_cache",
    # Markdown utilities
    "create_markdown_task",
]
