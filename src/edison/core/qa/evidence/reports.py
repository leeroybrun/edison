"""Validator report I/O utilities.

Validator reports are per-round structured files following a fixed naming convention:

    validator-<name>-report.md

They are written as Markdown with YAML frontmatter (machine-readable + LLM-readable).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .report_io import read_structured_report, write_structured_report


_VALIDATOR_PREFIX = "validator-"
_REPORT_SUFFIX = "-report.md"


def _normalize_validator_name(validator_name: str) -> str:
    name = validator_name.strip()
    if name.startswith(_VALIDATOR_PREFIX):
        name = name[len(_VALIDATOR_PREFIX) :]
    return name


def validator_report_path(round_dir: Path, validator_name: str) -> Path:
    """Return the expected report path for a validator in a round dir."""
    normalized = _normalize_validator_name(validator_name)
    return round_dir / f"{_VALIDATOR_PREFIX}{normalized}{_REPORT_SUFFIX}"

def _validator_id_from_path(path: Path) -> str:
    stem = path.stem  # validator-<id>-report
    if stem.startswith(_VALIDATOR_PREFIX):
        stem = stem[len(_VALIDATOR_PREFIX) :]
    if stem.endswith("-report"):
        stem = stem[: -len("-report")]
    return stem


def write_validator_report(round_dir: Path, validator_name: str, data: Dict[str, Any]) -> Path:
    """Write a validator report file (Markdown with YAML frontmatter).

    Args:
        round_dir: Round evidence directory.
        validator_name: Validator id/name (with or without the 'validator-' prefix).
        data: Dict payload (serialized as YAML frontmatter).

    Returns:
        Path to the written report file.
    """
    round_dir.mkdir(parents=True, exist_ok=True)
    path = validator_report_path(round_dir, validator_name)
    write_structured_report(path, data)
    return path


def read_validator_report(round_dir: Path, validator_name: str) -> Dict[str, Any]:
    """Read a validator report file.

    Returns an empty dict if the report does not exist or is invalid.
    """
    return read_structured_report(validator_report_path(round_dir, validator_name))


def list_validator_reports(round_dir: Path) -> List[Path]:
    """List validator report files in a round directory."""
    if not round_dir.exists():
        return []

    files = list(round_dir.glob(f"{_VALIDATOR_PREFIX}*{_REPORT_SUFFIX}"))
    return sorted(files, key=lambda p: p.name)
