"""Evidence operations manager for Edison framework.

This module centralizes all evidence directory and report management patterns
to eliminate duplication across validation and implementation scripts.

Key features:
- Evidence round directory management (creation, detection, listing)
- Report file I/O (bundle summaries, implementation reports, validator reports)
- Safe JSON operations with atomic writes
- Integration with pathlib for consistent path resolution

See `{management_dir}/qa/EDISON_NO_LEGACY_POLICY.md` for configuration and migration rules (management_dir defaults to .project).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from ..paths import PathResolver, EdisonPathError
from ..paths.management import get_management_paths
from ..file_io.utils import read_json_safe, write_json_safe


class EvidenceError(Exception):
    """Raised when evidence operations fail.

    This includes:
    - Evidence directory not found
    - Invalid report format
    - Failed to create round directory
    - Report file not found
    """
    pass


class EvidenceManager:
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

    def __init__(self, task_id: str, project_root: Optional[Path] = None):
        """Initialize evidence manager for a task.

        Args:
            task_id: Task ID (e.g., "task-100" or "100")
            project_root: Optional project root; defaults to PathResolver resolution

        Examples:
            >>> mgr = EvidenceManager("task-100")
            >>> assert mgr.task_id == "task-100"
        """
        self.task_id = task_id
        root = project_root or PathResolver.resolve_project_root()
        mgmt_paths = get_management_paths(root)
        self.base_dir = mgmt_paths.get_qa_root() / "validation-evidence" / task_id

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
        # read_json_safe provides FileNotFoundError + JSON errors
        return read_json_safe(bundle_path)

    @staticmethod
    def read_implementation_report(task_id: str) -> Dict[str, Any]:
        """Static helper: read implementation-report.json for latest round.

        Raises:
            FileNotFoundError: If evidence directory or report file missing.
            ValueError: If JSON is invalid (json.JSONDecodeError).
        """
        latest = EvidenceManager.get_latest_round_dir(task_id)
        report_path = latest / "implementation-report.json"
        return read_json_safe(report_path)

    # ------------------------------------------------------------------
    # Instance API (richer operations, tolerant semantics)
    # ------------------------------------------------------------------
    def _get_latest_round_dir(self) -> Optional[Path]:
        """Get latest round-N directory.

        Returns None if no rounds exist yet.

        Returns:
            Optional[Path]: Latest round directory, or None if no rounds

        Examples:
            >>> mgr = EvidenceManager("task-100")
            >>> latest = mgr._get_latest_round_dir()
            >>> if latest:
            ...     print(f"Latest round: {latest.name}")
        """
        if not self.base_dir.exists():
            return None

        rounds = sorted(
            [p for p in self.base_dir.glob("round-*") if p.is_dir()],
            key=lambda p: int(p.name.split("-")[1]) if p.name.split("-")[1].isdigit() else 0
        )

        return rounds[-1] if rounds else None

    def get_round_number(self, round_dir: Path) -> int:
        """Extract round number from round directory name.

        Args:
            round_dir: Path to round directory (e.g., .../round-2)

        Returns:
            int: Round number

        Raises:
            EvidenceError: If directory name is not in round-N format
        """
        try:
            return int(round_dir.name.split("-")[1])
        except (IndexError, ValueError) as e:
            raise EvidenceError(
                f"Invalid round directory name: {round_dir.name}. "
                "Expected format: round-N"
            ) from e

    def create_next_round_dir(self) -> Path:
        """Create next round-{N+1} directory and return path.

        If no rounds exist, creates round-1.
        If rounds exist, creates round-{max+1}.

        Returns:
            Path: Newly created round directory

        Raises:
            EvidenceError: If failed to create directory

        Examples:
            >>> mgr = EvidenceManager("task-100")
            >>> round_1 = mgr.create_next_round_dir()
            >>> assert round_1.name == "round-1"
            >>> round_2 = mgr.create_next_round_dir()
            >>> assert round_2.name == "round-2"
        """
        latest = self._get_latest_round_dir()

        if latest is None:
            next_num = 1
        else:
            next_num = self.get_round_number(latest) + 1

        next_dir = self.base_dir / f"round-{next_num}"

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

    def _read_bundle_summary(self, round: Optional[int] = None) -> Dict[str, Any]:
        """Read bundle-approved.json from specified round (or latest).

        Returns empty dict if file doesn't exist (not an error condition).

        Args:
            round: Specific round number, or None for latest

        Returns:
            Dict[str, Any]: Bundle summary data, or {} if not found

        Examples:
            >>> mgr = EvidenceManager("task-100")
            >>> bundle = mgr.read_bundle_summary()
            >>> if bundle.get("approved"):
            ...     print("Bundle approved!")
        """
        round_dir = self._resolve_round_dir(round)
        if round_dir is None:
            return {}

        bundle_path = round_dir / "bundle-approved.json"
        if not bundle_path.exists():
            return {}

        try:
            return read_json_safe(bundle_path)
        except Exception:
            # Invalid JSON is treated as missing
            return {}

    def _read_implementation_report(self, round: Optional[int] = None) -> Dict[str, Any]:
        """Read implementation-report.json.

        Returns {} if not found.

        Args:
            round: Specific round number, or None for latest

        Returns:
            Dict[str, Any]: Implementation report data, or {} if not found

        Examples:
            >>> mgr = EvidenceManager("task-100")
            >>> report = mgr.read_implementation_report()
            >>> if report:
            ...     print(f"Implemented by: {report.get('implementer')}")
        """
        round_dir = self._resolve_round_dir(round)
        if round_dir is None:
            return {}

        report_path = round_dir / "implementation-report.json"
        if not report_path.exists():
            return {}

        try:
            return read_json_safe(report_path)
        except Exception:
            return {}

    def read_validator_report(
        self,
        validator_name: str,
        round: Optional[int] = None
    ) -> Dict[str, Any]:
        """Read validator-{name}-report.json.

        Returns {} if not found.

        Args:
            validator_name: Validator name (e.g., "claude-global", "codex-security")
            round: Specific round number, or None for latest

        Returns:
            Dict[str, Any]: Validator report data, or {} if not found

        Examples:
            >>> mgr = EvidenceManager("task-100")
            >>> report = mgr.read_validator_report("claude-global")
            >>> if report:
            ...     verdict = report.get("validationVerdict", {}).get("verdict")
        """
        round_dir = self._resolve_round_dir(round)
        if round_dir is None:
            return {}

        # Handle both "validator-{name}-report.json" and "{name}-report.json" formats
        if validator_name.startswith("validator-"):
            report_path = round_dir / f"{validator_name}-report.json"
        else:
            report_path = round_dir / f"validator-{validator_name}-report.json"

        if not report_path.exists():
            return {}

        try:
            return read_json_safe(report_path)
        except Exception:
            return {}

    def write_bundle_summary(
        self,
        data: Dict[str, Any],
        round: Optional[int] = None
    ) -> None:
        """Write bundle-approved.json to specified round.

        Args:
            data: Bundle summary data to write
            round: Specific round number, or None for latest

        Raises:
            EvidenceError: If round directory doesn't exist

        Examples:
            >>> mgr = EvidenceManager("task-100")
            >>> mgr.write_bundle_summary({
            ...     "approved": True,
            ...     "taskId": "task-100",
            ...     "validators": ["claude-global"]
            ... })
        """
        round_dir = self._resolve_round_dir(round)
        if round_dir is None:
            raise EvidenceError(
                f"Cannot write bundle summary: no rounds exist for task {self.task_id}"
            )

        bundle_path = round_dir / "bundle-approved.json"
        try:
            write_json_safe(bundle_path, data)
        except Exception as e:
            raise EvidenceError(
                f"Failed to write bundle summary to {bundle_path}: {e}"
            ) from e

    def write_implementation_report(
        self,
        data: Dict[str, Any],
        round: Optional[int] = None
    ) -> None:
        """Write implementation-report.json to specified round.

        Args:
            data: Implementation report data to write
            round: Specific round number, or None for latest

        Raises:
            EvidenceError: If round directory doesn't exist
        """
        round_dir = self._resolve_round_dir(round)
        if round_dir is None:
            raise EvidenceError(
                f"Cannot write implementation report: no rounds exist for task {self.task_id}"
            )

        report_path = round_dir / "implementation-report.json"
        try:
            write_json_safe(report_path, data)
        except Exception as e:
            raise EvidenceError(
                f"Failed to write implementation report to {report_path}: {e}"
            ) from e

    def write_validator_report(
        self,
        validator_name: str,
        data: Dict[str, Any],
        round: Optional[int] = None
    ) -> None:
        """Write validator-{name}-report.json to specified round.

        Args:
            validator_name: Validator name
            data: Validator report data to write
            round: Specific round number, or None for latest

        Raises:
            EvidenceError: If round directory doesn't exist
        """
        round_dir = self._resolve_round_dir(round)
        if round_dir is None:
            raise EvidenceError(
                f"Cannot write validator report: no rounds exist for task {self.task_id}"
            )

        # Normalize validator name
        if validator_name.startswith("validator-"):
            report_path = round_dir / f"{validator_name}-report.json"
        else:
            report_path = round_dir / f"validator-{validator_name}-report.json"

        try:
            write_json_safe(report_path, data)
        except Exception as e:
            raise EvidenceError(
                f"Failed to write validator report to {report_path}: {e}"
            ) from e

    def list_validator_reports(self, round: Optional[int] = None) -> List[Path]:
        """List all validator-*-report.json files in round directory.

        Args:
            round: Specific round number, or None for latest

        Returns:
            List[Path]: List of validator report paths (sorted by name)

        Examples:
            >>> mgr = EvidenceManager("task-100")
            >>> reports = mgr.list_validator_reports()
            >>> for report in reports:
            ...     print(f"Found: {report.name}")
        """
        round_dir = self._resolve_round_dir(round)
        if round_dir is None or not round_dir.exists():
            return []

        reports = sorted(round_dir.glob("validator-*-report.json"))
        return reports

    def list_rounds(self) -> List[Path]:
        """List all round directories for this task.

        Returns:
            List[Path]: Sorted list of round directories (oldest to newest)

        Examples:
            >>> mgr = EvidenceManager("task-100")
            >>> rounds = mgr.list_rounds()
            >>> for round_dir in rounds:
            ...     print(f"Round: {round_dir.name}")
        """
        if not self.base_dir.exists():
            return []

        rounds = sorted(
            [p for p in self.base_dir.glob("round-*") if p.is_dir()],
            key=lambda p: int(p.name.split("-")[1]) if p.name.split("-")[1].isdigit() else 0
        )

        return rounds

    def _resolve_round_dir(self, round: Optional[int] = None) -> Optional[Path]:
        """Internal helper to resolve round directory.

        Args:
            round: Specific round number, or None for latest

        Returns:
            Optional[Path]: Round directory, or None if doesn't exist
        """
        if round is not None:
            round_dir = self.base_dir / f"round-{round}"
            return round_dir if round_dir.exists() else None
        else:
            return self._get_latest_round_dir()


def _task_evidence_root(task_id: str) -> Path:
    root = PathResolver.resolve_project_root()
    mgmt_paths = get_management_paths(root)
    return mgmt_paths.get_qa_root() / "validation-evidence" / task_id


def missing_evidence_blockers(task_id: str) -> List[Dict[str, Any]]:
    """Return automation blockers for missing evidence for a given task."""
    evidence_root = _task_evidence_root(task_id)
    project_root = PathResolver.resolve_project_root()
    try:
        evidence_rel = str(evidence_root.relative_to(project_root))
    except Exception:
        evidence_rel = str(evidence_root)
    if not evidence_root.exists():
        return [
            {
                "kind": "automation",
                "recordId": task_id,
                "message": f"Evidence dir missing: {evidence_rel}",
                "fixCmd": ["mkdir", "-p", f"{evidence_rel}/round-1"],
            }
        ]
    rounds = sorted(
        [p for p in evidence_root.glob("round-*") if p.is_dir()],
        key=lambda p: p.name,
    )
    if not rounds:
        return [
            {
                "kind": "automation",
                "recordId": task_id,
                "message": "No round-* directories present",
                "fixCmd": ["mkdir", "-p", f"{evidence_rel}/round-1"],
            }
        ]
    latest = rounds[-1]
    needed = {"command-type-check.txt", "command-lint.txt", "command-test.txt", "command-build.txt"}
    present = {p.name for p in latest.iterdir() if p.is_file()}
    missing = sorted(needed - present)
    if not missing:
        return []
    return [
        {
            "kind": "automation",
            "recordId": task_id,
            "message": f"Missing evidence files in {latest.name}: {', '.join(missing)}",
        }
    ]


def read_validator_jsons(task_id: str) -> Dict[str, Any]:
    """Return latest validator-* JSON reports for a task."""
    root = _task_evidence_root(task_id)
    out: Dict[str, Any] = {"round": None, "reports": []}
    if not root.exists():
        return out
    rounds = sorted([p for p in root.glob("round-*") if p.is_dir()], key=lambda p: p.name)
    if not rounds:
        return out
    latest = rounds[-1]
    out["round"] = latest.name
    for p in latest.glob("validator-*-report.json"):
        try:
            data = read_json_safe(p)
            out["reports"].append(data)
        except Exception:
            continue
    return out


def _latest_round_dir(task_id: str) -> Optional[Path]:
    root = _task_evidence_root(task_id)
    if not root.exists():
        return None
    rounds = [p for p in root.glob("round-*") if p.is_dir()]
    if not rounds:
        return None
    return sorted(rounds, key=lambda p: p.name)[-1]


def load_impl_followups(task_id: str) -> List[Dict[str, Any]]:
    """Load follow-up tasks from implementation-report.json for latest round."""
    rd = _latest_round_dir(task_id)
    if not rd:
        return []
    rp = rd / "implementation-report.json"
    if not rp.exists():
        return []
    try:
        data = read_json_safe(rp)
    except Exception:
        return []
    out: List[Dict[str, Any]] = []
    for it in data.get("followUpTasks", []) or []:
        out.append(
            {
                "source": "implementation",
                "title": it.get("title"),
                "blockingBeforeValidation": bool(it.get("blockingBeforeValidation", False)),
                "claimNow": bool(it.get("claimNow", False)),
                "category": it.get("category"),
            }
        )
    return out


def load_bundle_followups(task_id: str) -> List[Dict[str, Any]]:
    """Load non-blocking follow-ups from bundle-approved.json for latest round."""
    rd = _latest_round_dir(task_id)
    if not rd:
        return []
    bp = rd / "bundle-approved.json"
    if not bp.exists():
        return []
    try:
        data = read_json_safe(bp)
    except Exception:
        return []
    out: List[Dict[str, Any]] = []
    for it in data.get("nonBlockingFollowUps", []) or []:
        out.append(
            {
                "source": "validator",
                "title": it.get("title"),
                "blockingBeforeValidation": False,
                "claimNow": False,
                "category": it.get("category"),
            }
        )
    return out


# Convenience functions for common operations

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


# Helper functions from the original qa/evidence.py

def get_evidence_dir(task_id: str) -> Path:
    """Return the canonical evidence directory for a task."""
    return _task_evidence_root(task_id)


def get_latest_round(task_id: str) -> Optional[int]:
    """Return the latest evidence round number for a task, or None.

    Resolution order mirrors the legacy QA scripts:
    1. Prefer ``metadata.json`` when it contains a valid ``currentRound`` or
       ``round`` integer and the corresponding directory exists.
    2. Fall back to the highest numeric ``round-N`` directory under the
       task's evidence root.
    """
    root = _task_evidence_root(task_id)
    if not root.exists():
        return None

    meta = root / "metadata.json"
    try:
        if meta.exists():
            data = read_json_safe(meta)
            if isinstance(data, dict):
                for key in ("currentRound", "round"):
                    value = data.get(key)
                    if isinstance(value, int):
                        candidate = root / f"round-{value}"
                        if candidate.is_dir():
                            return int(value)
    except Exception:
        # Fall back to scanning directories when metadata is missing/invalid.
        pass

    rounds = [p for p in root.glob("round-*") if p.is_dir()]
    if not rounds:
        return None

    def _key(p: Path) -> tuple[int, str]:
        try:
            return (int(p.name.split("-", 1)[1]), p.name)
        except Exception:
            return (0, p.name)

    latest = sorted(rounds, key=_key)[-1]
    # We know latest follows round-N naming; extract N.
    try:
        return int(latest.name.split("-", 1)[1])
    except Exception:
        return None


def get_implementation_report_path(task_id: str, round_num: int) -> Path:
    """Return the path to the implementation report for a given round."""
    return get_evidence_dir(task_id) / f"round-{round_num}" / "implementation-report.json"


def list_evidence_files(base: Path) -> List[Path]:
    """
    Return a sorted list of evidence files underneath ``base``.

    Only regular files are returned; directories are ignored.
    """
    base = Path(base)
    if not base.exists():
        return []
    return sorted(p for p in base.rglob("*") if p.is_file())


def has_required_evidence(base: Path, required: Iterable[str]) -> bool:
    """
    Return True when all required evidence file patterns are present.

    Args:
        base: Evidence root directory.
        required: Iterable of glob-style patterns relative to ``base``.
    """
    base = Path(base)
    files = {str(p.relative_to(base)) for p in list_evidence_files(base)}
    for pattern in required:
        matched = any(Path(name).match(pattern) for name in files)
        if not matched:
            return False
    return True


__all__ = [
    "EvidenceError",
    "EvidenceManager",
    "get_evidence_manager",
    "missing_evidence_blockers",
    "read_validator_jsons",
    "load_impl_followups",
    "load_bundle_followups",
    "_task_evidence_root",
    # Helper functions
    "get_evidence_dir",
    "get_latest_round",
    "get_implementation_report_path",
    "list_evidence_files",
    "has_required_evidence",
]
