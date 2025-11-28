"""Evidence report management with configuration support."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.config.domains.qa import QAConfig
from . import io


def get_report_filenames(repo_root: Optional[Path] = None) -> Dict[str, str]:
    """Get configured filenames for reports."""
    config = QAConfig(repo_root=repo_root)
    # Access artifactPaths from the validation config section
    # artifactPaths is under validation: in the YAML config
    paths = config.validation_config.get("artifactPaths", {})
    if not isinstance(paths, dict):
        paths = {}

    return {
        "bundle": paths.get("bundleSummaryFile", "bundle-approved.json"),
        "implementation": paths.get("implementationReportFile", "implementation-report.json"),
    }


def read_bundle_report(round_dir: Path, repo_root: Optional[Path] = None) -> Dict[str, Any]:
    """Read bundle report using configured filename."""
    filenames = get_report_filenames(repo_root)
    return io.read_bundle_summary(round_dir, filename=filenames["bundle"])


def write_bundle_report(
    round_dir: Path, data: Dict[str, Any], repo_root: Optional[Path] = None
) -> None:
    """Write bundle report using configured filename."""
    filenames = get_report_filenames(repo_root)
    io.write_bundle_summary(round_dir, data, filename=filenames["bundle"])


def read_implementation_report(
    round_dir: Path, repo_root: Optional[Path] = None
) -> Dict[str, Any]:
    """Read implementation report using configured filename."""
    filenames = get_report_filenames(repo_root)
    return io.read_implementation_report(round_dir, filename=filenames["implementation"])


def write_implementation_report(
    round_dir: Path, data: Dict[str, Any], repo_root: Optional[Path] = None
) -> None:
    """Write implementation report using configured filename."""
    filenames = get_report_filenames(repo_root)
    io.write_implementation_report(round_dir, data, filename=filenames["implementation"])


def read_validator_report(round_dir: Path, validator_name: str) -> Dict[str, Any]:
    """Read validator report (wraps io.read_validator_report)."""
    return io.read_validator_report(round_dir, validator_name)


def write_validator_report(
    round_dir: Path, validator_name: str, data: Dict[str, Any]
) -> None:
    """Write validator report (wraps io.write_validator_report)."""
    io.write_validator_report(round_dir, validator_name, data)


def list_validator_reports(round_dir: Path) -> List[Path]:
    """List validator reports (wraps io.list_validator_reports)."""
    return io.list_validator_reports(round_dir)
