"""Centralized config loading utilities.

This module provides generic utilities for loading and validating config sections
from the unified configuration system.

Usage:
    from edison.core.utils.config import load_config_section, load_validated_section

    # Load a specific config section
    statemachine = load_config_section("statemachine")

    # Load and validate a config section with requirements
    cli_cfg = load_validated_section(
        "cli",
        required_subsections=["json", "table", "confirm", "output"]
    )
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.config.cache import get_cached_config


def load_config_section(
    section_name: str,
    repo_root: Optional[Path] = None,
    required: bool = True
) -> Dict[str, Any]:
    """Load a specific section from config.

    Args:
        section_name: Config section to load (e.g., "statemachine", "tasks", "qa")
        repo_root: Project root path (auto-detected if None)
        required: If True, raise KeyError if section missing

    Returns:
        Config section dict, or empty dict if not required and missing

    Raises:
        KeyError: If section is required but missing

    Example:
        >>> statemachine = load_config_section("statemachine")
        >>> workflow = load_config_section("workflow")
    """
    config = get_cached_config(repo_root=repo_root)

    if section_name not in config:
        if required:
            raise KeyError(f"Config section '{section_name}' not found")
        return {}

    return config.get(section_name, {}) or {}


def _resolve_section_from_config(
    config: Dict[str, Any],
    section_path: str | List[str],
    *,
    required_fields: Optional[List[str]] = None,
    required_subsections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Resolve and validate a config section from the already-loaded config dict."""

    # Navigate to section (handle both string and list paths)
    path_parts = section_path if isinstance(section_path, list) else [section_path]
    current = config
    for part in path_parts:
        if part not in current:
            path_display = ".".join(path_parts)
            raise RuntimeError(
                f"{path_display} configuration section is missing. "
                f"Add '{path_display}' section to your YAML config."
            )
        current = current[part]

    # Validate required fields
    if required_fields:
        missing_fields = [f for f in required_fields if f not in current]
        if missing_fields:
            path_display = ".".join(path_parts)
            raise RuntimeError(
                f"{path_display} configuration missing required fields: {missing_fields}"
            )

    # Validate required subsections
    if required_subsections:
        missing_subsections = [s for s in required_subsections if s not in current]
        if missing_subsections:
            path_display = ".".join(path_parts)
            raise RuntimeError(
                f"{path_display} configuration missing required subsections: {missing_subsections}"
            )

    return current


def load_validated_section(
    section_path: str | List[str],
    *,
    required_fields: Optional[List[str]] = None,
    required_subsections: Optional[List[str]] = None,
    repo_root: Optional[Path] = None
) -> Dict[str, Any]:
    """Load and validate a config section with strict requirements.

    This function provides a centralized way to load config sections with
    validation, replacing duplicate _cfg() patterns across the codebase.

    Args:
        section_path: Section name or path (e.g., "cli" or ["time", "iso8601"])
        required_fields: List of required field names in the section
        required_subsections: List of required subsection names in the section
        repo_root: Project root path (auto-detected if None)

    Returns:
        Validated config section dict

    Raises:
        RuntimeError: If section is missing or validation fails

    Example:
        >>> # Load time.iso8601 config with field validation
        >>> cfg = load_validated_section(
        ...     ["time", "iso8601"],
        ...     required_fields=["timespec", "use_z_suffix", "strip_microseconds"]
        ... )
        >>>
        >>> # Load cli config with subsection validation
        >>> cfg = load_validated_section(
        ...     "cli",
        ...     required_subsections=["json", "table", "confirm", "output"]
        ... )
    """
    config = get_cached_config(repo_root=repo_root)
    return _resolve_section_from_config(
        config,
        section_path,
        required_fields=required_fields,
        required_subsections=required_subsections,
    )


__all__ = [
    "load_config_section",
    "load_validated_section",
]
