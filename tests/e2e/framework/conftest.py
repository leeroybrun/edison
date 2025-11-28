from __future__ import annotations

import sys
from pathlib import Path
import pytest
import yaml

# Add tests directory to path so tests can import from helpers.*
TESTS_ROOT = Path(__file__).resolve().parent.parent.parent
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))


def _load_test_states() -> dict:
    """Load canonical state definitions from tests/config/states.yaml."""
    states_file = TESTS_ROOT / "config" / "states.yaml"
    if not states_file.exists():
        # Fallback to minimal defaults if config not found
        return {
            "session": {
                "unique_dirs": ["wip", "done", "validated", "recovery"]
            },
            "task": {
                "unique_dirs": ["todo"]
            },
            "qa": {
                "unique_dirs": ["waiting", "todo", "wip", "done", "validated"]
            },
            "additional_paths": {
                "qa": []
            }
        }
    with open(states_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


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
    states_config = _load_test_states()

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
