from __future__ import annotations

import importlib
from datetime import datetime, timezone
from pathlib import Path

import pytest

from helpers.io_utils import write_yaml


def _write_time_config(repo_root: Path) -> None:
    cfg_dir = repo_root / ".edison" / "config"

    # Write time.yaml
    time_cfg = {
        "time": {
            "iso8601": {
                "timespec": "seconds",
                "use_z_suffix": True,
                "strip_microseconds": True,
            }
        }
    }
    write_yaml(cfg_dir / "time.yaml", time_cfg)

    # Write timeouts.yaml
    timeouts_cfg = {
        "timeouts": {
            "default_seconds": 5.0,
            "git_operations_seconds": 5.0,
            "file_operations_seconds": 5.0,
        }
    }
    write_yaml(cfg_dir / "timeouts.yaml", timeouts_cfg)

    # Write file-locking.yaml
    file_locking_cfg = {
        "file_locking": {
            "timeout_seconds": 5.0,
            "poll_interval_seconds": 0.1,
        }
    }
    write_yaml(cfg_dir / "file-locking.yaml", file_locking_cfg)


@pytest.fixture()
def time_module(isolated_project_env: Path):
    _write_time_config(isolated_project_env)
    import edison.core.utils.time as t  # type: ignore

    importlib.reload(t)
    return t


def test_utc_now_returns_timezone_aware(time_module):
    now = time_module.utc_now()
    assert isinstance(now, datetime)
    assert now.tzinfo == timezone.utc
    assert now.microsecond == 0


def test_utc_timestamp_format(time_module):
    ts = time_module.utc_timestamp()
    assert ts.endswith("Z")
    # Should parse back into same second
    parsed = time_module.parse_iso8601(ts)
    assert parsed.tzinfo == timezone.utc
    assert parsed.microsecond == 0


def test_parse_iso8601_accepts_offset(time_module):
    dt = time_module.parse_iso8601("2030-01-01T12:00:00+00:00")
    assert dt.tzinfo == timezone.utc
    assert dt.hour == 12


def test_task_repository_timestamp_compliance(time_module):
    """Ensure TaskRepository uses canonical timestamp format (no microseconds)."""
    from edison.core.task.models import Task

    # Create a task and verify timestamps in metadata
    task = Task.create(
        task_id="test-task-ts",
        title="Title",
        state="todo"
    )

    # Canonical default in fixture is timespec='seconds', so no dots
    assert "." not in task.metadata.created_at, "Timestamps should be seconds precision per canonical default"
    assert "." not in task.metadata.updated_at

    # Verify utc_timestamp export matches canonical
    from edison.core.utils.time import utc_timestamp
    assert "." not in utc_timestamp()


def test_qa_scoring_timestamp_compliance(time_module):
    """Ensure qa/scoring.py uses canonical timestamp format."""
    from edison.core.qa import scoring
    
    session_id = "sess-ts-test"
    # Real call writing to file in isolated_project_env
    scoring.track_validation_score(session_id, "val", {}, 1.0)
    
    # Read back via scoring's public API
    entries = scoring.get_score_history(session_id)
    assert len(entries) == 1
    
    ts = entries[0]["timestamp"]
    assert "." not in ts, "QA timestamps should be canonical (seconds)"


@pytest.mark.skip(reason="Delegation module not implemented - future feature")
def test_delegation_timestamp_compliance(time_module):
    """Ensure delegation.py uses canonical timestamp format."""
    # This test is for a future delegation feature
    pass
