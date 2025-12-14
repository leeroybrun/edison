from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Set

from edison.core.utils.io import read_yaml
from edison.core.utils.patterns import matches_any_pattern
from edison.core.utils.paths import PathResolver

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
        root = PathResolver.resolve_project_root()
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
        base = path_resolver.bundled_packs_dir
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

        data = read_yaml(pack_yml, default={})

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
            if matches_any_pattern(rel, patterns):
                activated.add(pack_dir.name)
                break

    return activated
