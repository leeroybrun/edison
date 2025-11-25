"""Pytest config for migrated QA tests.

Adds helper import paths and provides minimal fixtures used by the tests.
"""
from __future__ import annotations

import sys
from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent
# Repo root: qa/ → tests/ → core/ → .edison/ → <repo>
REPO_ROOT = HERE.parents[3]

# Ensure our shimmed helpers package is importable: add its parent directory

# Also expose the legacy helpers directory for any direct imports
legacy_helpers_dir = REPO_ROOT / ".agents" / "scripts" / "tests" / "e2e" / "helpers"
if legacy_helpers_dir.exists() and str(legacy_helpers_dir) not in sys.path:
    sys.path.append(str(legacy_helpers_dir))

from helpers.test_env import TestProjectDir  # type: ignore
import json


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def test_project_dir(tmp_path: Path, repo_root: Path) -> TestProjectDir:  # type: ignore[override]
    proj = TestProjectDir(tmp_path, repo_root)
    # Normalize session JSON shape expected by edison sessionlib (maps not arrays)
    _orig_create_session = proj.create_session
    def _create_session(session_id: str, state: str = "wip", **kwargs):
        p = _orig_create_session(session_id, state=state, **kwargs)
        try:
            data = json.loads(p.read_text())
            # Ensure meta block exists
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
    # Attach helper for tests
    proj.create_session = _create_session  # type: ignore[attr-defined]
    return proj
