"""Session transaction management."""
from __future__ import annotations

import os
import json
import uuid
import shutil
import errno
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Iterator
from contextlib import contextmanager
from datetime import datetime, timezone

from edison.core.utils.paths import PathResolver, get_management_paths
from edison.core.utils.io.locking import acquire_file_lock, LockTimeoutError
from edison.core.utils.io import (
    write_json_atomic as io_write_json_atomic,
    read_json as io_read_json,
    ensure_directory,
)
from ...utils.time import utc_timestamp as io_utc_timestamp
from ...exceptions import SessionError
from ..core.id import validate_session_id
from .._config import get_config

logger = logging.getLogger(__name__)

# Constants removed, resolved dynamically
TX_VALIDATION_SUBDIR = "validation"

def _get_tx_root() -> Path:
    root = PathResolver.resolve_project_root()
    rel = get_config(root).get_tx_root_path()
    return (root / rel).resolve()

def _tx_dir(session_id: str) -> Path:
    d = _get_tx_root() / validate_session_id(session_id)
    ensure_directory(d)
    return d

def _sid_dir(session_id: str) -> Path:
    from ..persistence.repository import SessionRepository
    repo = SessionRepository()
    # Ensure a canonical session record exists so we can reliably derive the
    # on-disk directory (mapping is config-driven via SessionRepository).
    return repo.ensure_session(session_id)

def _tx_validation_dir(session_id: str, tx_id: str) -> Path:
    d = _get_tx_root() / validate_session_id(session_id) / TX_VALIDATION_SUBDIR / tx_id
    ensure_directory(d)
    return d

def _tx_validation_log_path(session_id: str) -> Path:
    return _sid_dir(session_id) / "validation-transactions.log"

def _append_tx_log(session_id: str, tx_id: str, action: str, message: str = "", *, wave: str | None = None) -> None:
    """Append one JSON line to the validation transactions log with a lock."""
    log_path = _tx_validation_log_path(session_id)
    payload = {
        "timestamp": io_utc_timestamp(),
        "txId": tx_id,
        "action": action,
        "wave": wave,
        "message": message,
    }
    try:
        with acquire_file_lock(log_path):
            ensure_directory(log_path.parent)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload) + "\n")
                f.flush()
                os.fsync(f.fileno())
    except SystemExit:
        raise

def begin_tx(
    session_id: str,
    *,
    domain: Optional[str] = None,
    record_id: Optional[str] = None,
    from_status: Optional[str] = None,
    to_status: Optional[str] = None,
) -> str:
    """Begin a lightweight validation/transition transaction for a session."""
    sid = validate_session_id(session_id)
    tx_id = uuid.uuid4().hex
    tx_dir = _tx_dir(sid)
    path = tx_dir / f"{tx_id}.json"
    payload: Dict[str, Any] = {
        "txId": tx_id,
        "sessionId": sid,
        "domain": domain or "session",
        "record_id": record_id or "",
        "from": from_status or "",
        "to": to_status or "",
        "startedAt": io_utc_timestamp(),
        "finalizedAt": None,
        "abortedAt": None,
    }
    try:
        with acquire_file_lock(path):
            io_write_json_atomic(path, payload)
    except SystemExit:
        raise
    except Exception as e:
        raise SessionError(
            "failed to begin validation transaction",
            session_id=sid,
            operation="begin-tx",
            details=str(e),
        )
    try:
        _append_tx_log(sid, tx_id, "begin", message=f"{payload['domain']}:{payload['record_id']}", wave=None)
    except (OSError, RuntimeError) as e:
        logger.warning("Failed to append transaction log for %s: %s", tx_id, e)
    return tx_id

def finalize_tx(session_id: str, tx_id: str) -> None:
    p = _tx_dir(session_id) / f"{tx_id}.json"
    if not p.exists():
        return
    with acquire_file_lock(p):
        data = io_read_json(p)
        data["finalizedAt"] = io_utc_timestamp()
        io_write_json_atomic(p, data)

def abort_tx(session_id: str, tx_id: str, reason: str = "") -> None:
    p = _tx_dir(session_id) / f"{tx_id}.json"
    if not p.exists():
        return
    with acquire_file_lock(p):
        data = io_read_json(p)
        data["abortedAt"] = io_utc_timestamp()
        if reason:
            data["reason"] = reason
        io_write_json_atomic(p, data)

def _find_tx_session(tx_id: str) -> str:
    """Locate the session id for a given ``tx_id`` under TX_ROOT."""
    tx_id = str(tx_id)
    tx_root = _get_tx_root()
    if not tx_root.exists():
        raise SessionError(
            "transaction not found",
            operation="lookup-tx",
            details=f"tx_id={tx_id}",
        )
    for sid_dir in tx_root.iterdir():
        if not sid_dir.is_dir():
            continue
        candidate = sid_dir / f"{tx_id}.json"
        if candidate.exists():
            return sid_dir.name
    raise SessionError(
        "transaction not found",
        operation="lookup-tx",
        details=f"tx_id={tx_id}",
    )

def commit_tx(tx_id: str) -> None:
    """Commit transaction changes identified by ``tx_id``."""
    session_id = _find_tx_session(tx_id)
    finalize_tx(session_id, tx_id)

def rollback_tx(tx_id: str) -> None:
    """Rollback transaction changes identified by ``tx_id``."""
    session_id = _find_tx_session(tx_id)
    abort_tx(session_id, tx_id, reason="rollback")

@contextmanager
def session_transaction(
    session_id: str,
    *,
    domain: str = "session",
    record_id: Optional[str] = None,
    from_status: Optional[str] = None,
    to_status: Optional[str] = None,
) -> Iterator[str]:
    """Context manager for atomic-ish session operations."""
    tx_id = begin_tx(
        session_id,
        domain=domain,
        record_id=record_id or "",
        from_status=from_status or "",
        to_status=to_status or "",
    )
    try:
        yield tx_id
    except SystemExit:
        raise
    except Exception:
        try:
            rollback_tx(tx_id)
        except SystemExit:
            raise
        except (OSError, RuntimeError) as e:
            logger.warning("Failed to rollback transaction %s: %s", tx_id, e)
        raise
    else:
        commit_tx(tx_id)

def _disk_free_bytes(path: Path) -> int:
    usage = shutil.disk_usage(str(path))
    return int(usage.free)

def _ensure_disk_space(final_root: Path, required_bytes: int) -> None:
    if os.environ.get("EDISON_FORCE_DISK_FULL") or os.environ.get("project_FORCE_DISK_FULL"):
        raise OSError(errno.ENOSPC, "Forced disk full for test")
    free_bytes = _disk_free_bytes(final_root)
    min_headroom = get_config().get_transaction_min_disk_headroom()
    headroom = max(int(required_bytes * 0.1), min_headroom)
    if free_bytes < required_bytes + headroom:
        raise OSError(errno.ENOSPC, f"Insufficient disk space: need {required_bytes}, free {free_bytes}")

def _iter_staging_files(staging_root: Path) -> Iterator[Path]:
    if not staging_root.exists():
        return
    for p in staging_root.rglob("*"):
        if p.is_file():
            yield p

def _relative_to_staging(staging_root: Path, p: Path) -> Path:
    return p.relative_to(staging_root)

class ValidationTransaction:
    def __init__(self, session_id: str, wave: str):
        self.session_id = validate_session_id(session_id)
        self.wave = wave
        self.tx_id = str(uuid.uuid4())
        self.tx_dir = _tx_validation_dir(self.session_id, self.tx_id)
        self.staging_root = self.tx_dir / "staging"
        self.snapshot_root = self.tx_dir / "snapshot"
        self.meta_path = self.tx_dir / "meta.json"
        self.final_root = PathResolver.resolve_project_root()
        mgmt_paths = get_management_paths(self.final_root)
        try:
            self._mgmt_rel = mgmt_paths.get_management_root().relative_to(self.final_root)
        except ValueError as e:
            logger.debug("Management root not relative to final root, using name only: %s", e)
            self._mgmt_rel = Path(mgmt_paths.get_management_root().name)
        self._committed = False
        self._aborted = False
        # Acquire lock to prevent concurrent transactions on same session
        self._lock_path = _tx_dir(self.session_id) / ".validation.lock"
        self._lock_cm = acquire_file_lock(self._lock_path)
        try:
            self._lock_cm.__enter__()
        except LockTimeoutError as e:
            raise SystemExit(f"Could not acquire validation transaction lock: {e}") from e
        # Initialize directories
        ensure_directory(self.staging_root / self._mgmt_rel)
        ensure_directory(self.snapshot_root)
        # Write meta stub
        meta = {
            "txId": self.tx_id,
            "sessionId": self.session_id,
            "wave": self.wave,
            "startedAt": io_utc_timestamp(),
            "finalizedAt": None,
            "abortedAt": None,
        }
        io_write_json_atomic(self.meta_path, meta)
        _append_tx_log(self.session_id, self.tx_id, "started", f"staging={str(self.staging_root)}", wave=self.wave)
        # Disk-space forced precheck
        _ensure_disk_space(self.final_root, 1)

    @property
    def env(self) -> dict:
        return {"AGENTS_PROJECT_ROOT": str(self.staging_root)}

    def _snapshot_manifest(self) -> None:
        from edison.core.qa._utils import get_evidence_base_path
        manifest: list[dict] = []
        base = get_evidence_base_path(self.final_root)
        if base.exists():
            for p in base.rglob("*"):
                if p.is_file():
                    try:
                        st = p.stat()
                        manifest.append({
                            "path": str(p.relative_to(self.final_root)),
                            "size": st.st_size,
                            "mtime": int(st.st_mtime),
                        })
                    except (OSError, ValueError) as e:
                        logger.debug("Failed to stat file %s: %s", p, e)
        try:
            meta = io_read_json(self.meta_path)
        except (FileNotFoundError, OSError) as e:
            logger.debug("Failed to read transaction metadata: %s", e)
            meta = {}
        except ValueError as e:
            logger.warning("Invalid transaction metadata JSON: %s", e)
            meta = {}
        meta["preManifest"] = manifest
        io_write_json_atomic(self.meta_path, meta)

    def commit(self) -> None:
        if self._committed:
            return
        if os.environ.get("EDISON_FORCE_PERMISSION_ERROR") or os.environ.get("project_FORCE_PERMISSION_ERROR"):
            _append_tx_log(self.session_id, self.tx_id, "commit-permission-error", "forced via env", wave=self.wave)
            raise PermissionError("Forced permission error for test")
        
        staged_files = list(_iter_staging_files(self.staging_root))
        staged_bytes = sum(p.stat().st_size for p in staged_files if p.exists())
        
        to_backup: list[Path] = []
        for sf in staged_files:
            rel = _relative_to_staging(self.staging_root, sf)
            dst = self.final_root / rel
            if dst.exists():
                to_backup.append(dst)
        backup_bytes = sum(d.stat().st_size for d in to_backup if d.exists())
        _ensure_disk_space(self.final_root, staged_bytes + backup_bytes)
        
        # Snapshot
        self._snapshot_manifest()
        
        # Apply changes
        for sf in staged_files:
            rel = _relative_to_staging(self.staging_root, sf)
            dst = self.final_root / rel
            ensure_directory(dst.parent)
            if dst.exists():
                backup_path = self.snapshot_root / rel
                ensure_directory(backup_path.parent)
                shutil.copy2(dst, backup_path)
            shutil.copy2(sf, dst)
            
        self._committed = True
        meta = io_read_json(self.meta_path)
        meta["finalizedAt"] = io_utc_timestamp()
        io_write_json_atomic(self.meta_path, meta)
        _append_tx_log(self.session_id, self.tx_id, "committed", wave=self.wave)
        # Release lock
        try:
            self._lock_cm.__exit__(None, None, None)
        except (OSError, RuntimeError) as e:
            logger.warning("Failed to release validation transaction lock after commit: %s", e)

    def abort(self, reason: str = "") -> None:
        if self._committed or self._aborted:
            return
        self._aborted = True
        # Cleanup staging
        if self.staging_root.exists():
            shutil.rmtree(self.staging_root, ignore_errors=True)
        if self.snapshot_root.exists():
            shutil.rmtree(self.snapshot_root, ignore_errors=True)

        meta = io_read_json(self.meta_path)
        meta["abortedAt"] = io_utc_timestamp()
        meta["reason"] = reason
        io_write_json_atomic(self.meta_path, meta)
        _append_tx_log(self.session_id, self.tx_id, "aborted", f"reason={reason}", wave=self.wave)
        # Release lock
        try:
            self._lock_cm.__exit__(None, None, None)
        except (OSError, RuntimeError) as e:
            logger.warning("Failed to release validation transaction lock during abort: %s", e)

    def rollback(self) -> None:
        self.abort("rollback")

@contextmanager
def validation_transaction(session_id: str, wave: str) -> Iterator[ValidationTransaction]:
    """Context manager for validation transactions."""
    tx = ValidationTransaction(session_id, wave)
    try:
        yield tx
    except Exception as e:
        tx.abort(f"exception: {e}")
        raise
    else:
        # The caller is expected to commit, but we can ensure it?
        # lib/qa/transaction.py calls commit() explicitly.
        # But if it falls through, should we commit?
        # The original sessionlib.validation_transaction likely didn't auto-commit 
        # if it was just yielding the object, but context managers usually do.
        # However, lib/qa/transaction.py handles commit/abort in its own __exit__.
        # So this context manager just needs to yield the tx.
        # But if we look at lib/qa/transaction.py:
        # self._cm = _sessionlib.validation_transaction(...)
        # self._tx = self._cm.__enter__()
        # It uses the context manager manually.
        pass
