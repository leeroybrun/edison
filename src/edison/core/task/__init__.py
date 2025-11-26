"""Task domain package."""

import os as os_module
import subprocess as subprocess_module

from .config import TaskConfig
from .io import (
    create_task,
    create_qa_brief,
    claim_task,
    ready_task,
    qa_progress,
    move_to_status,
    atomic_write_json,
    default_owner,
    write_text_locked,
    record_tdd_evidence,
    create_task_record,
    load_task_record,
    update_task_record,
    set_task_result,
    next_child_id,
    utc_timestamp,
    claim_task_with_lock,
)
from .store import tasks_root, qa_root, task_filename
from .locking import file_lock, is_locked, safe_move_file, transactional_move
from .finder import RecordMeta, RecordType, find_record, list_records, detect_record_type, normalize_record_id, infer_status_from_path
from .record_metadata import (
    TYPE_INFO,
    read_metadata,
    update_line,
    ensure_session_block,
    validate_state_transition,
)
from .paths import (
    ROOT,
    TASK_ROOT,
    QA_ROOT,
    SESSIONS_ROOT,
    SESSION_DIRS,
    TASK_DIRS,
    QA_DIRS,
    OWNER_PREFIX_TASK,
    OWNER_PREFIX_QA,
    STATUS_PREFIX,
    CLAIMED_PREFIX,
    LAST_ACTIVE_PREFIX,
    CONTINUATION_PREFIX,
    safe_relative,
)
from .transitions import transition_task  # existing orchestrated transition helper

# Legacy accessors kept for tests that monkeypatch low-level OS calls
os = os_module
subprocess = subprocess_module

__all__ = [
    "TaskConfig",
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
    "atomic_write_json",
    "record_tdd_evidence",
    "RecordMeta",
    "RecordType",
    "find_record",
    "list_records",
    "detect_record_type",
    "normalize_record_id",
    "infer_status_from_path",
    "update_line",
    "ensure_session_block",
    "read_metadata",
    "validate_state_transition",
    "ready_task",
    "qa_progress",
    "transition_task",
    "default_owner",
    "claim_task",
    "claim_task_with_lock",
    "file_lock",
    "is_locked",
    "create_task_record",
    "load_task_record",
    "update_task_record",
    "set_task_result",
    "ROOT",
    "TASK_ROOT",
    "QA_ROOT",
    "SESSIONS_ROOT",
    "SESSION_DIRS",
    "TASK_DIRS",
    "QA_DIRS",
    "TYPE_INFO",
    "CLAIMED_PREFIX",
    "LAST_ACTIVE_PREFIX",
    "CONTINUATION_PREFIX",
    "OWNER_PREFIX_TASK",
    "OWNER_PREFIX_QA",
    "STATUS_PREFIX",
    "utc_timestamp",
    "next_child_id",
    "os",
    "subprocess",
]
