"""Pytest configuration for E2E session tests.

CRITICAL: All session tests MUST run in isolated environments to prevent
session persistence between tests causing failures.

This conftest ensures:
1. Each test gets a fresh isolated project directory
2. Sessions are created in tmp_path, not real .project/
3. Session state is completely isolated between tests
"""
from __future__ import annotations

import pytest
from pathlib import Path


@pytest.fixture(autouse=True)
def _isolated_session_env(isolated_project_env):
    """Ensure all session tests run in isolated environment.

    This autouse fixture ensures that EVERY test in this directory
    automatically gets:
    - AGENTS_PROJECT_ROOT set to tmp_path
    - Fresh .project/ directory structure
    - Complete isolation from real project sessions

    This prevents session persistence between tests which was causing
    ~39 test failures with "Session already exists" and state contamination.
    """
    # The isolated_project_env fixture does all the work
    # We just need to ensure it's applied to all tests via autouse
    yield isolated_project_env
