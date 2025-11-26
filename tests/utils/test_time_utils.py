from __future__ import annotations

import importlib
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml


def _write_time_config(repo_root: Path) -> None:
    cfg = {
        "time": {
            "iso8601": {
                "timespec": "seconds",
                "use_z_suffix": True,
                "strip_microseconds": True,
            }
        },
        "subprocess_timeouts": {
            "default": 5.0,
            "git_operations": 5.0,
            "file_operations": 5.0,
        },
        "file_locking": {
            "mode": "portalocker",
            "timeout_seconds": 5.0,
            "poll_interval_seconds": 0.1,
        },
    }
    cfg_dir = repo_root / ".edison" / "core" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_dir.joinpath("defaults.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")


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


def test_task_io_timestamp_compliance(time_module):
    """Ensure task/io.py uses canonical timestamp format (no microseconds)."""
    from edison.core.task import io as task_io

    # This currently uses local _now_iso which includes microseconds (failing)
    record = task_io.create_task_record("test-task-ts", "Title")
    
    # Canonical default in fixture is timespec='seconds', so no dots
    assert "." not in record["created_at"], "Timestamps should be seconds precision per canonical default"
    assert "." not in record["updated_at"]
    
    # Verify utc_timestamp export matches canonical
    assert "." not in task_io.utc_timestamp()


def test_qa_scoring_timestamp_compliance(time_module):
    """Ensure qa/scoring.py uses canonical timestamp format."""
    from edison.core.qa import scoring
    from edison.core.qa import store
    
    session_id = "sess-ts-test"
    # Real call writing to file in isolated_project_env
    scoring.track_validation_score(session_id, "val", {}, 1.0)
    
    # Read back from real file
    history_file = store.score_history_file(session_id)
    assert history_file.exists(), "Score history file should be created"
    
    entries = list(store.read_jsonl(history_file))
    assert len(entries) == 1
    
    ts = entries[0]["timestamp"]
    assert "." not in ts, "QA timestamps should be canonical (seconds)"


def test_delegation_timestamp_compliance(time_module):
    """Ensure delegation.py uses canonical timestamp format."""
    from edison.core.composition import delegation
    from edison.core.task import load_task_record
    
    # Real call creating task in isolated_project_env
    child_id = delegation.delegate_task("desc", "agent")
    
    # Read back real task record
    record = load_task_record(child_id)
    
    assert "delegated_at" in record
    ts = record["delegated_at"]
    assert "." not in ts, "Delegation timestamps should be canonical (seconds)"
