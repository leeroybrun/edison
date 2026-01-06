"""Base classes and fixtures for E2E tests.

This module provides shared setup code for E2E tests to eliminate duplication
across test files. All directory structures and state configurations are loaded
from YAML files to ensure NO hardcoded values.

Usage (pytest fixture):
    @pytest.fixture
    def my_test_env(e2e_project_env: dict):
        # Use the environment
        root = env['root']
        ...

Usage (unittest.TestCase):
    class MyE2ETest(E2ETestCase):
        def test_something(self):
            # self.tmp and self.env are available
            ...
"""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Generator, Dict, Any

import pytest

from tests.config import load_states, load_paths
from edison.data import get_data_path
from tests.helpers.paths import get_repo_root


# Load from configuration instead of hardcoding
STATES = load_states()
PATHS = load_paths()


def create_project_structure(root: Path) -> None:
    """Create standard Edison project directory structure.

    Creates all state directories for tasks, qa, and sessions based on
    configuration from tests/config/states.yaml.

    Args:
        root: Project root directory (where .project/ will be created)
    """
    project_root = root / ".project"

    # Create task state directories
    for state in STATES['task']['unique_dirs']:
        (project_root / "tasks" / state).mkdir(parents=True, exist_ok=True)

    # Create QA state directories
    for state in STATES['qa']['unique_dirs']:
        (project_root / "qa" / state).mkdir(parents=True, exist_ok=True)

    # Create session state directories
    for state in STATES['session']['unique_dirs']:
        (project_root / "sessions" / state).mkdir(parents=True, exist_ok=True)

    # Create additional QA paths
    if 'additional_paths' in STATES and 'qa' in STATES['additional_paths']:
        for path in STATES['additional_paths']['qa']:
            (project_root / path).mkdir(parents=True, exist_ok=True)


def copy_templates(root: Path) -> None:
    """Copy required template files to test environment.

    Args:
        root: Project root directory
    """
    repo_root = get_repo_root()

    # Copy session template
    session_template_dest = root / ".edison" / "sessions" / "TEMPLATE.json"
    session_template_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        get_data_path("templates", "session.template.json"),
        session_template_dest,
    )

    # Copy QA template if it exists in real project
    qa_template_src = repo_root / ".project" / "qa" / "TEMPLATE.md"
    if qa_template_src.exists():
        qa_template_dest = root / ".project" / "qa" / "TEMPLATE.md"
        shutil.copyfile(qa_template_src, qa_template_dest)

    # Copy task template if it exists in real project
    task_template_src = repo_root / ".project" / "tasks" / "TEMPLATE.md"
    if task_template_src.exists():
        task_template_dest = root / ".project" / "tasks" / "TEMPLATE.md"
        shutil.copyfile(task_template_src, task_template_dest)

    # Provide minimal CI commands so evidence capture and session-complete flows
    # are deterministic in E2E tests (core defaults are placeholders).
    ci_cfg_path = root / ".edison" / "config" / "ci.yaml"
    ci_cfg_path.parent.mkdir(parents=True, exist_ok=True)
    ci_cfg_path.write_text(
        "ci:\n"
        "  commands:\n"
        "    type-check: \"echo type-check\"\n"
        "    lint: \"echo lint\"\n"
        "    test: \"echo test\"\n"
        "    test-full: \"echo test-full\"\n"
        "    build: \"echo build\"\n",
        encoding="utf-8",
    )


def setup_base_environment(root: Path, owner: str = "test-user") -> Dict[str, str]:
    """Set up base environment variables for E2E tests.

    Args:
        root: Project root directory
        owner: Owner identifier for the test session

    Returns:
        Dictionary of environment variables
    """
    env = os.environ.copy()
    # Tests must be deterministic: developer machines may set this override to a
    # different repo. Ensure E2E processes always resolve `.edison/` from the
    # test project root (`AGENTS_PROJECT_ROOT`).
    env.pop("EDISON_paths__project_config_dir", None)
    env.update({
        "AGENTS_PROJECT_ROOT": str(root),
        "AGENTS_OWNER": owner,
        "PYTHONUNBUFFERED": "1",
    })
    return env


@pytest.fixture
def e2e_project_env(tmp_path: Path) -> Generator[Dict[str, Any], None, None]:
    """Create isolated E2E project environment with standard structure.

    This fixture provides a complete test environment including:
    - Standard directory structure (.project/tasks, qa, sessions)
    - All state directories loaded from configuration
    - Template files copied from real project
    - Environment variables configured

    Yields:
        Dictionary with keys:
            - root: Project root path
            - project_root: .project directory path
            - env: Environment variables dict
            - tasks_root: .project/tasks path
            - qa_root: .project/qa path
            - sessions_root: .project/sessions path
    """
    # Create project structure
    create_project_structure(tmp_path)

    # Copy templates
    copy_templates(tmp_path)

    # Set up environment
    env = setup_base_environment(tmp_path)

    # Build environment data structure
    project_root = tmp_path / ".project"
    env_data = {
        "root": tmp_path,
        "project_root": project_root,
        "tasks_root": project_root / "tasks",
        "qa_root": project_root / "qa",
        "sessions_root": project_root / "sessions",
        "env": env,
    }

    yield env_data

    # Cleanup happens automatically with tmp_path


class E2ETestCase(unittest.TestCase):
    """Base class for E2E tests with standard setup.

    Provides:
    - self.tmp: Temporary project root directory
    - self.env: Environment variables dictionary
    - self.project_root: .project directory path
    - Automatic cleanup via addCleanup

    Usage:
        class MyE2ETest(E2ETestCase):
            def test_something(self):
                # Use self.tmp, self.env, self.project_root
                ...
    """

    def setUp(self) -> None:
        """Set up isolated test environment for each test."""
        # Create temporary directory
        self.tmp = Path(tempfile.mkdtemp(prefix="e2e-test-"))
        self.addCleanup(lambda: shutil.rmtree(self.tmp, ignore_errors=True))

        # Create project structure
        create_project_structure(self.tmp)

        # Copy templates
        copy_templates(self.tmp)

        # Set up environment
        self.env = setup_base_environment(self.tmp)

        # Store commonly used paths
        self.project_root = self.tmp / ".project"
        self.tasks_root = self.project_root / "tasks"
        self.qa_root = self.project_root / "qa"
        self.sessions_root = self.project_root / "sessions"


__all__ = [
    'create_project_structure',
    'copy_templates',
    'setup_base_environment',
    'e2e_project_env',
    'E2ETestCase',
    'STATES',
    'PATHS',
]
