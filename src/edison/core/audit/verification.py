"""Audit log verification utilities.

This module provides tamper-evident verification by comparing current file state
against logged audit events. It detects:
- Entity file changes not paired with transition events
- Evidence file modifications not paired with evidence-write events

This is tamper-EVIDENT (detect + report), not tamper-proof.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class UnloggedChange:
    """Represents a detected unlogged change."""

    entity_type: str  # "task", "qa", "session", "evidence"
    entity_id: str
    file_path: str
    reason: str
    last_modified: float  # mtime
    last_audit_event: str | None  # Timestamp of last relevant audit event
    current_hash: str | None  # Current content hash


def compute_file_hash(path: Path) -> str | None:
    """Compute SHA-256 hash of file content."""
    try:
        content = path.read_bytes()
        return hashlib.sha256(content).hexdigest()
    except Exception:
        return None


def read_audit_log(project_root: Path) -> list[dict[str, Any]]:
    """Read all events from the audit log.

    Returns a list of audit events, sorted by timestamp.
    """
    from edison.core.config.domains.logging import LoggingConfig

    try:
        cfg = LoggingConfig(repo_root=project_root)
    except Exception:
        return []

    if not cfg.enabled or not cfg.audit_enabled or not cfg.audit_jsonl_enabled:
        return []

    tokens = cfg.build_tokens(project_root=project_root)
    log_path = cfg.resolve_project_audit_path(tokens=tokens)
    if log_path is None or not log_path.exists():
        return []

    events: list[dict[str, Any]] = []
    try:
        with log_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    events.append(event)
                except json.JSONDecodeError:
                    continue
    except Exception:
        return []

    # Sort by timestamp
    events.sort(key=lambda e: e.get("ts", ""))
    return events


def get_entity_audit_events(
    events: list[dict[str, Any]],
    entity_type: str,
    entity_id: str,
    file_path: str | None = None,
) -> list[dict[str, Any]]:
    """Get audit events relevant to a specific entity.

    Args:
        events: List of audit events to search
        entity_type: Type of entity ("task", "qa", "session", "evidence")
        entity_id: ID of the entity (task_id for evidence)
        file_path: For evidence type, the specific file path to match.
                   If provided, only events for this exact file are returned.
                   If None, all evidence events for the task_id are returned.

    Returns:
        List of matching audit events, sorted by timestamp.
    """
    relevant: list[dict[str, Any]] = []
    for event in events:
        event_name = event.get("event", "")
        event_entity_id = event.get("entity_id") or event.get("task_id")

        # Match by entity type and ID
        if entity_type == "task":
            if event.get("task_id") == entity_id or event.get("entity_id") == entity_id:
                if "task" in event_name.lower() or "entity" in event_name.lower():
                    relevant.append(event)
        elif entity_type == "qa":
            qa_task_id = entity_id.replace("-qa", "")
            if event.get("task_id") == qa_task_id or event.get("entity_id") == entity_id:
                if "qa" in event_name.lower() or "entity" in event_name.lower():
                    relevant.append(event)
        elif entity_type == "session":
            if event.get("session_id") == entity_id:
                if "session" in event_name.lower():
                    relevant.append(event)
        elif entity_type == "evidence":
            if "evidence" in event_name.lower():
                # For evidence, prefer exact file path match if provided
                if file_path is not None:
                    event_file = event.get("file", "")
                    # Match if the event file path matches the target file
                    # Support both relative and absolute paths
                    if event_file and (
                        event_file == file_path
                        or file_path.endswith(event_file)
                        or event_file.endswith(file_path)
                        or Path(event_file).name == Path(file_path).name
                        and entity_id in event_file
                    ):
                        relevant.append(event)
                else:
                    # Fall back to task_id match only (less precise)
                    if event.get("task_id") == entity_id:
                        relevant.append(event)

    return relevant


def get_last_audit_timestamp(events: list[dict[str, Any]]) -> str | None:
    """Get the timestamp of the last event in the list."""
    if not events:
        return None
    return events[-1].get("ts")


def _get_relative_path(file_path: Path, project_root: Path, original_file: Path) -> str:
    """Get a relative path for reporting, handling symlinked directories.

    In Edison's meta-worktree layout, `.project/` is often a symlink to an external
    `_meta` directory. After resolving symlinks, file_path may not be under project_root.
    This function handles that case by using the original (pre-resolved) path relationship.

    Args:
        file_path: Resolved file path
        project_root: Resolved project root
        original_file: Original file path before symlink resolution

    Returns:
        A string path relative to project root (or the resolved path if outside)
    """
    try:
        return str(file_path.relative_to(project_root))
    except ValueError:
        # File is outside project_root after symlink resolution.
        # Use original path relationship if it works, otherwise use absolute path.
        try:
            # Try using the original paths (before resolution)
            return str(original_file.relative_to(original_file.parents[len(original_file.parts) - 1]))
        except (ValueError, IndexError):
            # Fall back to just the file name and some parent context
            return str(original_file)


def verify_entity_file(
    project_root: Path,
    entity_type: str,
    entity_id: str,
    file_path: Path,
    audit_events: list[dict[str, Any]],
) -> UnloggedChange | None:
    """Verify an entity file against audit log.

    Returns an UnloggedChange if the file appears to have been modified
    without a corresponding audit event.
    """
    if not file_path.exists():
        return None

    # Keep original path for relative path calculation in symlinked layouts
    original_file = file_path
    original_root = project_root

    # Resolve symlinks to handle macOS /var -> /private/var
    project_root = project_root.resolve()
    file_path = file_path.resolve()

    try:
        mtime = file_path.stat().st_mtime
    except Exception:
        return None

    current_hash = compute_file_hash(file_path)

    # Calculate relative path for reporting (handles symlinked .project/)
    def make_rel_path() -> str:
        # First try using resolved paths
        try:
            return str(file_path.relative_to(project_root))
        except ValueError:
            # Symlinked layout: use original pre-resolved path
            try:
                return str(original_file.relative_to(original_root))
            except ValueError:
                # Last resort: return the original path as-is
                return str(original_file)

    file_rel = make_rel_path()

    # Get relevant audit events for this entity
    # For evidence files, pass the file path to match events for this specific file
    if entity_type == "evidence":
        entity_events = get_entity_audit_events(
            audit_events, entity_type, entity_id, file_path=file_rel
        )
    else:
        entity_events = get_entity_audit_events(audit_events, entity_type, entity_id)
    last_audit_ts = get_last_audit_timestamp(entity_events)

    # If there are no audit events for this entity, but the file exists,
    # it might have been created before audit logging was enabled.
    # In this case, we check if there are ANY audit events at all.
    if not entity_events:
        # Check if there are any logged file modifications for this file
        file_events = [e for e in audit_events if file_rel in str(e.get("file", ""))]
        if not file_events and audit_events:
            # File exists but no audit events for it - potential unlogged change
            # However, we need to be careful about files created before audit logging
            # For now, we only flag files that were modified AFTER the first audit event
            first_event_ts = audit_events[0].get("ts", "") if audit_events else ""
            if first_event_ts:
                # Compare mtime to first event timestamp
                try:
                    from datetime import datetime

                    # Parse ISO timestamp
                    first_dt = datetime.fromisoformat(first_event_ts.replace("Z", "+00:00"))
                    file_dt = datetime.fromtimestamp(mtime, tz=first_dt.tzinfo)

                    if file_dt > first_dt:
                        return UnloggedChange(
                            entity_type=entity_type,
                            entity_id=entity_id,
                            file_path=file_rel,
                            reason="File modified after audit logging started, but no audit event found",
                            last_modified=mtime,
                            last_audit_event=None,
                            current_hash=current_hash,
                        )
                except Exception:
                    pass
        return None

    # Check if file was modified after the last audit event
    if last_audit_ts:
        try:
            from datetime import datetime

            last_dt = datetime.fromisoformat(last_audit_ts.replace("Z", "+00:00"))
            file_dt = datetime.fromtimestamp(mtime, tz=last_dt.tzinfo)

            # If file mtime is significantly after the last audit event (with tolerance),
            # it may have been tampered with.
            # Use a 1.0-second tolerance because audit log timestamps use second-level
            # precision (configurable via time.iso8601.timespec), so file modifications
            # within the same second as the audit event are legitimate.
            if (file_dt.timestamp() - last_dt.timestamp()) > 1.0:
                return UnloggedChange(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    file_path=file_rel,
                    reason="File modified after last audit event",
                    last_modified=mtime,
                    last_audit_event=last_audit_ts,
                    current_hash=current_hash,
                )
        except Exception:
            pass

    return None


def detect_unlogged_changes(
    project_root: Path,
    session_id: str,
    task_ids: list[str],
) -> list[UnloggedChange]:
    """Detect unlogged changes for all entities in a session.

    Args:
        project_root: Project root path
        session_id: Session ID to verify
        task_ids: List of task IDs in the session

    Returns:
        List of detected unlogged changes
    """
    from edison.core.task import TaskRepository
    from edison.core.qa.workflow.repository import QARepository

    unlogged: list[UnloggedChange] = []

    # Read audit log
    audit_events = read_audit_log(project_root)
    if not audit_events:
        # No audit log means we can't detect tampering
        return []

    task_repo = TaskRepository(project_root=project_root)
    qa_repo = QARepository(project_root=project_root)

    # Check task files
    for task_id in task_ids:
        try:
            task_path = task_repo.get_path(task_id)
            change = verify_entity_file(
                project_root=project_root,
                entity_type="task",
                entity_id=task_id,
                file_path=task_path,
                audit_events=audit_events,
            )
            if change:
                unlogged.append(change)
        except FileNotFoundError:
            pass

    # Check QA files
    for task_id in task_ids:
        qa_id = f"{task_id}-qa"
        try:
            qa_path = qa_repo.get_path(qa_id)
            change = verify_entity_file(
                project_root=project_root,
                entity_type="qa",
                entity_id=qa_id,
                file_path=qa_path,
                audit_events=audit_events,
            )
            if change:
                unlogged.append(change)
        except FileNotFoundError:
            pass

    # Check evidence files
    evidence_base = project_root / ".project" / "qa" / "validation-reports"
    for task_id in task_ids:
        task_evidence_dir = evidence_base / task_id
        if task_evidence_dir.exists():
            for round_dir in task_evidence_dir.iterdir():
                if not round_dir.is_dir():
                    continue
                for evidence_file in round_dir.iterdir():
                    if not evidence_file.is_file():
                        continue
                    change = verify_entity_file(
                        project_root=project_root,
                        entity_type="evidence",
                        entity_id=task_id,
                        file_path=evidence_file,
                        audit_events=audit_events,
                    )
                    if change:
                        unlogged.append(change)

    return unlogged


__all__ = [
    "UnloggedChange",
    "compute_file_hash",
    "read_audit_log",
    "verify_entity_file",
    "detect_unlogged_changes",
]
