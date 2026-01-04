from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class BundleScope(str, Enum):
    AUTO = "auto"
    HIERARCHY = "hierarchy"
    BUNDLE = "bundle"


def parse_bundle_scope(raw: Optional[str]) -> BundleScope:
    v = str(raw or "").strip().lower()
    if not v:
        return BundleScope.AUTO
    for s in BundleScope:
        if v == s.value:
            return s
    raise ValueError(f"Invalid bundle scope: {raw} (expected one of: auto, hierarchy, bundle)")


@dataclass(frozen=True)
class ClusterSelection:
    root_task_id: str
    scope: BundleScope  # resolved scope (AUTO must not appear here)
    task_ids: tuple[str, ...]


__all__ = [
    "BundleScope",
    "ClusterSelection",
    "parse_bundle_scope",
]

