from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from edison.core.utils.subprocess import run_with_timeout 
def _repo_root() -> Path:
    cur = Path(__file__).resolve()
    candidate: Path | None = None
    while cur != cur.parent:
        if (cur / ".git").exists():
            candidate = cur
        cur = cur.parent
    if candidate is None:
        raise RuntimeError("git root not found")
    if candidate.name == ".edison" and (candidate.parent / ".git").exists():
        return candidate.parent
    return candidate


def test_claim_task_with_lock_allows_single_claim(tmp_path: Path) -> None:
    """Single process claim should succeed and stamp session_id."""
    project_root = tmp_path
    repo_root = _repo_root()
    env = os.environ.copy()
    env.update(
        {
            "AGENTS_PROJECT_ROOT": str(project_root),
            "REPO_ROOT": str(repo_root),
        }
    )

    code = r"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

repo_root = Path(os.environ["REPO_ROOT"])
core_root = repo_root / ".edison" / "core"
from edison.core import task  # type: ignore  # noqa: E402

task_id = "t-lock-single"
task.create_task_record("demo", task_id=task_id)  # type: ignore[attr-defined]
ok = task.claim_task_with_lock(task_id, "sess-single", timeout=5)  # type: ignore[attr-defined]
meta_path = (task.ROOT / ".project" / "tasks" / "meta" / "task-t-lock-single.json").resolve()  # type: ignore[attr-defined]
meta = json.loads(meta_path.read_text())
print(json.dumps({"ok": ok, "session_id": meta.get("session_id")}))
"""

    res = run_with_timeout(
        [sys.executable, "-c", code],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, res.stderr
    payload = json.loads(res.stdout or "{}")
    assert payload.get("ok") is True
    assert payload.get("session_id") == "sess-single"


def test_claim_task_with_lock_serializes_concurrent_claims(tmp_path: Path) -> None:
    """Only one of two concurrent sessions should successfully claim a task."""
    project_root = tmp_path
    repo_root = _repo_root()
    env = os.environ.copy()
    env.update(
        {
            "AGENTS_PROJECT_ROOT": str(project_root),
            "REPO_ROOT": str(repo_root),
        }
    )

    code = r"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path
import multiprocessing as mp

repo_root = Path(os.environ["REPO_ROOT"])
core_root = repo_root / ".edison" / "core"
from edison.core import task  # type: ignore  # noqa: E402

task_id = "t-lock-concurrent"
task.create_task_record("demo", task_id=task_id)  # type: ignore[attr-defined]

def worker(session_id: str, shared: "dict[str, bool]") -> None:
    ok = task.claim_task_with_lock(task_id, session_id, timeout=5)  # type: ignore[attr-defined]
    shared[session_id] = bool(ok)

if __name__ == "__main__":
    mp.set_start_method("fork", force=True)
    mgr = mp.Manager()
    results = mgr.dict()
    procs = [
        mp.Process(target=worker, args=("sess-a", results)),
        mp.Process(target=worker, args=("sess-b", results)),
    ]
    for p in procs:
        p.start()
    for p in procs:
        p.join()
    # Resolve winner from metadata
    meta_path = (task.ROOT / ".project" / "tasks" / "meta" / "task-t-lock-concurrent.json").resolve()  # type: ignore[attr-defined]
    meta = json.loads(meta_path.read_text())
    payload = {
        "results": dict(results),
        "winner": meta.get("session_id"),
    }
    print(json.dumps(payload))
"""

    res = run_with_timeout(
        [sys.executable, "-c", code],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout or "{}")
    results = data.get("results") or {}
    winner = data.get("winner")
    # Exactly one session should succeed
    assert sum(1 for v in results.values() if v) == 1, results
    assert winner in results
    assert results[winner] is True


def test_claim_task_with_lock_respects_timeout(tmp_path: Path) -> None:
    """When a lock is held, contenders should time out and return False."""
    project_root = tmp_path
    repo_root = _repo_root()
    env = os.environ.copy()
    env.update(
        {
            "AGENTS_PROJECT_ROOT": str(project_root),
            "REPO_ROOT": str(repo_root),
        }
    )

    code = r"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path
import multiprocessing as mp
import time

repo_root = Path(os.environ["REPO_ROOT"])
core_root = repo_root / ".edison" / "core"
from edison.core import task  # type: ignore  # noqa: E402
from edison.core.locklib import acquire_file_lock  # type: ignore  # noqa: E402
from edison.core.utils.subprocess import run_with_timeout

task_id = "t-lock-timeout"
task.create_task_record("demo", task_id=task_id)  # type: ignore[attr-defined]
meta_path = (task.ROOT / ".project" / "tasks" / "meta" / "task-t-lock-timeout.json").resolve()  # type: ignore[attr-defined]

def holder():
    with acquire_file_lock(meta_path, timeout=5.0):
        time.sleep(1.5)

def contender(shared: "dict[str, bool]") -> None:
    ok = task.claim_task_with_lock(task_id, "sess-timeout", timeout=0.5)  # type: ignore[attr-defined]
    shared["ok"] = bool(ok)

if __name__ == "__main__":
    mp.set_start_method("fork", force=True)
    mgr = mp.Manager()
    results = mgr.dict()
    p1 = mp.Process(target=holder)
    p2 = mp.Process(target=contender, args=(results,))
    p1.start()
    time.sleep(0.1)  # ensure holder acquires lock first
    p2.start()
    p1.join()
    p2.join()
    print(json.dumps(dict(results)))
"""

    res = run_with_timeout(
        [sys.executable, "-c", code],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, res.stderr
    payload = json.loads(res.stdout or "{}")
    assert payload.get("ok") is False
