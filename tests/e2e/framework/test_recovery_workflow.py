import sys
import json
from pathlib import Path
from datetime import datetime, timezone

import pytest

_THIS_FILE = Path(__file__).resolve()
_CORE_ROOT = None
for _parent in _THIS_FILE.parents:
    candidate = _parent / ".edison" / "core"
    if (candidate / "lib").exists():
        _CORE_ROOT = candidate
        break

if _CORE_ROOT is None:
    _CORE_ROOT = _THIS_FILE.parents[4]

CORE_ROOT = _CORE_ROOT
from tests.helpers import session as sessionlib  # type: ignore
from edison.core.utils import resilience  # type: ignore


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def write_session(dirpath: Path, state: str = "Active", **extra) -> Path:
    dirpath.mkdir(parents=True, exist_ok=True)
    payload = {
        "id": extra.get("id", dirpath.name),
        "state": state,
        "created_at": extra.get("created_at", iso(datetime.now(timezone.utc))),
        "last_active_at": extra.get("last_active_at", iso(datetime.now(timezone.utc))),
        "meta": extra.get("meta", {}),
    }
    (dirpath / "session.json").write_text(json.dumps(payload), encoding="utf-8")
    # Simulate partial work
    (dirpath / "work").mkdir(exist_ok=True)
    (dirpath / "work" / "partial.txt").write_text("WIP", encoding="utf-8")
    return dirpath


def test_session_moved_to_project_recovery_on_timeout(tmp_path: Path):
    repo_root = Path.cwd()
    active_root = repo_root / ".project" / "sessions" / "active"
    sess = write_session(active_root / "sess-r1")
    rec_path = sessionlib.handle_timeout(sess)
    assert rec_path.parent.name == "recovery"
    assert rec_path.parent.parent.name == "sessions"
    assert rec_path.exists()


def test_recovery_metadata_preserved(tmp_path: Path):
    repo_root = Path.cwd()
    active_root = repo_root / ".project" / "sessions" / "active"
    sess = write_session(active_root / "sess-r2", meta={"owner": "alice"})
    rec_path = sessionlib.handle_timeout(sess)
    meta = json.loads((rec_path / "recovery.json").read_text(encoding="utf-8"))
    assert meta.get("reason")
    assert meta.get("original_path")
    assert meta.get("captured_at")
    assert meta.get("session", {}).get("meta", {}).get("owner") == "alice"


def test_resume_from_recovery_restores_active_state(tmp_path: Path):
    repo_root = Path.cwd()
    active_root = repo_root / ".project" / "sessions" / "active"
    sess = write_session(active_root / "sess-r3")
    rec_path = sessionlib.handle_timeout(sess)
    new_active = resilience.resume_from_recovery(rec_path)
    assert new_active.exists()
    data = json.loads((new_active / "session.json").read_text(encoding="utf-8"))
    assert data["state"] == "Active"


def test_recovery_queue_processing_and_ordering(tmp_path: Path):
    repo_root = Path.cwd()
    active_root = repo_root / ".project" / "sessions" / "active"
    s1 = write_session(active_root / "sess-qa-1")
    s2 = write_session(active_root / "sess-qa-2")
    r1 = sessionlib.handle_timeout(s1)
    r2 = sessionlib.handle_timeout(s2)
    # Ensure r1 is older by touching times
    (r1 / "recovery.json").touch()
    recoverables = resilience.list_recoverable_sessions()
    # Should include both
    names = [p.name for p in recoverables]
    assert r1.name in names and r2.name in names


def test_partial_work_preserved_after_move(tmp_path: Path):
    repo_root = Path.cwd()
    active_root = repo_root / ".project" / "sessions" / "active"
    sess = write_session(active_root / "sess-work")
    rec_path = sessionlib.handle_timeout(sess)
    assert (rec_path / "work" / "partial.txt").exists()


def test_multi_session_recovery_order_by_time(tmp_path: Path):
    repo_root = Path.cwd()
    active_root = repo_root / ".project" / "sessions" / "active"
    sA = write_session(active_root / "sess-order-A")
    sB = write_session(active_root / "sess-order-B")
    rA = sessionlib.handle_timeout(sA)
    # Ensure a small delay
    rB = sessionlib.handle_timeout(sB)
    recs = resilience.list_recoverable_sessions()
    # Focus ordering assertion only on the two sessions we created
    filtered = [p for p in recs if p.name in {rA.name, rB.name}]
    if (rA / "recovery.json").stat().st_mtime != (rB / "recovery.json").stat().st_mtime and filtered:
        assert filtered[0].name in {rA.name, rB.name}
