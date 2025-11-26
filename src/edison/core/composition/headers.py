"""Shared helpers for auto-generated file headers."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from edison.core.config import ConfigManager


def _extract_header_template(config: Dict[str, Any]) -> str:
    header_template = (config.get("composition") or {}).get("generatedFileHeader") or ""
    if not header_template.strip():
        raise ValueError("composition.generatedFileHeader must be configured")
    return header_template.strip()


def _extract_version(config: Dict[str, Any]) -> str:
    version = (config.get("edison") or {}).get("version")
    if not version:
        raise ValueError("edison.version must be configured")
    return str(version)


def build_generated_header(
    template_name: str,
    *,
    config: Optional[ConfigManager] = None,
    generated_at: Optional[datetime] = None,
) -> str:
    """Render the configured auto-generation header with runtime values."""
    cfg_mgr = config or ConfigManager()
    cfg = cfg_mgr.load_config(validate=False)

    header_template = _extract_header_template(cfg)
    version = _extract_version(cfg)
    timestamp = (generated_at or datetime.now()).isoformat()

    replacements = {
        "{{version}}": version,
        "{{template_name}}": template_name,
        "{{timestamp}}": timestamp,
    }

    header = header_template
    for marker, value in replacements.items():
        header = header.replace(marker, value)

    return f"{header.strip()}\n\n"


__all__ = ["build_generated_header"]
