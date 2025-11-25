"""Task file I/O helpers."""
from __future__ import annotations

from pathlib import Path

from .io import (
    _task_filename,
    create_task,
    create_qa_brief,
    move_to_status,
    record_tdd_evidence,
)
from .locking import safe_move_file, transactional_move, write_text_locked
from .metadata import RecordType
from .paths import _qa_root, _tasks_root, safe_relative


def tasks_root() -> Path:
    return _tasks_root()  # pragma: no cover - exercised via higher-level tests


def qa_root() -> Path:
    return _qa_root()  # pragma: no cover


def task_filename(task_id: str) -> str:
    return _task_filename(task_id)


__all__ = [
    "tasks_root",
    "qa_root",
    "task_filename",
    "create_task",
    "create_qa_brief",
    "safe_relative",
    "safe_move_file",
    "write_text_locked",
    "transactional_move",
    "move_to_status",
    "record_tdd_evidence",
    "RecordType",
]
