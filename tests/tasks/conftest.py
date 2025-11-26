"""Local pytest fixtures to run migrated task tests in isolation.

Bridges to the E2E helpers while avoiding dependency on the original
e2e/conftest.py package structure.
"""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

# Resolve repository root and tests directory
REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_ROOT = Path(__file__).resolve().parent.parent

# Add tests directory to path so tests can import from helpers.*
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))

from helpers.env import TestProjectDir


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def test_project_dir(tmp_path: Path, repo_root: Path) -> TestProjectDir:
    proj = TestProjectDir(tmp_path, repo_root)
    # Ensure sessions created during task tests have expected keys
    _orig_create_session = proj.create_session
    def _create_session(session_id: str, state: str = "wip", **kwargs):
        p = _orig_create_session(session_id, state=state, **kwargs)
        try:
            import json
            data = json.loads(p.read_text())
            if not isinstance(data.get("meta"), dict):
                from datetime import datetime
                now = datetime.utcnow().isoformat() + "Z"
                data["meta"] = {
                    "sessionId": session_id,
                    "createdAt": now,
                    "lastActive": now,
                }
            if isinstance(data.get("qa"), list):
                data["qa"] = {}
            if isinstance(data.get("tasks"), list):
                data["tasks"] = {}
            if not isinstance(data.get("activityLog"), list):
                data["activityLog"] = []
            p.write_text(json.dumps(data, indent=2))
        except Exception:
            pass
        return p
    proj.create_session = _create_session
    return proj


@pytest.fixture
def project_env(tmp_path, monkeypatch):
    """Isolated project environment for tests - prevents .edison/.project creation."""
    monkeypatch.setenv('AGENTS_PROJECT_ROOT', str(tmp_path))
    monkeypatch.chdir(tmp_path)

    # Create structure
    (tmp_path / ".git").mkdir()
    (tmp_path / ".project").mkdir()
    (tmp_path / ".project" / "qa").mkdir()
    (tmp_path / ".project" / "sessions").mkdir()
    (tmp_path / ".agents").mkdir()
    (tmp_path / ".edison").mkdir()

    yield tmp_path
