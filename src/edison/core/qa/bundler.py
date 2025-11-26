"""Validation bundle helpers (summary path + I/O)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from ..legacy_guard import enforce_no_legacy_project_root
from ..file_io.utils import (
    write_json_safe as io_write_json_safe,
    read_json_safe as io_read_json_safe,
    ensure_dir,
)
from . import config as qa_config
from . import evidence


enforce_no_legacy_project_root("lib.qa.bundler")


def bundle_summary_filename(config: Optional[Dict[str, Any]] = None) -> str:
    cfg = config or qa_config.load_validation_config()
    if isinstance(cfg, dict) and "artifactPaths" not in cfg and "validation" in cfg:
        cfg = cfg.get("validation", {}) or {}
    paths = cfg.get("artifactPaths", {}) if isinstance(cfg, dict) else {}
    name = paths.get("bundleSummaryFile") if isinstance(paths, dict) else None
    if not name:
        raise RuntimeError(
            "validation.artifactPaths.bundleSummaryFile missing in configuration"
        )
    return str(name)


def bundle_summary_path(task_id: str, round_num: int, *, config: Optional[Dict[str, Any]] = None) -> Path:
    filename = bundle_summary_filename(config)
    base = evidence.get_evidence_dir(task_id)
    return base / f"round-{int(round_num)}" / filename


def load_bundle_summary(task_id: str, round_num: int, *, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    path = bundle_summary_path(task_id, round_num, config=config)
    if not path.exists():
        return {}
    try:
        data = io_read_json_safe(path)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def write_bundle_summary(task_id: str, round_num: int, summary: Dict[str, Any], *, config: Optional[Dict[str, Any]] = None) -> Path:
    path = bundle_summary_path(task_id, round_num, config=config)
    ensure_dir(path.parent)
    io_write_json_safe(path, summary)
    return path


__all__ = [
    "bundle_summary_filename",
    "bundle_summary_path",
    "load_bundle_summary",
    "write_bundle_summary",
]
