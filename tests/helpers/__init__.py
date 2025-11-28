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
"""
from __future__ import annotations

# Core test environment classes
from tests.helpers.env import TestProjectDir, TestGitRepo, create_tdd_evidence

# Export main classes - these are the primary interfaces for tests
__all__ = ["TestProjectDir", "TestGitRepo", "create_tdd_evidence"]
