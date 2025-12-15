from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from edison.core.utils.io import read_yaml
from edison.core.utils.paths import get_project_config_dir


@dataclass
class PackManifest:
    name: str
    path: Path
    dependencies: Dict[str, str]
    dev_dependencies: Dict[str, str]
    scripts: Dict[str, str]
    required_packs: List[str]


def _load_yaml(path: Path) -> Dict[str, Any]:
    """Load YAML from a file path, returning empty dict if file doesn't exist."""
    if not path.exists():
        return {}
    return read_yaml(path, default={})


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    from edison.core.utils.io import read_json as io_read_json

    return io_read_json(path) or {}


def _pack_dir(repo_root: Path, name: str) -> Path:
    config_dir = get_project_config_dir(repo_root, create=False)
    return config_dir / "packs" / name


def load_pack(repo_root: Path, name: str) -> PackManifest:
    pdir = _pack_dir(repo_root, name)
    if not pdir.exists():
        raise FileNotFoundError(f"Pack '{name}' not found at {pdir}")

    defaults_path = pdir / "defaults.yaml"
    defaults: Dict[str, Any] = read_yaml(defaults_path, default={}) if defaults_path.exists() else {}

    deps_yaml = read_yaml(pdir / "pack-dependencies.yaml", default={})
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
