"""QA validation transaction management.

This module provides the ValidationTransaction class that wraps session-level
transactions for QA validation workflows. It manages:
- Task-specific validation staging directories
- Evidence report persistence
- Transaction lifecycle coordination with session transactions

The ValidationTransaction integrates with the session transaction system
to ensure atomic validation operations.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Optional

from edison.core.utils.io import (
    write_json_atomic as io_write_json_atomic,
    ensure_directory as io_ensure_directory,
)
from ...session.lifecycle import transaction as _session_transaction
from edison.core.utils.paths import get_management_paths
from edison.core.utils.paths import PathResolver
from .._utils import read_json_safe
from ..evidence import reports as reportlib


class ValidationTransaction:
    """Per-task validation transaction wrapper.

    This is a lightweight facade over :func:`sessionlib.validation_transaction`
    that exposes a task/round-scoped staging directory for validator reports
    and surfaces the underlying transaction journal path.

    The underlying implementation is responsible for:
    - Creating a staging root under `<project-management-dir>/sessions/_tx/<sid>/validation/<txId>/staging`
    - Atomically copying staged files into `<project-management-dir>/qa/<evidence-subdir>/...`
    - Maintaining `meta.json` with lifecycle timestamps.
    """

    def __init__(self, task_id: str, round_num: int) -> None:
        self.task_id = str(task_id)
        self.round_num = int(round_num)
        # Canonical session id detection:
        # AGENTS_SESSION → <project-management-dir>/.session-id → process-derived lookup.
        # For validation runs outside a real session, fall back to the configured
        # validation session identifier.
        from edison.core.session.core.id import detect_session_id

        sid = detect_session_id(project_root=PathResolver.resolve_project_root())
        if sid:
            self._session_id = sid
        else:
            from edison.core.config.domains.qa import QAConfig

            qa_config = QAConfig()
            self._session_id = qa_config.get_validation_session_id()

        self.staging_dir: Optional[Path] = None
        self.journal_path: Optional[Path] = None

        # Underlying context manager and transaction object from sessionlib
        self._cm = None
        self._tx: Optional[_session_transaction.ValidationTransaction] = None  # type: ignore[attr-defined]

    def begin(self) -> "ValidationTransaction":
        """Create staging area and enrich the transaction journal."""
        # Create the core validation transaction which sets up staging/snapshot
        # directories and validation-transactions.log.
        self._cm = _session_transaction.validation_transaction(
            session_id=self._session_id,
            wave=self.task_id,
        )
        self._tx = self._cm.__enter__()  # type: ignore[assignment]

        # Task/round-scoped staging directory inside the transaction staging root.
        # Use config-driven paths (no hardcoded directory names)
        from edison.core.config.domains.task import TaskConfig
        from edison.core.qa._utils import get_evidence_base_path
        staging_root: Path = self._tx.staging_root  # type: ignore[assignment]
        project_root = PathResolver.resolve_project_root()
        task_cfg = TaskConfig(repo_root=project_root)
        # Get the relative path from project root to evidence base
        evidence_base = get_evidence_base_path(project_root)
        try:
            evidence_rel = evidence_base.relative_to(project_root)
        except Exception:
            # Fallback: use the evidence_base path name components
            evidence_rel = Path(evidence_base.relative_to(evidence_base.anchor))
        task_round_dir = (
            staging_root
            / evidence_rel
            / self.task_id
            / f"round-{self.round_num}"
        )
        self.staging_dir = io_ensure_directory(task_round_dir)

        # Underlying meta.json lives alongside staging/snapshot; treat its
        # parent directory as the journal path and enrich with task/round.
        meta_path: Path = self._tx.meta_path  # type: ignore[assignment]
        self.journal_path = meta_path.parent
        meta = read_json_safe(meta_path, default={})
        if "taskId" not in meta:
            meta["taskId"] = self.task_id
        if "round" not in meta:
            meta["round"] = self.round_num
        io_write_json_atomic(meta_path, meta)
        return self

    def write_validator_report(self, validator_name: str, report: Dict[str, Any]) -> None:
        """Write a validator report into the staging area."""
        if self.staging_dir is None:
            raise RuntimeError("ValidationTransaction.begin() must be called before writing reports")
        safe_name = str(validator_name).replace("/", "-")
        reportlib.write_validator_report(self.staging_dir, safe_name, report)

    def commit(self) -> None:
        """Atomically move staged evidence into the final QA evidence tree."""
        if not self._tx or not self._cm:
            raise RuntimeError("ValidationTransaction has not been started")
        # Delegate to core transaction implementation; it will:
        # - pre-check disk space and permissions
        # - copy+replace staged files into `<project-management-dir>/qa/<evidence-subdir>/...`
        # - update meta.json finalizedAt and clean up staging/snapshot
        self._tx.commit()

    def rollback(self) -> None:
        """Abort the transaction and discard staged evidence."""
        if not self._tx or not self._cm:
            return
        # Abort marks abortedAt and removes staging/snapshot directories.
        self._tx.abort("manual-rollback")

    def __enter__(self) -> "ValidationTransaction":
        return self.begin()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore[override]
        if not self._cm or not self._tx:
            return
        try:
            if exc_type is None:
                # Normal path: commit staged evidence.
                self._tx.commit()
            else:
                # Failure path: abort and keep original exception surface.
                self._tx.abort(f"exception: {getattr(exc_type, '__name__', 'Error')}")
        finally:
            # Ensure underlying context manager releases the validation lock
            # and performs any implicit abort when neither commit/abort ran.
            self._cm.__exit__(exc_type, exc_val, exc_tb)
