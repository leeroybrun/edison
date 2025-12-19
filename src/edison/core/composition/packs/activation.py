from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Set

from edison.core.utils.io import read_yaml
from edison.core.utils.patterns import matches_any_pattern
from edison.core.utils.paths import PathResolver
from edison.core.packs.paths import iter_pack_dirs

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

    allowed: Optional[Set[str]] = None
    if available_packs is not None:
        allowed = {str(name).strip() for name in available_packs if str(name).strip()}

    if yaml is None:
        return set()

    activated: Set[str] = set()

    def _iter_candidate_packs() -> Iterable[tuple[str, Path]]:
        """Iterate pack candidates in the correct layering order.

        - If pack_root is provided, only scan that directory.
        - Otherwise scan bundled + project pack roots via the unified iterator.
        """
        if pack_root is not None:
            if not pack_root.exists():
                return []
            pairs: list[tuple[str, Path]] = []
            for child in sorted(pack_root.iterdir()):
                if not child.is_dir():
                    continue
                if child.name.startswith("_"):
                    continue
                pairs.append((child.name, child))
            return pairs

        if root is None:
            return []
        return ((name, p) for name, p, _kind in iter_pack_dirs(root))

    for pack_name, pack_dir in _iter_candidate_packs():
        if allowed is not None and pack_name not in allowed:
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
            str(pat).strip()
            for pat in raw_patterns
            if isinstance(pat, str) and str(pat).strip()
        ]
        if not patterns:
            continue

        for rel in rel_paths:
            if matches_any_pattern(rel, patterns):
                activated.add(pack_name)
                break

    return activated
