from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from edison.data import read_yaml
from edison.core.utils.io import read_yaml
from ...paths.project import get_project_config_dir
from ..includes import _repo_root


@dataclass
class PackManifest:
    name: str
    path: Path
    dependencies: Dict[str, str]
    dev_dependencies: Dict[str, str]
    scripts: Dict[str, str]
    required_packs: List[str]


def _load_yaml(path: Path) -> Dict[str, Any]:
    return read_yaml(path, default={})


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    from edison.core.utils.io import read_json as io_read_json

    return io_read_json(path) or {}


def _pack_dir(repo_root: Path, name: str) -> Path:
    config_dir = get_project_config_dir(repo_root, create=False)
    return config_dir / "packs" / name


@lru_cache(maxsize=1)
def _pack_defaults_catalog() -> Dict[str, Dict[str, Any]]:
    """Load pack defaults from the canonical config defaults.yaml."""
    try:
        cfg = read_yaml("config", "defaults.yaml") or {}
    except Exception:
        return {}
    packs_cfg = cfg.get("packs") or {}
    defaults_cfg = packs_cfg.get("defaults") or {}
    catalog: Dict[str, Dict[str, Any]] = {}
    for name, cfg_val in defaults_cfg.items():
        if isinstance(cfg_val, dict):
            catalog[str(name)] = cfg_val
    return catalog


def load_pack(repo_root: Path, name: str) -> PackManifest:
    pdir = _pack_dir(repo_root, name)
    if not pdir.exists():
        raise FileNotFoundError(f"Pack '{name}' not found at {pdir}")

    defaults_catalog = _pack_defaults_catalog()
    defaults_path = pdir / "defaults.yaml"
    defaults = defaults_catalog.get(name, {})

    # Enforce single source of truth: canonical config defaults override any pack-local file.
    if name in defaults_catalog and defaults_path.exists():
        raise ValueError(
            f"Duplicate defaults.yaml for pack '{name}' detected at {defaults_path}. "
            "Use src/edison/data/config/defaults.yaml as the canonical source."
        )
    if not defaults and defaults_path.exists():
        defaults = _load_yaml(defaults_path)

    deps_yaml = _load_yaml(pdir / "pack-dependencies.yaml")
    deps = deps_yaml.get("dependencies") or {}
    dev_deps = deps_yaml.get("devDependencies") or {}
    req = deps_yaml.get("requiredPacks") or []

    scripts = defaults.get("scripts", {}) if isinstance(defaults, dict) else {}
    scripts = scripts or {}
    return PackManifest(
        name=name,
        path=pdir,
        dependencies=dict(deps),
        dev_dependencies=dict(dev_deps),
        scripts=scripts,
        required_packs=list(req or []),
    )