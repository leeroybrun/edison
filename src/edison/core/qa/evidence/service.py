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
from .._utils import get_qa_root_path, sort_round_dirs
from .exceptions import EvidenceError


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

        This is the SINGLE SOURCE for validator report path resolution.
        Handles the validator- prefix normalization.
        """
        if validator_id.startswith("validator-"):
            return round_dir / f"{validator_id}-report.json"
        return round_dir / f"validator-{validator_id}-report.json"

    # -------------------------------------------------------------------------
    # Round management (delegates to internal helpers)
    # -------------------------------------------------------------------------

    def _find_latest_round_dir(self) -> Optional[Path]:
        """Get latest round-N directory."""
        if not self.evidence_root.exists():
            return None

        round_dirs = [p for p in self.evidence_root.glob("round-*") if p.is_dir()]
        rounds = sort_round_dirs(round_dirs)
        return rounds[-1] if rounds else None

    def _get_round_number(self, round_dir: Path) -> int:
        """Extract round number from round directory name."""
        try:
            return int(round_dir.name.split("-")[1])
        except (IndexError, ValueError) as e:
            raise EvidenceError(
                f"Invalid round directory name: {round_dir.name}. "
                "Expected format: round-N"
            ) from e

    def _create_next_round_dir(self) -> Path:
        """Create next round-{N+1} directory and return path."""
        latest = self._find_latest_round_dir()

        if latest is None:
            next_num = 1
        else:
            next_num = self._get_round_number(latest) + 1

        next_dir = self.evidence_root / f"round-{next_num}"

        try:
            next_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            raise EvidenceError(
                f"Round directory already exists: {next_dir}. "
                "This suggests a race condition or duplicate operation."
            )
        except Exception as e:
            raise EvidenceError(
                f"Failed to create round directory {next_dir}: {e}"
            ) from e

        return next_dir

    def _resolve_round_dir(self, round_num: Optional[int] = None) -> Optional[Path]:
        """Resolve round directory by number or latest."""
        if round_num is not None:
            round_dir = self.evidence_root / f"round-{round_num}"
            return round_dir if round_dir.exists() else None
        return self._find_latest_round_dir()

    def ensure_round(self, round_num: Optional[int] = None) -> Path:
        """Ensure a round directory exists.

        If round_num is None, returns the latest round or creates round-1.
        If round_num is provided and matches next/current, ensures it exists.
        """
        if not self.evidence_root.exists():
            self.evidence_root.mkdir(parents=True, exist_ok=True)

        if round_num is None:
            latest = self._find_latest_round_dir()
            if latest:
                return latest
            return self._create_next_round_dir()

        # Specific round requested
        path = self._resolve_round_dir(round_num)
        if path:
            return path

        # If not found, check if it is the next one to support creation via number
        latest = self._find_latest_round_dir()
        next_num = 1
        if latest:
            next_num = self._get_round_number(latest) + 1

        if round_num == next_num:
            return self._create_next_round_dir()

        raise EvidenceError(f"Cannot create round {round_num}. Next available is {next_num}.")

    def get_current_round(self) -> Optional[int]:
        """Get the current round number."""
        latest = self._find_latest_round_dir()
        if latest:
            return self._get_round_number(latest)
        return None

    def get_current_round_dir(self) -> Optional[Path]:
        """Get the current round directory path.

        Returns None if no rounds exist yet.
        """
        return self._find_latest_round_dir()

    def create_next_round(self) -> Path:
        """Create and return the next round directory."""
        if not self.evidence_root.exists():
            self.evidence_root.mkdir(parents=True, exist_ok=True)
        return self._create_next_round_dir()

    def list_rounds(self) -> List[Path]:
        """List all round directories."""
        if not self.evidence_root.exists():
            return []

        round_dirs = [p for p in self.evidence_root.glob("round-*") if p.is_dir()]
        return sort_round_dirs(round_dirs)

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
        report_path = self.get_validator_report_path(round_dir, validator_name)

        if not report_path.exists():
            return {}
        try:
            return read_json(report_path)
        except Exception:
            return {}

    def write_validator_report(
        self, validator_name: str, data: Dict[str, Any], round_num: Optional[int] = None
    ) -> None:
        """Write validator report.

        This is the SINGLE SOURCE for writing validator reports.
        """
        round_dir = self.ensure_round(round_num)
        report_path = self.get_validator_report_path(round_dir, validator_name)

        try:
            write_json_atomic(report_path, data)
        except Exception as e:
            raise EvidenceError(
                f"Failed to write validator report to {report_path}: {e}"
            ) from e

    def list_validator_reports(self, round_num: Optional[int] = None) -> List[Path]:
        """List all validator report files in a round.

        This is the SINGLE SOURCE for listing validator reports.
        """
        round_dir = self.ensure_round(round_num)
        return sorted(round_dir.glob("validator-*-report.json"))

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
