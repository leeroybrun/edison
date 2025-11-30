"""Session recovery and expiration management."""
from __future__ import annotations

import shutil
import logging
import yaml
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from edison.core.config.domains import TaskConfig
from edison.core.task.paths import get_task_dirs, get_qa_dirs
from edison.core.utils.io import ensure_directory, read_json, write_json_atomic, is_locked, safe_move_file
from edison.core.utils.time import utc_timestamp as io_utc_timestamp
from ..core.id import validate_session_id
from ..persistence.repository import SessionRepository
from .transaction import begin_tx, finalize_tx, abort_tx
from .._config import get_config
from .._utils import get_sessions_root

logger = logging.getLogger(__name__)

def _session_dir_map() -> Dict[str, Path]:
    """Get mapping of session states to their directory paths."""
    base = get_sessions_root()
    states = get_config().get_session_states()
    return {state: (base / dirname).resolve() for state, dirname in states.items()}

def _list_active_sessions() -> List[str]:
    """List all active session IDs."""
    repo = SessionRepository()
    sessions = repo.list_by_state("active")
    return [s.id for s in sessions]

def _session_json_path(sess_dir: Path) -> Path:
    """Get path to session.json within a session directory."""
    return sess_dir / "session.json"

def _parse_iso_utc(ts: str) -> Optional[datetime]:
    """Parse 'YYYY-MM-DDTHH:MM:SSZ' or with '+00:00' into aware UTC datetime."""
    try:
        if not ts:
            return None
        ts2 = str(ts).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts2)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError) as e:
        logger.debug("Failed to parse timestamp '%s': %s", ts, e)
        return None

def _session_meta_times(session: Dict[str, Any]) -> Tuple[Optional[datetime], Optional[datetime], Optional[datetime]]:
    meta = (session.get("meta") or {})
    created = _parse_iso_utc(str(meta.get("createdAt", "")))
    claimed = _parse_iso_utc(str(meta.get("claimedAt", "")))
    last_active = _parse_iso_utc(str(meta.get("lastActive", "")))
    return created, claimed, last_active

def _effective_activity_time(session: Dict[str, Any]) -> Optional[datetime]:
    created, claimed, last_active = _session_meta_times(session)
    times = [t for t in (last_active, claimed, created) if t is not None]
    return max(times) if times else None

def is_session_expired(session_id: str) -> bool:
    """Return True when a session exceeded inactivity timeout."""
    try:
        repo = SessionRepository()
        session_entity = repo.get(session_id)
        if not session_entity:
            return True
        sess = session_entity.to_dict()
    except (FileNotFoundError, OSError) as e:
        logger.warning("Failed to load session %s: %s", session_id, e)
        return True
    except ValueError as e:
        logger.error("Invalid session data for %s: %s", session_id, e)
        return True
    ref = _effective_activity_time(sess)
    if ref is None:
        return True
    now = datetime.now(timezone.utc)
    rec_cfg = get_config().get_recovery_config()
    skew_allowance = rec_cfg.get("clockSkewAllowanceSeconds")
    if skew_allowance is None:
        raise ValueError("session.recovery.clockSkewAllowanceSeconds not configured")
    skew_allowance = int(skew_allowance)
    timeout_hours = rec_cfg.get("timeoutHours")
    if timeout_hours is None:
        raise ValueError("session.recovery.timeoutHours not configured")
    timeout_hours = int(timeout_hours)
    
    if ref > now:
        skew = (ref - now).total_seconds()
        if skew <= skew_allowance:
            return False
        logger.warning("Session %s lastActive in future by %.1fs; tolerating", session_id, skew)
        return False
    elapsed = now - ref
    return elapsed > timedelta(hours=timeout_hours)

def append_session_log(session_id: str, message: str) -> None:
    """Append a message to the session activity log."""
    try:
        repo = SessionRepository()
        session_entity = repo.get(session_id)
        if not session_entity:
            return
        sess = session_entity.to_dict()
        sess.setdefault("activityLog", [])
        sess["activityLog"].insert(0, {
            "timestamp": io_utc_timestamp(),
            "message": message
        })
        from ..core.models import Session
        updated_entity = Session.from_dict(sess)
        repo.save(updated_entity)
    except (FileNotFoundError, OSError) as e:
        logger.warning("Failed to append session log for %s: %s", session_id, e)
    except ValueError as e:
        logger.error("Invalid session data for %s: %s", session_id, e)

def restore_records_to_global_transactional(session_id: str) -> int:
    """Restore all session-scoped records back to global queues."""
    sid = validate_session_id(session_id)
    # Locate the session directory across all configured states.
    session_root: Optional[Path] = None
    for base in _session_dir_map().values():
        candidate = (base / sid).resolve()
        if candidate.exists():
            session_root = candidate
            break
    if session_root is None:
        raise SessionNotFoundError(f"session directory not found for {sid}", context={"sessionId": sid})

    def _state_dirs_for(record_type: str, base: Path) -> List[Path]:
        config = TaskConfig()
        if record_type == "task":
            allowed = config.task_states()
        else:
            allowed = config.qa_states()
        return [(base / state).resolve() for state in allowed]

    records: List[Dict[str, Any]] = []
    domains = [("task", "tasks"), ("qa", "qa")]
    for rtype, domain in domains:
        base = session_root / domain
        if not base.exists():
            continue
        for state_dir in _state_dirs_for(rtype, base):
            if not state_dir.exists():
                continue
            for path in sorted(state_dir.glob("*.md")):
                record_id = path.stem  # Use filename stem as record_id
                if rtype == "task":
                    dest_base = get_task_dirs().get(state_dir.name)
                else:
                    dest_base = get_qa_dirs().get(state_dir.name)
                if dest_base is None:
                    continue
                dest = (dest_base / path.name).resolve()
                records.append(
                    {
                        "type": rtype,
                        "record_id": record_id,
                        "src": path,
                        "dest": dest,
                        "status": state_dir.name,
                    }
                )

    records.sort(key=lambda r: (r["type"], r["record_id"]))

    tx_id = begin_tx(sid, domain="rollback-restore", record_id="", from_status="active", to_status="closing")
    if not records:
        # Nothing to restore; treat as successful no-op so session completion can proceed.
        abort_tx(sid, tx_id, reason="rollback-restore-no-records")
        return 0

    moved: List[Dict[str, Any]] = []
    try:
        for rec in records:
            src: Path = rec["src"]
            dest: Path = rec["dest"]
            status: str = rec["status"]

            if is_locked(dest):
                raise RuntimeError(f"Destination locked for restore: {dest}")

            new_path = safe_move_file(src, dest)
            moved.append({"type": rec["type"], "src": src, "dest": new_path, "status": status})

        finalize_tx(sid, tx_id)
        return len(moved)
    except Exception as exc:
        for rec in reversed(moved):
            try:
                # move file back to its original session-scoped path
                ensure_directory(rec["dest"].parent)
                ensure_directory(rec["src"].parent)
                moved_back = safe_move_file(rec["dest"], rec["src"])
                logger.warning("Rollback restored %s to %s", rec["dest"], moved_back)
            except (OSError, RuntimeError) as e:
                logger.error("Rollback failed for %s: %s", rec["dest"], e)
                continue
        try:
            abort_tx(sid, tx_id, reason="rollback-restore")
        except (OSError, RuntimeError) as e:
            logger.warning("Failed to abort transaction %s: %s", tx_id, e)
        # Surface a clear rollback marker for callers/tests
        raise RuntimeError(f"Rolled back restore for session {sid}") from exc

def cleanup_expired_sessions() -> List[str]:
    """Detect and cleanup expired sessions."""
    cleaned: List[str] = []
    for sid in _list_active_sessions():
        try:
            if not is_session_expired(sid):
                continue
            try:
                restore_records_to_global_transactional(sid)
            except Exception as e:
                logger.error("Restore failed for %s: %s", sid, e)
            repo = SessionRepository()
            session_entity = repo.get(sid)
            if not session_entity:
                continue
            sess = session_entity.to_dict()
            sess["state"] = "closing"
            sess_meta = sess.get("meta", {})
            sess_meta["expiredAt"] = io_utc_timestamp()
            sess_meta.setdefault("lastActive", io_utc_timestamp())
            sess["meta"] = sess_meta
            append_session_log(sid, "Session expired due to inactivity; records restored to global queues")
            from ..core.models import Session
            updated_entity = Session.from_dict(sess)
            repo.save(updated_entity)
            # Note: save moves the session directory to the new state
            cleaned.append(sid)
        except SystemExit:
            raise
        except Exception as e:
            logger.error("Failed to cleanup session %s: %s", sid, e)
    return cleaned

def check_timeout(sess_dir: Path, threshold_minutes: Optional[int] = None) -> bool:
    if threshold_minutes is None:
        threshold_minutes = get_config().get_recovery_default_timeout_minutes()

    p = _session_json_path(sess_dir)
    if not p.exists():
        raise ValueError('missing session.json')
    data = read_json(p)
    ts = data.get('last_active_at') # Note: original code used last_active_at, but meta uses lastActive.
    # I should check if sessionlib uses both.
    # Line 2559: ts = data.get('last_active_at')
    if not ts:
        # Fallback to meta.lastActive?
        ts = (data.get("meta") or {}).get("lastActive")

    if not ts:
        raise ValueError('last_active_at missing')

    # _parse_iso is not defined here, I'll use _parse_iso_utc
    last = _parse_iso_utc(str(ts))
    if not last:
         raise ValueError('invalid timestamp')

    now = datetime.now(timezone.utc).replace(microsecond=0)
    delta = now - last
    return delta > timedelta(minutes=threshold_minutes)

def handle_timeout(sess_dir: Path) -> Path:
    # Move to recovery and annotate metadata
    orig = {}
    try:
        orig = read_json(_session_json_path(sess_dir))
    except (FileNotFoundError, OSError) as e:
        logger.warning("Failed to read session.json for %s: %s", sess_dir, e)
        orig = {}
    except ValueError as e:
        logger.error("Invalid session.json for %s: %s", sess_dir, e)
        orig = {}

    rec_dir = get_sessions_root() / 'recovery' / sess_dir.name
    ensure_directory(rec_dir.parent)
    if rec_dir.exists():
        shutil.rmtree(rec_dir)
    shutil.move(str(sess_dir), str(rec_dir))

    # Update session state
    meta = read_json(_session_json_path(rec_dir))
    meta['state'] = 'Recovery'
    write_json_atomic(_session_json_path(rec_dir), meta)

    # Write recovery reason
    write_json_atomic(rec_dir / 'recovery.json', {
        'reason': 'timeout exceeded',
        'original_path': str(sess_dir),
        'captured_at': io_utc_timestamp(),
        'session': orig,
    })
    return rec_dir


def detect_incomplete_transactions() -> List[Dict[str, Any]]:
    """Detect all incomplete validation transactions across all sessions.

    Returns a list of incomplete transaction metadata dictionaries.
    Each entry contains:
    - sessionId: Session identifier
    - txId: Transaction identifier
    - txDir: Path to transaction directory
    - startedAt: Transaction start timestamp
    - meta: Full transaction metadata
    """
    from .transaction import _get_tx_root, TX_VALIDATION_SUBDIR
    from edison.core.utils.io import read_json as io_read_json

    tx_root = _get_tx_root()
    if not tx_root.exists():
        return []

    incomplete = []

    # Iterate over session directories in transaction root
    for session_dir in tx_root.iterdir():
        if not session_dir.is_dir():
            continue

        session_id = session_dir.name
        val_root = session_dir / TX_VALIDATION_SUBDIR

        if not val_root.exists():
            continue

        # Iterate over validation transaction directories
        for tx_dir in val_root.iterdir():
            if not tx_dir.is_dir():
                continue

            meta_path = tx_dir / "meta.json"
            if not meta_path.exists():
                continue

            try:
                meta = io_read_json(meta_path)
            except (FileNotFoundError, OSError) as e:
                logger.debug("Failed to read meta.json for %s: %s", tx_dir, e)
                continue
            except ValueError as e:
                logger.warning("Invalid meta.json for %s: %s", tx_dir, e)
                continue

            tx_id = meta.get("txId")
            if not tx_id:
                continue

            finalized = meta.get("finalizedAt")
            aborted = meta.get("abortedAt")

            if not finalized and not aborted:
                # This is an incomplete transaction
                incomplete.append({
                    "sessionId": session_id,
                    "txId": tx_id,
                    "txDir": tx_dir,
                    "startedAt": meta.get("startedAt"),
                    "meta": meta,
                })

    return incomplete


def recover_incomplete_validation_transactions(session_id: str) -> int:
    """Recover incomplete validation transactions for a session.

    Scans for incomplete transactions in the session's transaction directory.
    For each incomplete transaction:
    1. If it was committed but not finalized, finalize it (it's done).
    2. If it was aborted, clean it up.
    3. If it was neither committed nor aborted (stale/crash), abort it and clean up.

    Returns the number of recovered transactions.
    """
    from .transaction import _tx_dir, _find_tx_session, finalize_tx, abort_tx, _get_tx_root, TX_VALIDATION_SUBDIR
    from edison.core.utils.io import read_json as io_read_json

    sid = validate_session_id(session_id)
    # Validation transactions are stored in <tx_root>/<sid>/validation/<tx_id>
    # But wait, transaction.py says:
    # _tx_validation_dir = _get_tx_root() / validate_session_id(session_id) / TX_VALIDATION_SUBDIR / tx_id

    tx_root = _get_tx_root()
    val_root = tx_root / sid / TX_VALIDATION_SUBDIR

    if not val_root.exists():
        return 0

    recovered = 0
    for tx_dir in val_root.iterdir():
        if not tx_dir.is_dir():
            continue

        meta_path = tx_dir / "meta.json"
        if not meta_path.exists():
            # Zombie directory?
            continue

        try:
            meta = io_read_json(meta_path)
        except (FileNotFoundError, OSError) as e:
            logger.debug("Failed to read meta.json for %s: %s", tx_dir, e)
            continue
        except ValueError as e:
            logger.warning("Invalid meta.json for %s: %s", tx_dir, e)
            continue

        tx_id = meta.get("txId")
        if not tx_id:
            continue

        finalized = meta.get("finalizedAt")
        aborted = meta.get("abortedAt")

        if finalized or aborted:
            # Already done
            continue

        # It's incomplete.
        # Check if we should roll it back or just mark it aborted.
        # ValidationTransaction.commit() sets _committed=True then writes finalizedAt.
        # If finalizedAt is missing, it wasn't fully committed.
        # So we should abort/rollback.

        # We can instantiate a ValidationTransaction and call abort?
        # Or just manually clean up.
        # Manual cleanup is safer to avoid side effects of __init__.

        logger.info("Recovering incomplete validation transaction %s for session %s", tx_id, sid)

        # 1. Clean up staging/snapshot
        staging = tx_dir / "staging"
        snapshot = tx_dir / "snapshot"
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        if snapshot.exists():
            shutil.rmtree(snapshot, ignore_errors=True)

        # 2. Mark as aborted in meta.json (validation transactions store metadata differently)
        try:
            from edison.core.utils.io.locking import acquire_file_lock
            from edison.core.utils.io import write_json_atomic as io_write_json_atomic

            with acquire_file_lock(meta_path):
                meta["abortedAt"] = io_utc_timestamp()
                meta["reason"] = "recovery-cleanup"
                io_write_json_atomic(meta_path, meta)

            recovered += 1
        except Exception as e:
            logger.error("Failed to abort recovered tx %s: %s", tx_id, e)

    return recovered


def clear_session_locks(session_id: str) -> List[str]:
    """Clear locks for a specific session.

    Args:
        session_id: Session identifier

    Returns:
        List of cleared lock file names
    """
    from edison.core.utils.paths import PathResolver

    sid = validate_session_id(session_id)
    try:
        root = PathResolver.resolve_project_root()
    except (FileNotFoundError, OSError, RuntimeError) as e:
        logger.warning("Failed to resolve project root: %s", e)
        return []

    lock_dir = root / ".project" / "locks"
    if not lock_dir.exists():
        return []

    cleared = []
    # Look for session-specific lock files
    for lock_file in lock_dir.glob(f"{sid}*.lock"):
        try:
            lock_file.unlink()
            cleared.append(lock_file.name)
        except Exception as e:
            logger.warning("Failed to clear lock %s: %s", lock_file.name, e)

    return cleared


def clear_all_locks(force: bool = False) -> List[str]:
    """Clear all stale locks.

    Args:
        force: If True, force clear all locks regardless of staleness

    Returns:
        List of cleared lock file names
    """
    from edison.core.utils.paths import PathResolver

    try:
        root = PathResolver.resolve_project_root()
    except (FileNotFoundError, OSError, RuntimeError) as e:
        logger.warning("Failed to resolve project root: %s", e)
        return []

    lock_dir = root / ".project" / "locks"
    if not lock_dir.exists():
        return []

    cleared = []
    for lock_file in lock_dir.glob("*.lock"):
        try:
            if force:
                lock_file.unlink()
                cleared.append(lock_file.name)
            else:
                # TODO: Implement staleness check based on lock age
                # For now, only clear if force=True
                pass
        except Exception as e:
            logger.warning("Failed to clear lock %s: %s", lock_file.name, e)

    return cleared
