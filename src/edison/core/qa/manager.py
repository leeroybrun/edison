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
from .evidence import EvidenceService
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
        svc = EvidenceService(task_id, project_root=self.project_root)
        return svc.create_next_round()

    def initialize_round(
        self, 
        task_id: str, 
        session_id: Optional[str] = None, 
        owner: Optional[str] = None
    ) -> Dict[str, Any]:
        """Initialize a new round with QA brief and metadata.
        
        Uses EvidenceService.create_qa_brief() as the canonical method.
        
        Args:
            task_id: Task identifier
            session_id: Session ID context
            owner: Validator owner (not used, kept for API compatibility)
            
        Returns:
            Dict with round info and path
        """
        svc = EvidenceService(task_id, project_root=self.project_root)
        
        # Use EvidenceService.create_qa_brief() as the single source
        qa_brief = svc.create_qa_brief(session_id=session_id)
        
        round_num = svc.get_current_round() or 1
        round_dir = svc.ensure_round(round_num)
        brief_path = round_dir / "qa-brief.json"
        
        return {
            "round": round_num,
            "path": str(brief_path),
            "brief": qa_brief
        }

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
        svc = EvidenceService(task_id, project_root=self.project_root)
        return svc.get_current_round()

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
        svc = EvidenceService(task_id, project_root=self.project_root)
        if round_num is None:
            return svc.get_current_round_dir()
        # Check if specific round exists
        round_dir = svc.get_round_dir(round_num)
        return round_dir if round_dir.exists() else None

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
        svc = EvidenceService(task_id, project_root=self.project_root)
        return svc.list_rounds()

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
        svc = EvidenceService(task_id, project_root=self.project_root)

        if report_type == "bundle":
            svc.write_bundle(data, round_num=round_num)
        elif report_type == "implementation":
            svc.write_implementation_report(data, round_num=round_num)
        elif report_type == "validator":
            if validator_name is None:
                raise ValueError("validator_name required for validator report type")
            svc.write_validator_report(validator_name, data, round_num=round_num)
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
        svc = EvidenceService(task_id, project_root=self.project_root)

        if report_type == "bundle":
            return svc.read_bundle(round_num=round_num)
        elif report_type == "implementation":
            return svc.read_implementation_report(round_num=round_num)
        elif report_type == "validator":
            if validator_name is None:
                raise ValueError("validator_name required for validator report type")
            return svc.read_validator_report(validator_name, round_num=round_num)
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
        svc = EvidenceService(task_id, project_root=self.project_root)
        return svc.list_validator_reports(round_num=round_num)


__all__ = ["QAManager"]
