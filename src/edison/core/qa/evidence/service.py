"""Evidence Service for QA Phase 5."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.utils.paths.management import get_management_paths
from . import reports, rounds
from .exceptions import EvidenceError


class EvidenceService:
    """Orchestrates evidence management for a task."""

    def __init__(self, task_id: str, project_root: Optional[Path] = None) -> None:
        self.task_id = task_id
        self.project_root = project_root
        
        # Resolve evidence root
        pm_paths = get_management_paths(project_root)
        self.evidence_root = pm_paths.get_qa_root() / "validation-evidence" / task_id

    def get_evidence_root(self) -> Path:
        """Return the root evidence directory for this task."""
        return self.evidence_root

    def ensure_round(self, round_num: Optional[int] = None) -> Path:
        """Ensure a round directory exists.

        If round_num is None, returns the latest round or creates round-1.
        If round_num is provided and matches next/current, ensures it exists.
        """
        if not self.evidence_root.exists():
            self.evidence_root.mkdir(parents=True, exist_ok=True)

        if round_num is None:
            latest = rounds.find_latest_round_dir(self.evidence_root)
            if latest:
                return latest
            return rounds.create_next_round_dir(self.evidence_root)
        
        # Specific round requested
        path = rounds.resolve_round_dir(self.evidence_root, round_num)
        if path:
            return path
            
        # If not found, check if it is the next one to support creation via number
        latest = rounds.find_latest_round_dir(self.evidence_root)
        next_num = 1
        if latest:
            next_num = rounds.get_round_number(latest) + 1
            
        if round_num == next_num:
            return rounds.create_next_round_dir(self.evidence_root)
            
        raise EvidenceError(f"Cannot create round {round_num}. Next available is {next_num}.")

    def get_current_round(self) -> Optional[int]:
        """Get the current round number."""
        latest = rounds.find_latest_round_dir(self.evidence_root)
        if latest:
            return rounds.get_round_number(latest)
        return None

    def get_current_round_dir(self) -> Optional[Path]:
        """Get the current round directory path.

        Returns None if no rounds exist yet.
        """
        return rounds.find_latest_round_dir(self.evidence_root)

    def create_next_round(self) -> Path:
        """Create and return the next round directory."""
        if not self.evidence_root.exists():
            self.evidence_root.mkdir(parents=True, exist_ok=True)
        return rounds.create_next_round_dir(self.evidence_root)

    def list_rounds(self) -> List[Path]:
        """List all round directories."""
        return rounds.list_round_dirs(self.evidence_root)

    def read_bundle(self, round_num: Optional[int] = None) -> Dict[str, Any]:
        """Read bundle summary."""
        round_dir = self.ensure_round(round_num)
        return reports.read_bundle_report(round_dir, self.project_root)

    def write_bundle(self, data: Dict[str, Any], round_num: Optional[int] = None) -> None:
        """Write bundle summary."""
        round_dir = self.ensure_round(round_num)
        reports.write_bundle_report(round_dir, data, self.project_root)

    def read_implementation_report(self, round_num: Optional[int] = None) -> Dict[str, Any]:
        """Read implementation report."""
        round_dir = self.ensure_round(round_num)
        return reports.read_implementation_report(round_dir, self.project_root)

    def write_implementation_report(
        self, data: Dict[str, Any], round_num: Optional[int] = None
    ) -> None:
        """Write implementation report."""
        round_dir = self.ensure_round(round_num)
        reports.write_implementation_report(round_dir, data, self.project_root)

    def read_validator_report(
        self, validator_name: str, round_num: Optional[int] = None
    ) -> Dict[str, Any]:
        """Read validator report."""
        round_dir = self.ensure_round(round_num)
        return reports.read_validator_report(round_dir, validator_name)

    def write_validator_report(
        self, validator_name: str, data: Dict[str, Any], round_num: Optional[int] = None
    ) -> None:
        """Write validator report."""
        round_dir = self.ensure_round(round_num)
        reports.write_validator_report(round_dir, validator_name, data)

    def list_validator_reports(self, round_num: Optional[int] = None) -> List[Path]:
        """List validator reports."""
        round_dir = self.ensure_round(round_num)
        return reports.list_validator_reports(round_dir)
