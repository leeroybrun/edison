"""Evidence operations manager for Edison framework."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from .exceptions import EvidenceError  # Re-export for convenience if needed, or just use
from .manager_base import EvidenceManagerBase
from .manager_read import EvidenceManagerReadMixin
from .manager_write import EvidenceManagerWriteMixin
from . import io as evidence_io


class EvidenceManager(EvidenceManagerBase, EvidenceManagerReadMixin, EvidenceManagerWriteMixin):
    """Evidence directory and report management for validation workflow.

    This class manages the evidence directory structure:
        <management_dir>/qa/validation-evidence/{task_id}/
            round-1/
                implementation-report.json
                validator-{name}-report.json
                bundle-approved.json
            round-2/
                ...

    All operations are relative to a specific task ID. Round numbers are
    automatically detected or can be specified explicitly.

    Examples:
        >>> mgr = EvidenceManager("task-100")
        >>> latest = mgr.get_latest_round_dir()
        >>> next_round = mgr.create_next_round_dir()
        >>> bundle = mgr.read_bundle_summary()
    """

    # ------------------------------------------------------------------
    # Static helpers (package 1A surface)
    # ------------------------------------------------------------------
    @staticmethod
    def get_latest_round_dir(task_id: str) -> Path:
        """Static helper: get latest evidence round directory for a task.

        Raises:
            FileNotFoundError: If no evidence rounds exist for the task.
        """
        mgr = EvidenceManager(task_id)
        latest = mgr._get_latest_round_dir()
        if latest is None:
            raise FileNotFoundError(
                f"No evidence rounds found for task {task_id} "
                f"under {mgr.base_dir}"
            )
        return latest

    @staticmethod
    def read_bundle_summary(task_id: str) -> Dict[str, Any]:
        """Static helper: read bundle-approved.json for latest round.

        Raises:
            FileNotFoundError: If evidence directory or bundle file missing.
            ValueError: If JSON is invalid (json.JSONDecodeError).
        """
        latest = EvidenceManager.get_latest_round_dir(task_id)
        bundle_path = latest / "bundle-approved.json"
        # read_json provides FileNotFoundError + JSON errors
        return evidence_io.read_json(bundle_path)

    @staticmethod
    def read_implementation_report(task_id: str) -> Dict[str, Any]:
        """Static helper: read implementation-report.json for latest round.

        Raises:
            FileNotFoundError: If evidence directory or report file missing.
            ValueError: If JSON is invalid (json.JSONDecodeError).
        """
        latest = EvidenceManager.get_latest_round_dir(task_id)
        report_path = latest / "implementation-report.json"
        return evidence_io.read_json(report_path)


def get_evidence_manager(task_id: str) -> EvidenceManager:
    """Convenience factory for creating evidence manager.

    Args:
        task_id: Task ID

    Returns:
        EvidenceManager: Configured evidence manager

    Examples:
        >>> mgr = get_evidence_manager("task-100")
        >>> latest = mgr.get_latest_round_dir()
    """
    return EvidenceManager(task_id)
