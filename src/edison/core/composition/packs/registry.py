from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional

from ..includes import _repo_root
from .metadata import PackMetadata
from .validation import validate_pack


@dataclass
class PackInfo:
    name: str
    path: Path
    meta: PackMetadata


class DependencyResult(NamedTuple):
    ordered: List[str]
    cycles: List[List[str]]
    unknown: List[str]


def _packs_dir_from_cfg(cfg: Dict[str, Any]) -> Path:
    """Get packs directory from config, using unified resolver as fallback."""
    base = cfg.get("packs", {}) if isinstance(cfg, dict) else {}
    root = _repo_root()

    # If config specifies a directory, use it
    if base.get("directory"):
        return root / str(base["directory"])

    # Otherwise use composition path resolver
    from ..core import CompositionPathResolver

    return CompositionPathResolver(root).bundled_packs_dir


def discover_packs(root: Optional[Path] = None) -> List[PackInfo]:
    """Discover all valid packs using composition path resolution."""
    root = root or _repo_root()

    # Use composition path resolver for consistent path resolution
    from ..core import CompositionPathResolver

    base = CompositionPathResolver(root).bundled_packs_dir

    results: List[PackInfo] = []
    if not base.exists():
        return results
    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith("_"):
            continue  # not a real pack
        if not (child / "pack.yml").exists():
            continue
        v = validate_pack(child)
        if v.ok and v.normalized:
            results.append(PackInfo(v.normalized.name, child, v.normalized))
    return results


def resolve_dependencies(packs: Dict[str, PackInfo]) -> DependencyResult:
    # Build graph of name -> required list
    graph: Dict[str, List[str]] = {
        n: list((p.meta.dependencies or [])) for n, p in packs.items()
    }
    # Track unknown deps
    unknown: List[str] = []
    for name, deps in graph.items():
        for d in deps:
            if d not in packs:
                unknown.append(f"{name}:{d}")

    # Kahn's algorithm
    indeg: Dict[str, int] = {n: 0 for n in graph}
    for n, deps in graph.items():
        for d in deps:
            if d in indeg:
                indeg[n] += 1

    ready = [n for n, d in indeg.items() if d == 0]
    order: List[str] = []
    adj: Dict[str, List[str]] = {n: [] for n in graph}
    for n, deps in graph.items():
        for d in deps:
            adj.setdefault(d, []).append(n)

    while ready:
        ready.sort()
        n = ready.pop(0)
        order.append(n)
        for m in adj.get(n, []):
            indeg[m] -= 1
            if indeg[m] == 0:
                ready.append(m)

    cycles: List[List[str]] = []
    if len(order) != len(graph):
        # Find remaining nodes in cycle
        remaining = [n for n, d in indeg.items() if d > 0]
        cycles.append(remaining)

    return DependencyResult(order, cycles, unknown)
