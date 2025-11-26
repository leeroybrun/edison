from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Iterable, List, Optional, Set

from ...file_io.utils import read_yaml_safe
from ..includes import _repo_root

try:  # PyYAML is required for pack-trigger discovery
    import yaml  # type: ignore
except Exception:  # pragma: no cover - surfaced by core tests that import yaml directly
    yaml = None  # type: ignore[assignment]


def auto_activate_packs(
    changed_files: List[Path],
    *,
    pack_root: Optional[Path] = None,
    available_packs: Optional[Iterable[str]] = None,
) -> Set[str]:
    """Activate packs whose ``pack.yml`` triggers match ``changed_files``."""
    if not changed_files:
        return set()

    try:
        root = _repo_root()
    except Exception:
        root = None  # type: ignore[assignment]

    rel_paths: List[str] = []
    for p in changed_files:
        path = Path(p)
        if root is not None:
            try:
                rel = path.resolve().relative_to(root)
                rel_paths.append(rel.as_posix())
                continue
            except Exception:
                pass
        rel_paths.append(path.as_posix())

    if not rel_paths:
        return set()

    if pack_root is not None:
        base = pack_root
    elif root is not None:
        # Use composition path resolver for consistent path resolution
        from ..core import CompositionPathResolver
        path_resolver = CompositionPathResolver(root)
        base = path_resolver.packs_dir
    else:
        base = None

    if base is None or not base.exists():
        return set()

    allowed: Optional[Set[str]] = None
    if available_packs is not None:
        allowed = {str(name).strip() for name in available_packs if str(name).strip()}

    if yaml is None:
        return set()

    activated: Set[str] = set()

    for pack_dir in sorted(base.iterdir()):
        if not pack_dir.is_dir():
            continue
        if pack_dir.name.startswith("_"):
            continue  # template or internal pack
        if allowed is not None and pack_dir.name not in allowed:
            continue

        pack_yml = pack_dir / "pack.yml"
        if not pack_yml.exists():
            continue

        data = read_yaml_safe(pack_yml, default={})

        triggers = data.get("triggers") or {}
        raw_patterns: List[str]
        if isinstance(triggers, dict):
            raw_patterns = list(triggers.get("filePatterns") or [])
        elif isinstance(triggers, list):
            raw_patterns = list(triggers or [])
        else:
            raw_patterns = []

        patterns = [
            str(pat).strip() for pat in raw_patterns if isinstance(pat, str) and str(pat).strip()
        ]
        if not patterns:
            continue

        for rel in rel_paths:
            for pat in patterns:
                if fnmatch.fnmatch(rel, pat):
                    activated.add(pack_dir.name)
                    break
            if pack_dir.name in activated:
                break

    return activated
