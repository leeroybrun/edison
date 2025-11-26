"""I/O utilities for Edison.

This package provides safe, atomic file operations:
- Core: atomic writes, directory management, text I/O
- JSON: read/write with locking
- YAML: read/write with locking
- Locking: file locking primitives
"""
from __future__ import annotations

from .core import (
    PathLike,
    atomic_write,
    ensure_directory,
    ensure_parent_dir,
    read_text,
    write_text,
)

# Alias for backward compatibility
ensure_dir = ensure_directory
from .json import (
    DEFAULT_JSON_CONFIG,
    read_json,
    update_json,
    write_json_atomic,
)
from .locking import (
    LockTimeoutError,
    acquire_file_lock,
    get_file_locking_config,
)
from .yaml import (
    HAS_YAML,
    dump_yaml_string,
    parse_yaml_string,
    read_yaml,
    write_yaml,
)

__all__ = [
    # core
    "PathLike",
    "ensure_parent_dir",
    "ensure_directory",
    "ensure_dir",  # alias for ensure_directory
    "atomic_write",
    "read_text",
    "write_text",
    # json
    "DEFAULT_JSON_CONFIG",
    "read_json",
    "write_json_atomic",
    "update_json",
    # yaml
    "HAS_YAML",
    "read_yaml",
    "write_yaml",
    "parse_yaml_string",
    "dump_yaml_string",
    # locking
    "acquire_file_lock",
    "LockTimeoutError",
    "get_file_locking_config",
]
