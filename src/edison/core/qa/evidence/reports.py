"""Validator report I/O utilities.

Validator reports are per-round JSON files following a fixed naming convention:

    validator-<name>-report.json

This module is intentionally small and does not depend on external services.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from edison.core.utils.io import read_json, write_json_atomic


_VALIDATOR_PREFIX = "validator-"
_REPORT_SUFFIX = "-report.json"


def _normalize_validator_name(validator_name: str) -> str:
    name = validator_name.strip()
    if name.startswith(_VALIDATOR_PREFIX):
        name = name[len(_VALIDATOR_PREFIX) :]
    return name


def validator_report_path(round_dir: Path, validator_name: str) -> Path:
    """Return the expected report path for a validator in a round dir."""
    normalized = _normalize_validator_name(validator_name)
    return round_dir / f"{_VALIDATOR_PREFIX}{normalized}{_REPORT_SUFFIX}"


def write_validator_report(round_dir: Path, validator_name: str, data: Dict[str, Any]) -> Path:
    """Write a validator report JSON file.

    Args:
        round_dir: Round evidence directory.
        validator_name: Validator id/name (with or without the 'validator-' prefix).
        data: JSON-serializable dict.

    Returns:
        Path to the written report file.
    """
    round_dir.mkdir(parents=True, exist_ok=True)
    path = validator_report_path(round_dir, validator_name)
    write_json_atomic(path, data)
    return path


def read_validator_report(round_dir: Path, validator_name: str) -> Dict[str, Any]:
    """Read a validator report JSON file.

    Returns an empty dict if the report does not exist or is invalid JSON.
    """
    path = validator_report_path(round_dir, validator_name)
    if not path.exists():
        return {}

    try:
        data = read_json(path)
    except Exception:
        return {}

    return data if isinstance(data, dict) else {}


def list_validator_reports(round_dir: Path) -> List[Path]:
    """List validator report files in a round directory."""
    if not round_dir.exists():
        return []

    files = list(round_dir.glob(f"{_VALIDATOR_PREFIX}*{_REPORT_SUFFIX}"))
    return sorted(files, key=lambda p: p.name)

