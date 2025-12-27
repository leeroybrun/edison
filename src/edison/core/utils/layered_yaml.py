"""Shared layered YAML loading helpers.

These helpers centralize common patterns used across Edison:
- Deterministic iteration of YAML files in a directory
- "named config file" resolution with .yaml/.yml fallback
- Deep-merge semantics consistent with ConfigManager
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from edison.core.utils.io import iter_yaml_files, read_yaml
from edison.core.utils.merge import deep_merge


def merge_yaml_directory(base: Dict[str, Any], directory: Path) -> Dict[str, Any]:
    """Merge all YAML files from ``directory`` into ``base``.

    Files are merged in deterministic order. Missing directories are ignored.
    YAML must be valid; invalid YAML raises.
    """
    d = Path(directory)
    if not d.exists():
        return base

    cfg: Dict[str, Any] = dict(base)
    for path in iter_yaml_files(d):
        module_cfg = read_yaml(path, default={}, raise_on_error=True) or {}
        cfg = deep_merge(cfg, module_cfg)
    return cfg


def merge_named_yaml(base: Dict[str, Any], directory: Path, name: str) -> Dict[str, Any]:
    """Merge ``<name>.yaml`` or ``<name>.yml`` from ``directory`` into ``base``.

    Preference order is ``.yaml`` then ``.yml``.
    """
    d = Path(directory)
    if not d.exists():
        return base

    yaml_path = d / f"{name}.yaml"
    if yaml_path.exists():
        module_cfg = read_yaml(yaml_path, default={}, raise_on_error=True) or {}
        return deep_merge(dict(base), module_cfg)

    yml_path = d / f"{name}.yml"
    if yml_path.exists():
        module_cfg = read_yaml(yml_path, default={}, raise_on_error=True) or {}
        return deep_merge(dict(base), module_cfg)

    return base


__all__ = [
    "merge_yaml_directory",
    "merge_named_yaml",
]

