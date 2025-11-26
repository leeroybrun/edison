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

from ..paths.resolver import PathResolver
from ..file_io.locking import acquire_file_lock
from ..file_io.utils import (
    write_json_safe as io_atomic_write_json,
    read_json_safe as io_read_json_safe,
    ensure_dir,
)
from ..utils.time import utc_timestamp as io_utc_timestamp
from ..exceptions import SessionError
from .store import sanitize_session_id
from ..paths.management import get_management_paths

logger = logging.getLogger(__name__)

from .config import SessionConfig

_CONFIG = SessionConfig()

# Constants removed, resolved dynamically
TX_VALIDATION_SUBDIR = "validation"

def _get_tx_root() -> Path:
    env_root = os.environ.get("AGENTS_PROJECT_ROOT") or os.environ.get("project_ROOT")
    root = Path(env_root).resolve() if env_root else PathResolver.resolve_project_root()
    rel = _CONFIG.get_tx_root_path()
    return (root / rel).resolve()

def _tx_dir(session_id: str) -> Path:
    d = _get_tx_root() / sanitize_session_id(session_id)
    ensure_dir(d)
    return d

def _sid_dir(session_id: str) -> Path:
    # This should probably use store._session_dir logic or similar, 
    # but for now we can use the configured session root.
    # Or better, import _session_dir from store?
    # store._session_dir requires state.
    # Here we just want the session directory.
    # If the session directory location depends on state, we have a problem if we don't know the state.
    # However, _sid_dir seems to be used for validation logs inside the session dir.
    # If the session moves, the log moves?
    # Let's look at where _sid_dir is used: _tx_validation_log_path.
    # And _tx_validation_log_path is used in _append_tx_log.
    # If we don't know the state, we can't find the directory if it's partitioned by state.
    # The new store layout IS partitioned by state (active/closing/validated).
    # So we MUST know the state or search for it.
    # But _append_tx_log doesn't take state.
    # We might need to search for the session.
    from .store import get_session_json_path
    try:
        json_path = get_session_json_path(session_id)
        return json_path.parent
    except Exception:
        # Fallback or error?
        # If session doesn't exist, we can't log to it.
        # But maybe we are creating it?
        # For transactions, session usually exists.
        # Let's assume it exists.
        raise

def _tx_validation_dir(session_id: str, tx_id: str) -> Path:
    d = _get_tx_root() / sanitize_session_id(session_id) / TX_VALIDATION_SUBDIR / tx_id
    ensure_dir(d)
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
            ensure_dir(log_path.parent)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload) + "\n")
                f.flush()
                os.fsync(f.fileno())
    except SystemExit:
        pass

def begin_tx(
    session_id: str,
    *,
    domain: Optional[str] = None,
    record_id: Optional[str] = None,
    from_status: Optional[str] = None,
    to_status: Optional[str] = None,
) -> str:
    """Begin a lightweight validation/transition transaction for a session."""
    sid = sanitize_session_id(session_id)
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
            io_atomic_write_json(path, payload)
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
    except Exception:
        pass
    return tx_id

def finalize_tx(session_id: str, tx_id: str) -> None:
    p = _tx_dir(session_id) / f"{tx_id}.json"
    if not p.exists():
        return
    with acquire_file_lock(p):
        data = io_read_json_safe(p)
        data["finalizedAt"] = io_utc_timestamp()
        io_atomic_write_json(p, data)

def abort_tx(session_id: str, tx_id: str, reason: str = "") -> None:
    p = _tx_dir(session_id) / f"{tx_id}.json"
    if not p.exists():
        return
    with acquire_file_lock(p):
        data = io_read_json_safe(p)
        data["abortedAt"] = io_utc_timestamp()
        if reason:
            data["reason"] = reason
        io_atomic_write_json(p, data)

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
    except Exception:
        try:
            rollback_tx(tx_id)
        except SystemExit:
            raise
        except Exception:
            pass
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
    headroom = max(int(required_bytes * 0.1), 5 * 1024 * 1024)  # ≥5MB
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
        self.session_id = sanitize_session_id(session_id)
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
        except Exception:
            self._mgmt_rel = Path(mgmt_paths.get_management_root().name)
        self._committed = False
        self._aborted = False
        # Initialize directories
        ensure_dir(self.staging_root / self._mgmt_rel)
        ensure_dir(self.snapshot_root)
        # Write meta stub
        meta = {
            "txId": self.tx_id,
            "sessionId": self.session_id,
            "wave": self.wave,
            "startedAt": io_utc_timestamp(),
            "finalizedAt": None,
            "abortedAt": None,
        }
        io_atomic_write_json(self.meta_path, meta)
        _append_tx_log(self.session_id, self.tx_id, "started", f"staging={str(self.staging_root)}", wave=self.wave)
        # Disk-space forced precheck
        _ensure_disk_space(self.final_root, 1)

    @property
    def env(self) -> dict:
        return {"AGENTS_PROJECT_ROOT": str(self.staging_root)}

    def _snapshot_manifest(self) -> None:
        manifest: list[dict] = []
        mgmt_paths = get_management_paths(self.final_root)
        base = mgmt_paths.get_qa_root() / "validation-evidence"
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
                    except Exception:
                        pass
        try:
            meta = io_read_json_safe(self.meta_path)
        except Exception:
            meta = {}
        meta["preManifest"] = manifest
        io_atomic_write_json(self.meta_path, meta)

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
            ensure_dir(dst.parent)
            if dst.exists():
                backup_path = self.snapshot_root / rel
                ensure_dir(backup_path.parent)
                shutil.copy2(dst, backup_path)
            shutil.copy2(sf, dst)
            
        self._committed = True
        meta = io_read_json_safe(self.meta_path)
        meta["finalizedAt"] = io_utc_timestamp()
        io_atomic_write_json(self.meta_path, meta)
        _append_tx_log(self.session_id, self.tx_id, "committed", wave=self.wave)

    def abort(self, reason: str = "") -> None:
        if self._committed or self._aborted:
            return
        self._aborted = True
        # Cleanup staging
        if self.staging_root.exists():
            shutil.rmtree(self.staging_root, ignore_errors=True)
        if self.snapshot_root.exists():
            shutil.rmtree(self.snapshot_root, ignore_errors=True)
            
        meta = io_read_json_safe(self.meta_path)
        meta["abortedAt"] = io_utc_timestamp()
        meta["reason"] = reason
        io_atomic_write_json(self.meta_path, meta)
        _append_tx_log(self.session_id, self.tx_id, "aborted", f"reason={reason}", wave=self.wave)

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
