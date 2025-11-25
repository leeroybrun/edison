"""
Edison data resource helpers.

Provides utilities for accessing bundled configuration files, schemas,
guidelines, and other data files using importlib.resources.
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any

import yaml


def get_data_path(subpackage: str, filename: str = "") -> Path:
    """
    Get absolute path to a data file or directory.

    Args:
        subpackage: Name of the data subpackage (e.g., "config", "schemas")
        filename: Optional filename within the subpackage

    Returns:
        Absolute path to the file or directory

    Example:
        >>> get_data_path("config", "defaults.yaml")
        PosixPath('/path/to/edison/data/config/defaults.yaml')
    """
    pkg = resources.files("edison.data")
    base = Path(str(pkg / subpackage))
    return base / filename if filename else base


@lru_cache(maxsize=64)
def read_yaml(subpackage: str, filename: str) -> dict[str, Any]:
    """
    Read and parse a YAML data file (cached).

    Args:
        subpackage: Name of the data subpackage
        filename: YAML filename

    Returns:
        Parsed YAML content as dictionary
    """
    path = get_data_path(subpackage, filename)
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=64)
def read_json(subpackage: str, filename: str) -> dict[str, Any]:
    """
    Read and parse a JSON data file (cached).

    Args:
        subpackage: Name of the data subpackage
        filename: JSON filename

    Returns:
        Parsed JSON content as dictionary
    """
    path = get_data_path(subpackage, filename)
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(subpackage: str, filename: str) -> str:
    """
    Read a text data file.

    Args:
        subpackage: Name of the data subpackage
        filename: Text filename

    Returns:
        File contents as string
    """
    path = get_data_path(subpackage, filename)
    return path.read_text(encoding="utf-8")


def list_files(subpackage: str, pattern: str = "*") -> list[Path]:
    """
    List files matching pattern in a data subpackage.

    Args:
        subpackage: Name of the data subpackage
        pattern: Glob pattern (default "*")

    Returns:
        List of matching file paths
    """
    return list(get_data_path(subpackage).glob(pattern))


def list_dirs(subpackage: str) -> list[Path]:
    """
    List directories in a data subpackage.

    Args:
        subpackage: Name of the data subpackage

    Returns:
        List of directory paths
    """
    base = get_data_path(subpackage)
    return [p for p in base.iterdir() if p.is_dir()]


def file_exists(subpackage: str, filename: str) -> bool:
    """
    Check if a data file exists.

    Args:
        subpackage: Name of the data subpackage
        filename: Filename to check

    Returns:
        True if file exists
    """
    return get_data_path(subpackage, filename).exists()


# Clear caches (useful for testing)
def clear_caches() -> None:
    """Clear all read caches."""
    read_yaml.cache_clear()
    read_json.cache_clear()


__all__ = [
    "get_data_path",
    "read_yaml",
    "read_json",
    "read_text",
    "list_files",
    "list_dirs",
    "file_exists",
    "clear_caches",
]
