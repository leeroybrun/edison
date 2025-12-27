"""Pack path utilities (bundled + project).

Keep this module dependency-lite to avoid circular imports.

Pack layering model:
1. Bundled packs live under the Edison distribution (edison.data/packs)
2. User packs live under the user config directory (~/<user-config-dir>/packs)
3. Project packs live under the project config directory (<project-config-dir>/packs)
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Iterator, Optional

from edison.data import get_data_path
from edison.core.utils.paths import get_project_config_dir, get_user_config_dir
from edison.core.packs.model import PackRoot

def get_pack_roots(repo_root: Path) -> tuple[PackRoot, ...]:
    """Return pack roots in deterministic precedence order.

    Precedence (low → high) is:
      bundled → (company, etc) → user → project
    """
    from edison.core.layers import resolve_layer_stack

    return resolve_layer_stack(repo_root).pack_roots()


def iter_pack_dirs(
    repo_root: Path,
    *,
    packs: Optional[Iterable[str]] = None,
) -> Iterator[tuple[str, Path, str]]:
    """Iterate pack directories from all pack roots.

    Args:
        repo_root: Repository root.
        packs: Optional iterable of pack names to filter to.

    Yields:
        Tuples of (pack_name, pack_dir, kind) where kind matches PackRoot.kind.
    """
    allowed = {p for p in (packs or []) if isinstance(p, str) and p.strip()} or None

    for root in get_pack_roots(repo_root):
        if not root.path.exists():
            continue
        for child in sorted(root.path.iterdir()):
            if not child.is_dir():
                continue
            if child.name.startswith("_"):
                continue
            if allowed is not None and child.name not in allowed:
                continue
            yield child.name, child, root.kind


__all__ = ["PackRoot", "get_pack_roots", "iter_pack_dirs"]
