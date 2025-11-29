"""Test helper modules for Edison test suite.

This module consolidates all test helper utilities into a clean, DRY structure:
- env: TestProjectDir and TestGitRepo for test environment setup
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
"""
from __future__ import annotations

# Core test environment classes
from tests.helpers.env import TestProjectDir, TestGitRepo, create_tdd_evidence

# I/O utilities for writing test files
from tests.helpers.io_utils import (
    write_yaml,
    write_json,
    write_config,
    write_text,
    format_round_dir,
    create_round_dir,
)

# Export main classes and functions - these are the primary interfaces for tests
__all__ = [
    # Core environment
    "TestProjectDir",
    "TestGitRepo",
    "create_tdd_evidence",
    # I/O utilities
    "write_yaml",
    "write_json",
    "write_config",
    "write_text",
    "format_round_dir",
    "create_round_dir",
]
