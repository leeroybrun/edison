"""YAML I/O utilities with atomic writes and advisory locks."""
from __future__ import annotations

import fcntl
from pathlib import Path
from typing import Any

from .core import atomic_write

try:
    import yaml

    HAS_YAML = True

    # Custom representer for multiline strings - use literal block style (|)
    def _str_representer(dumper: yaml.SafeDumper, data: str) -> yaml.ScalarNode:
        """Represent multiline strings with literal block style."""
        if "\n" in data:
            # Use literal block style for multiline strings
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        return dumper.represent_scalar("tag:yaml.org,2002:str", data)

    yaml.add_representer(str, _str_representer, Dumper=yaml.SafeDumper)

except ImportError:
    HAS_YAML = False


def read_yaml(
    path: Path, default: Any = None, raise_on_error: bool = False
) -> Any:
    """Read YAML with error handling.

    Returns default if file is missing or invalid, unless raise_on_error is True.

    Args:
        path: YAML file path to read
        default: Value to return if file missing or invalid (default: None)
        raise_on_error: If True, propagate exceptions instead of returning default.

    Returns:
        Any: Parsed YAML data, or default if error

    Examples:
        >>> config = read_yaml(Path("config.yaml"), default={})
        >>> assert isinstance(config, dict)
    """
    if not HAS_YAML:
        if raise_on_error:
            raise RuntimeError("PyYAML is required")
        return default

    path = Path(path)
    if not path.exists():
        if raise_on_error:
            raise FileNotFoundError(f"File not found: {path}")
        return default

    try:
        with open(path, "r", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            data = yaml.safe_load(f)  # type: ignore[no-untyped-call]
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        return data if data is not None else default
    except Exception:
        if raise_on_error:
            raise
        return default


def write_yaml(path: Path, data: Any) -> None:
    """Atomically write YAML data to ``path``.

    Matches the JSON helper by using the shared atomic writer. Keys are
    sorted for deterministic output.

    Args:
        path: Target file path
        data: Data to serialize as YAML

    Raises:
        RuntimeError: If PyYAML is not installed
    """
    if not HAS_YAML:
        raise RuntimeError(
            "PyYAML is required for YAML operations. Install with: pip install pyyaml"
        )

    def _writer(f) -> None:
        yaml.safe_dump(  # type: ignore[no-untyped-call]
            data,
            f,
            default_flow_style=False,
            sort_keys=True,
            allow_unicode=True,
        )

    atomic_write(Path(path), _writer)


def parse_yaml_string(content: str, default: Any = None) -> Any:
    """Parse YAML from string with error handling.

    Args:
        content: YAML string content
        default: Value to return on error (default: None)

    Returns:
        Parsed data or default
    """
    if not HAS_YAML:
        return default

    try:
        data = yaml.safe_load(content)  # type: ignore[no-untyped-call]
        return data if data is not None else default
    except Exception:
        return default


def dump_yaml_string(data: Any, sort_keys: bool = True) -> str:
    """Dump data to YAML string.

    Args:
        data: Data to dump
        sort_keys: Whether to sort keys (default: True)

    Returns:
        YAML string

    Raises:
        RuntimeError: If PyYAML is not installed
    """
    if not HAS_YAML:
        raise RuntimeError(
            "PyYAML is required for YAML operations. Install with: pip install pyyaml"
        )

    return yaml.safe_dump(  # type: ignore[no-untyped-call]
        data,
        default_flow_style=False,
        sort_keys=sort_keys,
        allow_unicode=True,
    )

def iter_yaml_files(dir_path: Path) -> list[Path]:
    """Return YAML files in ``dir_path`` in deterministic order.

    Includes both ``*.yml`` and ``*.yaml``.

    When both ``<name>.yaml`` and ``<name>.yml`` exist, this prefers ``.yaml`` and
    returns only the ``.yaml`` path to avoid competing/duplicated config loads.
    """
    d = Path(dir_path)
    if not d.exists():
        return []
    yml_files = {p.stem: p for p in d.glob("*.yml")}
    yaml_files = {p.stem: p for p in d.glob("*.yaml")}

    out: list[Path] = []
    for stem in sorted(set(yml_files.keys()) | set(yaml_files.keys())):
        preferred = yaml_files.get(stem) or yml_files.get(stem)
        if preferred is not None:
            out.append(preferred)
    return out

def resolve_yaml_path(path: Path) -> Path:
    """Resolve a YAML path that may be either ``.yml`` or ``.yaml``.

    If ``path`` points to a ``.yml``/``.yaml`` file and the sibling with the other
    extension exists, return the existing sibling. Preference is given to
    ``.yaml`` when both exist.

    If no existing candidate is found, returns ``path`` unchanged.
    """
    p = Path(path)
    if p.suffix in {".yml", ".yaml"}:
        base = p.with_suffix("")
        original = p
    else:
        base = p
        original = p

    for ext in (".yaml", ".yml"):
        candidate = base.with_suffix(ext)
        if candidate.exists():
            return candidate

    return original


__all__ = [
    "HAS_YAML",
    "read_yaml",
    "write_yaml",
    "parse_yaml_string",
    "dump_yaml_string",
    "iter_yaml_files",
    "resolve_yaml_path",
]
