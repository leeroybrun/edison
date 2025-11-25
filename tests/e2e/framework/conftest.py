from __future__ import annotations

from pathlib import Path
import pytest


@pytest.fixture(autouse=True)
def ensure_project_dirs() -> None:
    """Ensure basic Edison project directories exist for file-based tests.

    This fixture is intentionally non-destructive: it only creates directories
    if missing and does not purge content.
    """
    root = Path('.project')
    for sub in [
        'qa/waiting', 'qa/todo', 'qa/wip', 'qa/done', 'qa/validated',
        'tasks/todo',
        'sessions/active', 'sessions/closing', 'sessions/validated', 'sessions/recovery',
    ]:
        (root / sub).mkdir(parents=True, exist_ok=True)

