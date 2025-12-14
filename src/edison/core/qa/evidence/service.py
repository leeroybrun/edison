"""Evidence Service - Single source of truth for all evidence I/O.

This module consolidates all evidence I/O operations into a single service.
All evidence-related reads and writes should go through EvidenceService.

Architecture:
- EvidenceService is the ONLY entry point for evidence I/O
- Filenames are resolved from configuration (validation.artifactPaths)
- Round management is delegated to the rounds module
"""
from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.utils.io import read_json, write_json_atomic
from .._utils import get_qa_root_path
from .exceptions import EvidenceError
from . import rounds
from . import reports


class EvidenceService:
    """Single source of truth for evidence management.

    All evidence I/O operations (bundle, implementation reports, validator reports)
    should go through this service. It handles:
    - Config-based filename resolution
    - Round directory management
    - Atomic writes with proper error handling
    """

    def __init__(self, task_id: str, project_root: Optional[Path] = None) -> None:
        self.task_id = task_id
        self.project_root = project_root

        # Resolve evidence root using shared utility (single source of truth)
        from .._utils import get_evidence_base_path
        self.evidence_root = get_evidence_base_path(project_root) / task_id

    # -------------------------------------------------------------------------
    # Config-based filename resolution (SINGLE SOURCE)
    # -------------------------------------------------------------------------

    @cached_property
    def _artifact_paths(self) -> Dict[str, str]:
        """Get configured artifact filenames from QA config.

        Returns filenames for bundle and implementation reports.
        This is the SINGLE SOURCE for artifact filename resolution.
        """
        from edison.core.config.domains.qa import QAConfig

        config = QAConfig(repo_root=self.project_root)
        paths = config.validation_config.get("artifactPaths", {})
        if not isinstance(paths, dict):
            paths = {}

        return {
            "bundle": paths.get("bundleSummaryFile", "bundle-approved.json"),
            "implementation": paths.get("implementationReportFile", "implementation-report.json"),
        }

    @property
    def bundle_filename(self) -> str:
        """Get configured bundle summary filename."""
        return self._artifact_paths["bundle"]

    @property
    def implementation_filename(self) -> str:
        """Get configured implementation report filename."""
        return self._artifact_paths["implementation"]

    # -------------------------------------------------------------------------
    # Path resolution
    # -------------------------------------------------------------------------

    def get_evidence_root(self) -> Path:
        """Return the root evidence directory for this task."""
        return self.evidence_root

    def get_round_dir(self, round_num: int) -> Path:
        """Get path to a specific round directory (may not exist)."""
        return self.evidence_root / f"round-{round_num}"

    def get_validator_report_path(self, round_dir: Path, validator_id: str) -> Path:
        """Get the path for a validator report file.

        Delegates to `edison.core.qa.evidence.reports` as the canonical naming rule.
        """
        return reports.validator_report_path(round_dir, validator_id)

    def ensure_round(self, round_num: Optional[int] = None) -> Path:
        """Ensure a round directory exists.

        If round_num is None, returns the latest round or creates round-1.
        If round_num is provided and matches next/current, ensures it exists.
        """
        return rounds.ensure_round_dir(self.evidence_root, round_num)

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
        return rounds.create_next_round_dir(self.evidence_root)

    def list_rounds(self) -> List[Path]:
        """List all round directories."""
        return rounds.list_round_dirs(self.evidence_root)

    # -------------------------------------------------------------------------
    # Bundle I/O (SINGLE SOURCE)
    # -------------------------------------------------------------------------

    def read_bundle(self, round_num: Optional[int] = None) -> Dict[str, Any]:
        """Read bundle summary using configured filename.

        This is the SINGLE SOURCE for reading bundle summaries.
        """
        round_dir = self.ensure_round(round_num)
        bundle_path = round_dir / self.bundle_filename

        if not bundle_path.exists():
            return {}
        try:
            return read_json(bundle_path)
        except Exception:
            # Invalid JSON is treated as missing
            return {}

    def write_bundle(self, data: Dict[str, Any], round_num: Optional[int] = None) -> None:
        """Write bundle summary using configured filename.

        This is the SINGLE SOURCE for writing bundle summaries.
        """
        round_dir = self.ensure_round(round_num)
        bundle_path = round_dir / self.bundle_filename

        try:
            write_json_atomic(bundle_path, data)
        except Exception as e:
            raise EvidenceError(
                f"Failed to write bundle summary to {bundle_path}: {e}"
            ) from e

    # -------------------------------------------------------------------------
    # Implementation Report I/O (SINGLE SOURCE)
    # -------------------------------------------------------------------------

    def read_implementation_report(self, round_num: Optional[int] = None) -> Dict[str, Any]:
        """Read implementation report using configured filename.

        This is the SINGLE SOURCE for reading implementation reports.
        """
        round_dir = self.ensure_round(round_num)
        report_path = round_dir / self.implementation_filename

        if not report_path.exists():
            return {}
        try:
            return read_json(report_path)
        except Exception:
            return {}

    def write_implementation_report(
        self, data: Dict[str, Any], round_num: Optional[int] = None
    ) -> None:
        """Write implementation report using configured filename.

        This is the SINGLE SOURCE for writing implementation reports.
        """
        round_dir = self.ensure_round(round_num)
        report_path = round_dir / self.implementation_filename

        try:
            write_json_atomic(report_path, data)
        except Exception as e:
            raise EvidenceError(
                f"Failed to write implementation report to {report_path}: {e}"
            ) from e

    # -------------------------------------------------------------------------
    # Validator Report I/O (SINGLE SOURCE)
    # -------------------------------------------------------------------------

    def read_validator_report(
        self, validator_name: str, round_num: Optional[int] = None
    ) -> Dict[str, Any]:
        """Read validator report.

        This is the SINGLE SOURCE for reading validator reports.
        """
        round_dir = self.ensure_round(round_num)
        return reports.read_validator_report(round_dir, validator_name)

    def write_validator_report(
        self, validator_name: str, data: Dict[str, Any], round_num: Optional[int] = None
    ) -> None:
        """Write validator report.

        This is the SINGLE SOURCE for writing validator reports.
        """
        round_dir = self.ensure_round(round_num)
        try:
            reports.write_validator_report(round_dir, validator_name, data)
        except Exception as e:
            # Keep EvidenceService as the user-facing exception boundary.
            raise EvidenceError(f"Failed to write validator report: {e}") from e

    def list_validator_reports(self, round_num: Optional[int] = None) -> List[Path]:
        """List all validator report files in a round.

        This is the SINGLE SOURCE for listing validator reports.
        """
        round_dir = self.ensure_round(round_num)
        return reports.list_validator_reports(round_dir)

    # -------------------------------------------------------------------------
    # Metadata management
    # -------------------------------------------------------------------------

    def update_metadata(self, round_num: Optional[int] = None) -> None:
        """Update task evidence metadata.json.

        Creates or updates metadata.json in the evidence root directory.

        Args:
            round_num: Round number to set as current (defaults to latest)
        """
        current = round_num or self.get_current_round() or 1
        metadata = {
            "task_id": self.task_id,
            "currentRound": current,
            "round": current,
        }
        metadata_path = self.evidence_root / "metadata.json"
        self.evidence_root.mkdir(parents=True, exist_ok=True)
        write_json_atomic(metadata_path, metadata)

    def create_qa_brief(
        self,
        session_id: Optional[str] = None,
        round_num: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create qa-brief.json for a round.

        Creates a new QA brief file and updates the metadata.
        This is the canonical method for creating QA briefs.

        Args:
            session_id: Optional session context
            round_num: Optional round number (creates next round if not specified)

        Returns:
            The created QA brief dict
        """
        # Ensure round directory exists
        if round_num is None:
            # Create next round
            round_dir = self.create_next_round()
            rn = self.get_current_round() or 1
        else:
            round_dir = self.ensure_round(round_num)
            rn = round_num

        brief: Dict[str, Any] = {
            "task_id": self.task_id,
            "session_id": session_id,
            "round": rn,
            "created_at": None,
            "status": "pending",
            "validators": [],
            "evidence": [],
        }
        write_json_atomic(round_dir / "qa-brief.json", brief)
        self.update_metadata(rn)
        return brief
