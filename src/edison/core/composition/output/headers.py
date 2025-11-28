"""Shared helpers for auto-generated file headers."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from edison import __version__ as package_version
from edison.core.config import ConfigManager
from edison.core.utils.time import utc_timestamp
from edison.data import get_data_path
from ..path_utils import resolve_project_dir_placeholders


def load_header_template(cfg_mgr: ConfigManager, config: Dict[str, Any]) -> str:
    """Retrieve the configured header template, falling back to bundled defaults."""
    header_template = (config.get("composition") or {}).get("generatedFileHeader") or ""
    if header_template.strip():
        return header_template.strip()

    fallback_path = get_data_path("config", "composition.yaml")
    fallback_cfg = cfg_mgr.load_yaml(fallback_path) if fallback_path.exists() else {}
    header_template = (fallback_cfg.get("composition") or {}).get("generatedFileHeader") or ""

    if not header_template.strip():
        raise ValueError("composition.generatedFileHeader must be configured")
    return header_template.strip()


def resolve_version(cfg_mgr: ConfigManager, config: Dict[str, Any]) -> str:
    """Resolve Edison version from YAML config or bundled defaults."""
    version = (config.get("edison") or {}).get("version")
    if version:
        return str(version)

    defaults_path = get_data_path("config", "defaults.yaml")
    defaults_cfg = cfg_mgr.load_yaml(defaults_path) if defaults_path.exists() else {}
    version = (defaults_cfg.get("edison") or {}).get("version")
    if version:
        return str(version)

    return str(package_version)


def build_generated_header(
    template_name: str,
    *,
    config: Optional[ConfigManager] = None,
    generated_at: Optional[datetime] = None,
    target_path: Optional[Path] = None,
) -> str:
    """Render the configured auto-generation header with runtime values."""
    cfg_mgr = config or ConfigManager()
    cfg = cfg_mgr.load_config(validate=False)

    header_template = load_header_template(cfg_mgr, cfg)
    version = resolve_version(cfg_mgr, cfg)
    timestamp = generated_at.isoformat() if generated_at else utc_timestamp()

    replacements = {
        "{{version}}": version,
        "{{template}}": template_name,
        "{{timestamp}}": timestamp,
    }
    project_dir = cfg_mgr.project_config_dir.parent

    header = header_template
    for marker, value in replacements.items():
        header = header.replace(marker, value)

    header = resolve_project_dir_placeholders(
        header,
        project_dir=project_dir,
        target_path=target_path,
        repo_root=cfg_mgr.repo_root,
    )

    return f"{header.strip()}\n\n"


__all__ = ["build_generated_header", "load_header_template", "resolve_version"]



