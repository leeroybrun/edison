"""Local pytest fixtures for task tests.

Most fixtures are now consolidated in tests/conftest.py.
This file ensures tests directory is in sys.path for helper imports.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add tests directory to path so tests can import from helpers.*
TESTS_ROOT = Path(__file__).resolve().parent.parent
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))

# All common fixtures (repo_root, test_project_dir, project_env) are now
# provided by tests/conftest.py to avoid duplication across test directories.
