from __future__ import annotations

"""Task and QA file operations plus atomic writes."""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from datetime import datetime, timezone

import getpass

from ..exceptions import TaskStateError
from edison.core.io import utils as io_utils
from ..session.layout import get_session_base_path
from .locking import safe_move_file, file_lock
from .paths import _qa_root, _session_qa_dir, _session_tasks_dir, _tasks_root, ROOT
from ..paths.management import get_management_paths
from .metadata import TYPE_INFO


def _task_filename(task_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]", "-", task_id)
    return f"task-{safe}.md"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def create_task(task_id: str, title: str, description: str = "") -> Path:
    filename = _task_filename(task_id)
    path = _tasks_root() / "todo" / filename

    # Check if task already exists
    if path.exists():
        raise TaskStateError(f"Task {task_id} already exists at {path}")

    body = (
        f"---\n"
        f"id: {task_id}\n"
        f"status: todo\n"
        f"title: {title}\n"
        f"---\n\n{description}\n"
    )
    _write(path, body)
    create_qa_brief(task_id, title)
    return path


def default_owner() -> str:
    try:
        from ..process.inspector import find_topmost_process  # type: ignore

        process_name, pid = find_topmost_process()
        return process_name
    except Exception:
        pass
    return os.environ.get("AGENTS_OWNER") or getpass.getuser()


def create_qa_brief(task_id: str, title: str) -> Path:
    path = _qa_root() / "waiting" / f"{task_id}-qa.md"
    content = (
        f"# QA Brief for {task_id}\n\n"
        f"- [ ] Unit tests green\n"
        f"- [ ] Lint/Type-check pass\n"
        f"- [ ] Evidence recorded\n"
        f"\nTitle: {title}\n"
    )
    _write(path, content)
    return path


def claim_task(task_id: str, session_id: str) -> Tuple[Path, Path]:
    src = _tasks_root() / "todo" / _task_filename(task_id)
    dst = _session_tasks_dir(session_id, "wip") / _task_filename(task_id)
    dst.parent.mkdir(parents=True, exist_ok=True)
    content = src.read_text(encoding="utf-8") if src.exists() else ""
    content = content.replace("status: todo", "status: wip") or content
    dst.write_text(content, encoding="utf-8")
    if src.exists():
        src.unlink(missing_ok=False)

    qa_dst = _session_qa_dir(session_id, "waiting") / f"{task_id}-qa.md"
    qa_dst.parent.mkdir(parents=True, exist_ok=True)
    qa_src = _qa_root() / "waiting" / f"{task_id}-qa.md"
    if qa_src.exists():
        safe_move_file(qa_src, qa_dst)
    else:
        qa_dst.write_text(f"# QA Brief for {task_id}\n\n- **Status:** waiting\n", encoding="utf-8")

    return src, dst


def ready_task(task_id: str, session_id: str) -> Tuple[Path, Path]:
    src = _session_tasks_dir(session_id, "wip") / _task_filename(task_id)
    dst = _session_tasks_dir(session_id, "done") / _task_filename(task_id)
    dst.parent.mkdir(parents=True, exist_ok=True)
    content = src.read_text(encoding="utf-8") if src.exists() else ""
    content = content.replace("status: wip", "status: done") or content
    dst.write_text(content, encoding="utf-8")
    if src.exists():
        src.unlink(missing_ok=False)
    qa_src = _session_qa_dir(session_id, "waiting") / f"{task_id}-qa.md"
    qa_dst = _session_qa_dir(session_id, "todo") / f"{task_id}-qa.md"
    qa_dst.parent.mkdir(parents=True, exist_ok=True)
    if qa_src.exists():
        safe_move_file(qa_src, qa_dst)
    else:
        global_waiting = _qa_root() / "waiting" / f"{task_id}-qa.md"
        if global_waiting.exists():
            safe_move_file(global_waiting, qa_dst)
        else:
            qa_dst.write_text(f"# QA Brief for {task_id}\n\n- **Status:** todo\n", encoding="utf-8")
    return src, dst


def qa_progress(task_id: str, from_state: str, to_state: str, session_id: Optional[str] = None) -> Tuple[Path, Path]:
    if session_id:
        from .metadata import find_record  # local import to avoid cycles

        src = find_record(task_id, "qa", session_id=session_id)
        qa_root = src.parent.parent
        dst = qa_root / to_state / f"{task_id}-qa.md"
    else:
        src = _qa_root() / from_state / f"{task_id}-qa.md"
        dst = _qa_root() / to_state / f"{task_id}-qa.md"

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    src.unlink(missing_ok=False)
    return src, dst


def move_to_status(
    path: Path,
    record_type: str,
    status: str,
    session_id: Optional[str] = None,
) -> Path:
    status = status.lower()
    src = Path(path)

    if session_id:
        sid = session_id
        session: Dict[str, Any] = {"id": sid}
        session_path: Optional[Path] = None
        try:
            from edison.core.session import store as session_store 
            session = session_store.load_session(sid)
            session_path = session_store.get_session_json_path(sid)
            if session_path and "parent" not in session:
                session = dict(session)
                session["parent"] = str(session_path.parent)
        except Exception:
            pass

        domain_dir = "tasks" if record_type == "task" else "qa"
        base = get_session_base_path(session, session_path=session_path)

        if base.name != sid and not (base / domain_dir).exists():
            base = base / sid

        dest_dir = base / domain_dir / status
    else:
        dirs = TYPE_INFO[record_type]["dirs"]
        if status not in dirs:
            raise TaskStateError(
                f"Unknown status '{status}' for record type {record_type}",
                context={"recordType": record_type, "status": status},
            )
        dest_dir = dirs[status]

    dest = Path(dest_dir) / src.name
    if dest.resolve() == src.resolve():
        return dest
    return safe_move_file(src, dest)


def atomic_write_json(path: Path, data: Dict[str, Any], *, indent: int = 2) -> None:
    target = Path(path)

    def _writer(f):
        json.dump(data, f, indent=indent)

    io_utils._atomic_write(target, _writer)


def write_text_locked(path: Path, content: str) -> None:
    from .locking import write_text_locked as _wtl

    _wtl(path, content)


def move_to_status_atomic(path: Path, record_type: str, status: str, session_id: Optional[str] = None) -> Path:
    return move_to_status(path, record_type, status, session_id=session_id)


def record_tdd_evidence(task_id: str, phase: str, note: str = "") -> Path:
    mgmt_paths = get_management_paths(ROOT)
    path = (mgmt_paths.get_qa_root() / "validation-evidence" / "tasks").resolve() / f"task-{task_id}.tdd.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(f"{phase.upper()}: {note}\n")
    return path


def _tasks_meta_root() -> Path:
    mgmt_paths = get_management_paths(ROOT)
    return (mgmt_paths.get_tasks_root() / "meta").resolve()


def _task_meta_path(task_id: str) -> Path:
    return _tasks_meta_root() / f"{task_id}.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _validate_task_record(rec: Dict[str, Any]) -> None:
    required = ["id", "title", "status"]
    missing = [f for f in required if f not in rec]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")


def update_task_record(task_id: str, updates: Dict[str, Any], *, operation: str = "update") -> Dict[str, Any]:
    path = _task_meta_path(task_id)
    record: Dict[str, Any] = {}
    if path.exists():
        record = _read_json(path)
    record.update(updates)
    record.setdefault("id", task_id)
    record.setdefault("status", "todo")
    record.setdefault("updated_at", _now_iso())
    record["operation"] = operation
    _validate_task_record(record)
    _write_json(path, record)
    return record


def _resolve_session_json_path(session_id: str) -> Optional[Path]:
    mgmt_paths = get_management_paths(ROOT)
    candidates = [
        mgmt_paths.get_session_state_dir("active") / session_id / "session.json",
        mgmt_paths.get_sessions_root() / "session.json",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _append_task_to_session(session_id: str, task_id: str) -> None:
    path = _resolve_session_json_path(session_id)
    if path is None:
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8")) or {}
        tasks = data.get("tasks") or []
        if task_id not in tasks:
            tasks.append(task_id)
        data["tasks"] = tasks
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def create_task_record(task_id: str, title: str, *, status: str = "todo") -> Dict[str, Any]:
    record = {
        "id": task_id,
        "title": title,
        "status": status,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    _write_json(_task_meta_path(task_id), record)
    return record


def load_task_record(task_id: str) -> Dict[str, Any]:
    path = _task_meta_path(task_id)
    if not path.exists():
        raise FileNotFoundError(f"Task record not found: {task_id}")
    return _read_json(path)


def set_task_result(task_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
    record = load_task_record(task_id)
    record["result"] = result
    record["updated_at"] = _now_iso()
    _write_json(_task_meta_path(task_id), record)
    return record


def next_child_id(base_id: str) -> str:
    existing_ids = []
    meta_dir = _tasks_meta_root()
    if meta_dir.exists():
        for path in meta_dir.glob(f"{base_id}-*.json"):
            existing_ids.append(path.stem)
    if not existing_ids:
        return f"{base_id}-1"
    nums = []
    for eid in existing_ids:
        try:
            suffix = int(eid.split("-")[-1])
            nums.append(suffix)
        except Exception:
            continue
    nxt = max(nums) + 1 if nums else 1
    return f"{base_id}-{nxt}"


def claim_task_with_lock(task_id: str, session_id: str, timeout: int = 30) -> bool:
    lock_path = _task_meta_path(task_id).with_suffix(".lock")
    with file_lock(lock_path, timeout=timeout):
        update_task_record(task_id, {"claimed_by": session_id}, operation="claim")
        _append_task_to_session(session_id, task_id)
    return True


__all__ = [
    "create_task",
    "create_qa_brief",
    "claim_task",
    "ready_task",
    "qa_progress",
    "move_to_status",
    "atomic_write_json",
    "default_owner",
    "_task_filename",
    "write_text_locked",
    "record_tdd_evidence",
    "create_task_record",
    "load_task_record",
    "update_task_record",
    "set_task_result",
    "next_child_id",
    "utc_timestamp",
    "claim_task_with_lock",
]
