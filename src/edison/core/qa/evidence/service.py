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

from edison.core.utils.io import write_json_atomic
from edison.core.utils.text import parse_frontmatter, strip_frontmatter_block
from edison.data import get_data_path
from .._utils import get_qa_root_path
from .exceptions import EvidenceError
from . import rounds
from . import reports
from .report_io import read_structured_report, write_structured_report


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
            "bundle": paths.get("bundleSummaryFile", "bundle-summary.md"),
            "implementation": paths.get("implementationReportFile", "implementation-report.md"),
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

    def ensure_required_evidence_files(self, round_dir: Path) -> list[Path]:
        """Ensure required evidence marker files exist for a round.

        These files are configured via `validation.evidence.requiredFiles` and are
        used by task/QA guards to enforce evidence completeness. This method
        creates empty placeholders for missing files (idempotent).
        """
        from edison.core.config.domains.qa import QAConfig

        cfg = QAConfig(repo_root=self.project_root)
        required = cfg.get_required_evidence_files()
        created: list[Path] = []

        round_dir.mkdir(parents=True, exist_ok=True)
        for filename in required:
            name = str(filename).strip()
            if not name:
                continue
            path = round_dir / name
            if path.exists():
                continue
            path.write_text("", encoding="utf-8")
            created.append(path)

        return created

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
        if not bundle_path.exists() and self.bundle_filename != "bundle-approved.md":
            legacy = round_dir / "bundle-approved.md"
            if legacy.exists():
                bundle_path = legacy

        return read_structured_report(bundle_path)

    def write_bundle(self, data: Dict[str, Any], round_num: Optional[int] = None) -> None:
        """Write bundle summary using configured filename.

        This is the SINGLE SOURCE for writing bundle summaries.
        """
        round_dir = self.ensure_round(round_num)
        bundle_path = round_dir / self.bundle_filename

        try:
            write_structured_report(bundle_path, data)
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

        return read_structured_report(report_path)

    def write_implementation_report(
        self, data: Dict[str, Any], round_num: Optional[int] = None
    ) -> None:
        """Write implementation report using configured filename.

        This is the SINGLE SOURCE for writing implementation reports.
        """
        round_dir = self.ensure_round(round_num)
        report_path = round_dir / self.implementation_filename

        try:
            # Always write to the configured report path.
            body: str | None = None
            if report_path.exists():
                try:
                    existing_doc = parse_frontmatter(report_path.read_text(encoding="utf-8", errors="strict"))
                    if not str(existing_doc.content or "").strip():
                        body = self._load_implementation_report_template()
                except Exception:
                    body = None
            else:
                body = self._load_implementation_report_template()

            write_structured_report(report_path, data, body=body, preserve_existing_body=True)
        except Exception as e:
            raise EvidenceError(
                f"Failed to write implementation report to {report_path}: {e}"
            ) from e

    def _load_implementation_report_template(self) -> str:
        """Load the composed implementation report template body (fallback to core)."""
        try:
            from edison.core.utils.paths.project import get_project_config_dir
            from edison.core.utils.paths import PathResolver

            repo_root = (self.project_root or PathResolver.resolve_project_root()).resolve()
            project_cfg = get_project_config_dir(repo_root, create=False)
            tpl_path = project_cfg / "_generated" / "templates" / "IMPLEMENTATION_REPORT.md"
            if not tpl_path.exists():
                tpl_path = get_data_path("templates") / "artifacts" / "IMPLEMENTATION_REPORT.md"
            raw = tpl_path.read_text(encoding="utf-8", errors="strict")
            return strip_frontmatter_block(raw)
        except Exception:
            # Fail-open: template is UX-only; evidence/report semantics come from YAML frontmatter.
            return ""

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
