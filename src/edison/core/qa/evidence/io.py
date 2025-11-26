"""Evidence report I/O operations."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.utils.io import read_json, write_json_atomic
from .exceptions import EvidenceError


def read_bundle_summary(round_dir: Path) -> Dict[str, Any]:
    """Read bundle-approved.json from round directory."""
    bundle_path = round_dir / "bundle-approved.json"
    if not bundle_path.exists():
        return {}
    try:
        return read_json(bundle_path)
    except Exception:
        # Invalid JSON is treated as missing
        return {}


def read_implementation_report(round_dir: Path) -> Dict[str, Any]:
    """Read implementation-report.json from round directory."""
    report_path = round_dir / "implementation-report.json"
    if not report_path.exists():
        return {}
    try:
        return read_json(report_path)
    except Exception:
        return {}


def read_validator_report(round_dir: Path, validator_name: str) -> Dict[str, Any]:
    """Read validator-{name}-report.json from round directory."""
    if validator_name.startswith("validator-"):
        report_path = round_dir / f"{validator_name}-report.json"
    else:
        report_path = round_dir / f"validator-{validator_name}-report.json"

    if not report_path.exists():
        return {}
    try:
        return read_json(report_path)
    except Exception:
        return {}


def write_bundle_summary(round_dir: Path, data: Dict[str, Any]) -> None:
    """Write bundle-approved.json to round directory."""
    bundle_path = round_dir / "bundle-approved.json"
    try:
        write_json_atomic(bundle_path, data)
    except Exception as e:
        raise EvidenceError(
            f"Failed to write bundle summary to {bundle_path}: {e}"
        ) from e


def write_implementation_report(round_dir: Path, data: Dict[str, Any]) -> None:
    """Write implementation-report.json to round directory."""
    report_path = round_dir / "implementation-report.json"
    try:
        write_json_atomic(report_path, data)
    except Exception as e:
        raise EvidenceError(
            f"Failed to write implementation report to {report_path}: {e}"
        ) from e


def write_validator_report(
    round_dir: Path, validator_name: str, data: Dict[str, Any]
) -> None:
    """Write validator-{name}-report.json to round directory."""
    if validator_name.startswith("validator-"):
        report_path = round_dir / f"{validator_name}-report.json"
    else:
        report_path = round_dir / f"validator-{validator_name}-report.json"

    try:
        write_json_atomic(report_path, data)
    except Exception as e:
        raise EvidenceError(
            f"Failed to write validator report to {report_path}: {e}"
        ) from e


def list_validator_reports(round_dir: Path) -> List[Path]:
    """List all validator-*-report.json files in round directory."""
    return sorted(round_dir.glob("validator-*-report.json"))
