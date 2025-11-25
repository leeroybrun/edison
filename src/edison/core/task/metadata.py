from __future__ import annotations

"""Record metadata parsing, validation, and JSON persistence."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Optional, Tuple

from ..state import (
    RichStateMachine,
    StateTransitionError,
    action_registry,
    condition_registry,
    guard_registry,
    _flatten_transitions,
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
from .locking import file_lock, safe_move_file

RecordType = Literal["task", "qa"]


def _load_statemachine() -> Dict[str, Any]:
    """Load task/qa state machine from defaults.yaml with fallbacks."""
    try:
        from edison.core.config import ConfigManager 
        cfg = ConfigManager().load_config(validate=False)
        sm = cfg.get("statemachine")
        if sm:
            return sm
    except Exception:
        pass

    try:
        import yaml  # type: ignore

        core_root = Path(__file__).resolve().parents[2]
        for candidate in [
            core_root / "config/state-machine.yaml",
            Path(".edison/core/config/state-machine.yaml").resolve(),
            Path("config/state-machine.yaml").resolve(),
        ]:
            if candidate.exists():
                data = yaml.safe_load(candidate.read_text()) or {}
                sm = (data or {}).get("statemachine")
                if sm:
                    return sm
    except Exception:
        pass

    cfg_path = Path(".edison/core/config/defaults.yaml").resolve()
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(cfg_path.read_text()) if cfg_path.exists() else {}
        sm = (data or {}).get("statemachine")
        if sm:
            return sm
    except Exception:
        pass

    return {
        "task": {
            "states": {
                "todo": {"allowed_transitions": [{"to": "wip"}, {"to": "blocked"}]},
                "wip": {
                    "allowed_transitions": [
                        {"to": "blocked"},
                        {"to": "done"},
                        {"to": "todo"},
                        {"to": "validated"},
                    ]
                },
                "blocked": {"allowed_transitions": [{"to": "wip"}, {"to": "todo"}]},
                "done": {"allowed_transitions": [{"to": "validated"}, {"to": "wip"}]},
                "validated": {"allowed_transitions": []},
            },
        },
        "qa": {
            "states": {
                "waiting": {"allowed_transitions": [{"to": "todo"}]},
                "todo": {"allowed_transitions": [{"to": "wip"}]},
                "wip": {"allowed_transitions": [{"to": "done"}, {"to": "todo"}]},
                "done": {"allowed_transitions": [{"to": "validated"}, {"to": "wip"}]},
                "validated": {"allowed_transitions": []},
            },
        },
    }


def _allowed_states_for(record_type: Literal["task", "qa"]) -> List[str]:
    sm = _load_statemachine()
    domain = "task" if record_type == "task" else "qa"
    states = (sm.get(domain) or {}).get("states") or []
    if isinstance(states, dict):
        return list(states.keys())
    return [str(s) for s in states]


TYPE_INFO: Dict[str, Dict[str, Any]] = {
    "task": {
        "allowed_statuses": _allowed_states_for("task")
        or ["todo", "wip", "blocked", "done", "validated"],
        "default_status": "todo",
        "owner_prefix": OWNER_PREFIX_TASK,
        "status_prefix": STATUS_PREFIX,
        "dirs": TASK_DIRS,
    },
    "qa": {
        "allowed_statuses": _allowed_states_for("qa")
        or ["waiting", "todo", "wip", "done", "validated"],
        "default_status": "waiting",
        "owner_prefix": OWNER_PREFIX_QA,
        "status_prefix": STATUS_PREFIX,
        "dirs": QA_DIRS,
    },
}


def validate_state_transition(
    domain: Literal["task", "qa"], from_state: str, to_state: str
) -> Tuple[bool, str]:
    """Validate a state transition using configured state machine."""
    domain = "qa" if domain == "qa" else "task"
    sm = _load_statemachine()
    spec = sm.get(domain) or {}

    if domain == "qa" and isinstance(spec.get("states"), dict):
        states = spec.get("states", {})
        wip_state = states.get("wip") or {}
        transitions = wip_state.get("allowed_transitions") or []
        if isinstance(transitions, list) and not any((t or {}).get("to") == "waiting" for t in transitions):
            transitions.append({"to": "waiting", "guard": "always_allow"})
            wip_state["allowed_transitions"] = transitions
            states["wip"] = wip_state
            spec["states"] = states

    try:
        machine = RichStateMachine(domain, spec, guard_registry, condition_registry, action_registry)
        machine.validate(from_state, to_state, context={}, execute_actions=False)
        return True, "ok"
    except StateTransitionError as exc:
        transitions = machine.transitions_map() if "machine" in locals() else _flatten_transitions(
            spec.get("states", {})
        )
        allowed = sorted(transitions.get(from_state, []))
        known = sorted(machine.states.keys()) if "machine" in locals() else []
        return (
            False,
            f"{domain} transition {from_state} -> {to_state} not allowed. Allowed from {from_state}: {allowed}. Known states: {known}. {exc}",
        )


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
        default_status = "waiting" if is_qa else "todo"
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
