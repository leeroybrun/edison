from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

RelationshipEdge = Dict[str, str]


def normalize_edges(
    edges: List[RelationshipEdge],
    *,
    singleton_types: Sequence[str] = (),
) -> List[RelationshipEdge]:
    """Return a deterministic, de-duplicated list of relationship edges.

    - Removes invalid/empty entries.
    - De-duplicates by (type, target).
    - Stable ordering: (type, target).
    - Enforces singleton edge types (fail-closed) when provided.
    """
    cleaned: List[RelationshipEdge] = []
    seen: set[Tuple[str, str]] = set()

    for raw in edges or []:
        if not isinstance(raw, dict):
            continue
        t = str(raw.get("type") or "").strip()
        target = str(raw.get("target") or "").strip()
        if not t or not target:
            continue
        key = (t, target)
        if key in seen:
            continue
        seen.add(key)
        cleaned.append({"type": t, "target": target})

    for singleton in singleton_types or ():
        st = str(singleton).strip()
        if not st:
            continue
        matches = [e for e in cleaned if e.get("type") == st]
        if len(matches) > 1:
            raise ValueError(f"Multiple '{st}' edges found ({len(matches)}); at most one is allowed")

    cleaned.sort(key=lambda e: (str(e.get("type") or ""), str(e.get("target") or "")))
    return cleaned

