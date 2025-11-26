"""QA manager facade for evidence and validation operations.

This module provides a unified interface for QA operations, following the same
pattern as SessionManager and TaskManager for module coherence.

The QAManager provides:
- Round directory management (create, get, list)
- Report operations (read, write, list)
- Integration with the evidence store

Examples:
    >>> mgr = QAManager()
    >>> round_dir = mgr.create_round("task-100")
    >>> mgr.write_report("task-100", "bundle", {...})
    >>> bundle = mgr.read_report("task-100", "bundle")
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.utils.paths import PathResolver
from .evidence import EvidenceManager
from edison.core.config.domains import QAConfig


class QAManager:
    """Lightweight facade for QA evidence and validation operations.

    Follows the same pattern as TaskManager with instance-based API and
    project_root parameter for test isolation.

    Attributes:
        project_root: Project root directory for path resolution
    """

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize QA manager.

        Args:
            project_root: Optional project root; defaults to PathResolver resolution
        """
        self.project_root = project_root or PathResolver.resolve_project_root()
        self._config = QAConfig(repo_root=self.project_root)

    def create_round(self, task_id: str) -> Path:
        """Create next evidence round directory for a task.

        Creates round-1 if no rounds exist, otherwise creates round-{N+1}.

        Args:
            task_id: Task identifier

        Returns:
            Path to newly created round directory

        Examples:
            >>> mgr = QAManager()
            >>> round_1 = mgr.create_round("task-100")
            >>> assert round_1.name == "round-1"
        """
        mgr = EvidenceManager(task_id, project_root=self.project_root)
        return mgr.create_next_round_dir()

    def get_latest_round(self, task_id: str) -> Optional[int]:
        """Get the latest round number for a task.

        Args:
            task_id: Task identifier

        Returns:
            Latest round number, or None if no rounds exist

        Examples:
            >>> mgr = QAManager()
            >>> latest = mgr.get_latest_round("task-100")
            >>> if latest:
            ...     print(f"Latest round: {latest}")
        """
        mgr = EvidenceManager(task_id, project_root=self.project_root)
        latest_dir = mgr._get_latest_round_dir()
        if latest_dir is None:
            return None
        return mgr.get_round_number(latest_dir)

    def get_round_dir(self, task_id: str, round_num: Optional[int] = None) -> Optional[Path]:
        """Get path to evidence round directory.

        Args:
            task_id: Task identifier
            round_num: Specific round number, or None for latest

        Returns:
            Path to round directory, or None if doesn't exist

        Examples:
            >>> mgr = QAManager()
            >>> round_2 = mgr.get_round_dir("task-100", round_num=2)
            >>> latest = mgr.get_round_dir("task-100")  # Get latest
        """
        mgr = EvidenceManager(task_id, project_root=self.project_root)
        return mgr._resolve_round_dir(round_num)

    def list_rounds(self, task_id: str) -> List[Path]:
        """List all evidence round directories for a task.

        Args:
            task_id: Task identifier

        Returns:
            Sorted list of round directories (oldest to newest)

        Examples:
            >>> mgr = QAManager()
            >>> rounds = mgr.list_rounds("task-100")
            >>> for round_dir in rounds:
            ...     print(round_dir.name)
        """
        mgr = EvidenceManager(task_id, project_root=self.project_root)
        return mgr.list_rounds()

    def write_report(
        self,
        task_id: str,
        report_type: str,
        data: Dict[str, Any],
        *,
        round_num: Optional[int] = None,
        validator_name: Optional[str] = None
    ) -> None:
        """Write a report to the evidence directory.

        Args:
            task_id: Task identifier
            report_type: Type of report ("bundle", "implementation", "validator")
            data: Report data to write
            round_num: Specific round number, or None for latest
            validator_name: Required for "validator" report_type

        Raises:
            ValueError: If validator_name not provided for validator report
            ValueError: If invalid report_type

        Examples:
            >>> mgr = QAManager()
            >>> mgr.write_report("task-100", "bundle", {"approved": True})
            >>> mgr.write_report("task-100", "validator", {...}, validator_name="claude")
        """
        mgr = EvidenceManager(task_id, project_root=self.project_root)

        if report_type == "bundle":
            mgr.write_bundle_summary(data, round=round_num)
        elif report_type == "implementation":
            mgr.write_implementation_report(data, round=round_num)
        elif report_type == "validator":
            if validator_name is None:
                raise ValueError("validator_name required for validator report type")
            mgr.write_validator_report(validator_name, data, round=round_num)
        else:
            raise ValueError(f"Unknown report_type: {report_type}")

    def read_report(
        self,
        task_id: str,
        report_type: str,
        *,
        round_num: Optional[int] = None,
        validator_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Read a report from the evidence directory.

        Args:
            task_id: Task identifier
            report_type: Type of report ("bundle", "implementation", "validator")
            round_num: Specific round number, or None for latest
            validator_name: Required for "validator" report_type

        Returns:
            Report data, or empty dict if not found

        Raises:
            ValueError: If validator_name not provided for validator report
            ValueError: If invalid report_type

        Examples:
            >>> mgr = QAManager()
            >>> bundle = mgr.read_report("task-100", "bundle")
            >>> validator = mgr.read_report("task-100", "validator", validator_name="claude")
        """
        mgr = EvidenceManager(task_id, project_root=self.project_root)

        if report_type == "bundle":
            return mgr._read_bundle_summary(round=round_num)
        elif report_type == "implementation":
            return mgr._read_implementation_report(round=round_num)
        elif report_type == "validator":
            if validator_name is None:
                raise ValueError("validator_name required for validator report type")
            return mgr.read_validator_report(validator_name, round=round_num)
        else:
            raise ValueError(f"Unknown report_type: {report_type}")

    def list_validator_reports(self, task_id: str, round_num: Optional[int] = None) -> List[Path]:
        """List all validator report files in a round directory.

        Args:
            task_id: Task identifier
            round_num: Specific round number, or None for latest

        Returns:
            Sorted list of validator report paths

        Examples:
            >>> mgr = QAManager()
            >>> reports = mgr.list_validator_reports("task-100")
            >>> for report in reports:
            ...     print(report.name)
        """
        mgr = EvidenceManager(task_id, project_root=self.project_root)
        return mgr.list_validator_reports(round=round_num)


__all__ = ["QAManager"]
