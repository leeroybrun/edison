from __future__ import annotations

"""Record metadata parsing, validation, and JSON persistence."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Optional, Tuple

from edison.core.config import (
    load_workflow_config,
    get_task_states,
    get_qa_states,
    get_semantic_state,
)
from .paths import (
    TASK_DIRS,
    QA_DIRS,
    OWNER_PREFIX_TASK,
    OWNER_PREFIX_QA,
    STATUS_PREFIX,
    CLAIMED_PREFIX,
    LAST_ACTIVE_PREFIX,
    CONTINUATION_PREFIX,
)

RecordType = Literal["task", "qa"]


def _allowed_states_for(record_type: Literal["task", "qa"]) -> List[str]:
    if record_type == "task":
        return get_task_states()
    return get_qa_states()


TYPE_INFO: Dict[str, Dict[str, Any]] = {
    "task": {
        "allowed_statuses": _allowed_states_for("task"),
        "default_status": get_semantic_state("task", "todo"),
        "owner_prefix": OWNER_PREFIX_TASK,
        "status_prefix": STATUS_PREFIX,
        "dirs": TASK_DIRS,
    },
    "qa": {
        "allowed_statuses": _allowed_states_for("qa"),
        "default_status": get_semantic_state("qa", "waiting"),
        "owner_prefix": OWNER_PREFIX_QA,
        "status_prefix": STATUS_PREFIX,
        "dirs": QA_DIRS,
    },
}


def validate_state_transition(
    domain: Literal["task", "qa"],
    from_state: str,
    to_state: str,
) -> Tuple[bool, str]:
    """Validate a state transition using configured state machine."""
    allowed = _allowed_states_for(domain)
    
    if from_state not in allowed:
         return False, f"Invalid from_state '{from_state}' for {domain}. Allowed: {allowed}"
    
    if to_state not in allowed:
        return False, f"Invalid to_state '{to_state}' for {domain}. Allowed: {allowed}"

    # Note: Strict transition rules are not currently enforced by the YAML config,
    # so we allow any transition between valid states.
    # If strict rules are needed, they should be added to workflow.yaml and checked here.
    
    return True, "ok"


def detect_record_type(path: Optional[Path], explicit: Optional[str]) -> RecordType:
    if explicit in {"task", "qa"}:
        return explicit  # type: ignore[return-value]
    if path is None:
        raise ValueError("Must provide path or explicit record_type")
    name = Path(path).name.lower()
    if name.endswith("-qa.md") or name.endswith(".qa.md") or name.endswith(".qa"):
        return "qa"
    return "task"


def normalize_record_id(record_type: RecordType, filename: str) -> str:
    name = Path(filename).name
    if name.endswith(".md"):
        name = name[:-3]
    if record_type == "qa":
        if name.endswith("-qa"):
            name = name[:-3]
    if name.startswith("task-"):
        name = name[len("task-") :]
    return name


def infer_status_from_path(path: Path, record_type: RecordType) -> Optional[str]:
    p = Path(path).resolve()
    for parent in p.parents:
        if parent.name in ("tasks", "qa"):
            try:
                status = p.relative_to(parent).parts[0]
                return status
            except Exception:
                continue
    return p.parent.name


@dataclass
class RecordMeta:
    """Normalized metadata view for a task or QA markdown record."""

    path: Path
    record_id: str
    record_type: RecordType
    status: Optional[str] = None
    owner: Optional[str] = None
    claimed_at: Optional[str] = None
    last_active: Optional[str] = None


def update_line(lines: List[str], prefix: str, new_value: str, skip_if_set: bool = False) -> bool:
    if not lines:
        return False

    prefix_core = prefix.strip()

    for idx, line in enumerate(lines):
        stripped = line.lstrip()
        if not stripped.startswith(prefix_core):
            continue
        current = stripped[len(prefix_core) :].strip()
        if skip_if_set and current and current not in {"_unassigned_", "_none_"}:
            return False
        indent_len = len(line) - len(stripped)
        indent = line[:indent_len]
        newline = ""
        if line.endswith("\r\n"):
            newline = "\r\n"
        elif line.endswith("\n"):
            newline = "\n"
        lines[idx] = f"{indent}{prefix_core} {new_value}{newline}"
        return True
    return False


def ensure_session_block(lines: List[str]) -> None:
    is_qa = any(OWNER_PREFIX_QA in line for line in lines)
    owner_prefix = OWNER_PREFIX_QA if is_qa else OWNER_PREFIX_TASK

    def _has(prefix: str) -> bool:
        return any(line.lstrip().startswith(prefix) for line in lines)

    if not _has(owner_prefix):
        lines.append(f"{owner_prefix}_unassigned_\n")
    if not _has(STATUS_PREFIX):
        # Use default status from config via TYPE_INFO
        record_type = "qa" if is_qa else "task"
        default_status = TYPE_INFO[record_type]["default_status"]
        lines.append(f"{STATUS_PREFIX}{default_status}\n")

    if is_qa:
        if not _has(LAST_ACTIVE_PREFIX.strip()):
            lines.append(f"{LAST_ACTIVE_PREFIX}_unassigned_\n")
        return

    has_claimed = any(CLAIMED_PREFIX.strip() in line for line in lines)
    has_last_active = any(LAST_ACTIVE_PREFIX.strip() in line for line in lines)
    has_continuation = any(CONTINUATION_PREFIX.strip() in line for line in lines)

    if not (has_claimed and has_last_active and has_continuation):
        lines.append("## Session Info\n")
        if not has_claimed:
            lines.append(f"{CLAIMED_PREFIX}_unassigned_\n")
        if not has_last_active:
            lines.append(f"{LAST_ACTIVE_PREFIX}_unassigned_\n")
        if not has_continuation:
            lines.append(f"{CONTINUATION_PREFIX}_none_\n")


def read_metadata(path: Path, kind: RecordType) -> RecordMeta:
    p = Path(path)
    text = ""
    try:
        text = p.read_text(encoding="utf-8")
    except Exception:
        pass

    status = None
    owner = None
    claimed_at = None
    last_active = None

    for line in text.splitlines():
        stripped = line.strip()
        lower = stripped.lower()
        if stripped.startswith(OWNER_PREFIX_TASK):
            owner = stripped[len(OWNER_PREFIX_TASK) :].strip()
        elif stripped.startswith(OWNER_PREFIX_QA):
            owner = stripped[len(OWNER_PREFIX_QA) :].strip()
        elif stripped.startswith(STATUS_PREFIX):
            status_part = stripped[len(STATUS_PREFIX) :].strip()
            status = status_part.split("|")[0].strip()
        else:
            claim_prefix = CLAIMED_PREFIX.strip()
            last_prefix = LAST_ACTIVE_PREFIX.strip()
            if stripped.startswith(claim_prefix):
                claimed_at = stripped[len(claim_prefix) :].strip()
            elif stripped.startswith(last_prefix):
                last_active = stripped[len(last_prefix) :].strip()

    if not status:
        status = infer_status_from_path(p, kind)

    record_id = normalize_record_id(kind, p.name)
    return RecordMeta(
        path=p,
        record_id=record_id,
        record_type=kind,
        status=status,
        owner=owner,
        claimed_at=claimed_at,
        last_active=last_active,
    )


# Compatibility shim: some legacy callers import find_record from this module.
# Provide a thin wrapper that delegates to the finder implementation.
def find_record(record_id: str, record_type: RecordType, session_id: str | None = None):
    from .finder import find_record as _find_record  # local import to avoid cycles
    return _find_record(record_id, record_type, session_id=session_id)


__all__ = [
    "TYPE_INFO",
    "RecordType",
    "RecordMeta",
    "validate_state_transition",
    "detect_record_type",
    "normalize_record_id",
    "infer_status_from_path",
    "find_record",
    "update_line",
    "ensure_session_block",
    "read_metadata",
]