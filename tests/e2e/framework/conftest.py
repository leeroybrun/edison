from __future__ import annotations

from pathlib import Path
import pytest

# Import centralized config loader (SINGLE source of truth)
# sys.path is already set up by tests/conftest.py
from config import load_states as load_test_states


@pytest.fixture
def ensure_project_dirs(tmp_path: Path) -> Path:
    """Ensure basic Edison project directories exist for file-based tests.

    This fixture creates directories in an ISOLATED tmp_path to prevent
    test interference and artifacts in the working directory.

    CRITICAL: This fixture is NOT autouse - tests must explicitly request it
    to get isolated project structure.

    Returns:
        Path: The isolated .project root directory
    """
    states_config = load_test_states()

    root = tmp_path / ".project"

    # Create QA directories
    qa_unique_dirs = states_config.get("qa", {}).get("unique_dirs", [])
    for dir_name in qa_unique_dirs:
        (root / "qa" / dir_name).mkdir(parents=True, exist_ok=True)

    # Create additional QA paths
    qa_additional = states_config.get("additional_paths", {}).get("qa", [])
    for rel_path in qa_additional:
        (root / rel_path).mkdir(parents=True, exist_ok=True)

    # Create task directories
    task_unique_dirs = states_config.get("task", {}).get("unique_dirs", [])
    for dir_name in task_unique_dirs:
        (root / "tasks" / dir_name).mkdir(parents=True, exist_ok=True)

    # Create session directories
    session_unique_dirs = states_config.get("session", {}).get("unique_dirs", [])
    for dir_name in session_unique_dirs:
        (root / "sessions" / dir_name).mkdir(parents=True, exist_ok=True)

    return root
