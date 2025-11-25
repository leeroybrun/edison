"""Task/QA discovery utilities."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional

from ..exceptions import TaskNotFoundError
from ..session.layout import get_session_base_path
from .metadata import (
    RecordMeta,
    RecordType,
    detect_record_type,
    normalize_record_id,
    infer_status_from_path,
    read_metadata,
    TYPE_INFO,
)
from .paths import _tasks_root, _qa_root, SESSION_DIRS


def _record_filename(record_type: str, record_id: str) -> str:
    if record_type == "task":
        return f"task-{record_id}.md" if not record_id.endswith(".md") else record_id
    return f"{record_id}.md" if record_id.endswith(".qa") or record_id.endswith("-qa") else f"{record_id}-qa.md"


def _allowed_states_list(record_type: RecordType) -> List[str]:
    states = TYPE_INFO[record_type].get("allowed_statuses") or []
    if not states:
        states = (
            ["todo", "wip", "blocked", "done", "validated"]
            if record_type == "task"
            else ["waiting", "todo", "wip", "done", "validated"]
        )
    seen: set[str] = set()
    ordered: List[str] = []
    for s in states:
        s_norm = str(s).lower()
        if s_norm not in seen:
            seen.add(s_norm)
            ordered.append(s_norm)
    return ordered


def _session_base_candidates(session_id: str) -> List[Path]:
    bases: List[Path] = []
    session: dict = {"id": session_id}
    session_path: Optional[Path] = None

    try:
        from edison.core.session import store as session_store 
        session = session_store.load_session(session_id)
        session_path = session_store.get_session_json_path(session_id)
        if session_path and "parent" not in session:
            session = dict(session)
            session["parent"] = str(session_path.parent)
    except Exception:
        pass

    def _add(path: Optional[Path]) -> None:
        if path is None:
            return
        resolved = Path(path).resolve()
        if resolved not in bases:
            bases.append(resolved)

    primary = get_session_base_path(session, session_path=session_path)
    _add(primary)

    if session_id:
        if primary.name == session_id:
            _add(primary.parent)
        else:
            _add(primary / session_id)

    for sess_dir in SESSION_DIRS.values():
        _add((sess_dir / session_id).resolve())

    return bases


def _existing_session_bases() -> List[Path]:
    bases: List[Path] = []
    for sess_dir in SESSION_DIRS.values():
        if not sess_dir.exists():
            continue
        try:
            for child in sess_dir.iterdir():
                if child.is_dir():
                    resolved = child.resolve()
                    if resolved not in bases:
                        bases.append(resolved)
        except Exception:
            continue
    return bases


def find_record(
    record_id: str, record_type: RecordType, *, session_id: Optional[str] = None
) -> Path:
    rid = record_id
    if record_type == "qa" and rid.endswith(".md"):
        rid = rid[:-3]
    candidates: list[Path] = []
    fname = _record_filename("task" if record_type == "task" else "qa", record_id if record_type == "task" else rid)
    bare_task_name = f"{record_id}.md" if record_type == "task" else None
    alt_qa_name = None
    if record_type == "qa" and rid.endswith("-qa"):
        alt_qa_name = f"{rid}-qa.md"
    states = _allowed_states_list("task" if record_type == "task" else "qa")
    domain = "tasks" if record_type == "task" else "qa"

    session_bases: List[Path] = []
    if session_id:
        session_bases.extend(_session_base_candidates(session_id))
        for base in _existing_session_bases():
            if base.name == session_id and base not in session_bases:
                session_bases.append(base)
    else:
        session_bases.extend(_existing_session_bases())

    for base in session_bases:
        for state in states:
            sub = (base / domain / state).resolve()
            if record_type == "task":
                candidates.append(sub / fname)
                if bare_task_name and bare_task_name != fname:
                    candidates.append(sub / bare_task_name)
            else:
                candidates.append(sub / fname)
                if alt_qa_name:
                    candidates.append(sub / alt_qa_name)

    base = _tasks_root() if record_type == "task" else _qa_root()
    for state in states:
        sub = (base / state).resolve()
        if record_type == "task":
            candidates.append(sub / fname)
            if bare_task_name and bare_task_name != fname:
                candidates.append(sub / bare_task_name)
        else:
            candidates.append(sub / fname)
            if alt_qa_name:
                candidates.append(sub / alt_qa_name)
    for c in candidates:
        if c.exists():
            return c.resolve()
    raise TaskNotFoundError(
        f"Record not found: {record_type} {record_id}",
        context={"recordType": record_type, "recordId": record_id, "sessionId": session_id},
    )


def _iter_state_dirs(record_type: RecordType, base: Path) -> Iterable[Path]:
    info = TYPE_INFO[record_type]
    states: List[str] = list(info.get("allowed_statuses") or [])
    if not states:
        states = (
            ["todo", "wip", "blocked", "done", "validated"]
            if record_type == "task"
            else ["waiting", "todo", "wip", "done", "validated"]
        )
    for state in states:
        yield (base / state).resolve()


def list_records(
    record_type: RecordType,
    *,
    session_id: Optional[str] = None,
    include_global: bool = True,
) -> List[RecordMeta]:
    records: List[RecordMeta] = []

    if include_global:
        base = _tasks_root() if record_type == "task" else _qa_root()
        for state_dir in _iter_state_dirs(record_type, base):
            if not state_dir.exists():
                continue
            for path in state_dir.glob("*.md"):
                records.append(read_metadata(path, record_type))

    if session_id:
        for base in _session_base_candidates(session_id):
            domain_dir = "tasks" if record_type == "task" else "qa"
            for state in _allowed_states_list(record_type):
                state_dir = (base / domain_dir / state).resolve()
                if not state_dir.exists():
                    continue
                for path in state_dir.glob("*.md"):
                    records.append(read_metadata(path, record_type))
    else:
        for base in _existing_session_bases():
            domain_dir = "tasks" if record_type == "task" else "qa"
            for state in _allowed_states_list(record_type):
                state_dir = (base / domain_dir / state).resolve()
                if not state_dir.exists():
                    continue
                for path in state_dir.glob("*.md"):
                    records.append(read_metadata(path, record_type))

    return records


__all__ = [
    "RecordMeta",
    "RecordType",
    "find_record",
    "list_records",
    "detect_record_type",
    "normalize_record_id",
    "infer_status_from_path",
]
