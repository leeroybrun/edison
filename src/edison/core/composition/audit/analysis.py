from __future__ import annotations

"""
Guideline analysis module - duplication detection using shingles.

Responsibilities:
- Build shingle index for guideline files
- Compute duplication matrix using Jaccard similarity
- Detect content overlap between guidelines to enforce DRY principles

This module uses config-driven shingle sizing with headings and code blocks
stripped to reduce false positives.
"""

from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple, Any, Optional

from edison.core.utils.text import (
    _strip_headings_and_code,
    _tokenize,
    _shingles,
)
from .guideline_discovery import GuidelineRecord


def _file_shingles(path: Path, *, k: int = 12) -> Set[Tuple[str, ...]]:
    """Return k‑word shingles for the entire file (headings/code ignored)."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    cleaned = _strip_headings_and_code(text)
    tokens = _tokenize(cleaned)
    return _shingles(tokens, k=k)


def build_shingle_index(
    records: Iterable[GuidelineRecord], *, k: int = 12
) -> Dict[Path, Set[Tuple[str, ...]]]:
    """Compute shingle sets for each guideline path."""
    index: Dict[Path, Set[Tuple[str, ...]]] = {}
    for rec in records:
        if rec.path in index:
            continue
        index[rec.path] = _file_shingles(rec.path, k=k)
    return index


def duplication_matrix(
    records: Iterable[GuidelineRecord],
    *,
    k: Optional[int] = None,
    min_similarity: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Return list of highly similar guideline pairs using config-driven settings.

    Similarity metric: Jaccard index between file‑level shingle sets.
    k (shingle size) and min_similarity default to composition.dryDetection config.
    Only pairs with similarity >= min_similarity are returned.
    """
    recs = list(records)

    if k is None or min_similarity is None:
        import os
        from ...config import ConfigManager

        # Respect AGENTS_PROJECT_ROOT for test isolation
        repo_root = None
        agents_root = os.environ.get("AGENTS_PROJECT_ROOT")
        if agents_root:
            repo_root = Path(agents_root)

        cfg = ConfigManager(repo_root=repo_root).load_config(validate=False)
        dry_config = cfg.get("composition", {}).get("dryDetection", {})

        if k is None:
            if "shingleSize" not in dry_config:
                raise KeyError("composition.dryDetection.shingleSize missing in configuration")
            k = dry_config["shingleSize"]

        if min_similarity is None:
            if "minSimilarity" not in dry_config:
                raise KeyError("composition.dryDetection.minSimilarity missing in configuration")
            min_similarity = dry_config["minSimilarity"]

    index = build_shingle_index(recs, k=k)
    pairs: List[Dict[str, Any]] = []

    for i, a in enumerate(recs):
        sa = index.get(a.path) or set()
        if not sa:
            continue
        for b in recs[i + 1 :]:
            sb = index.get(b.path) or set()
            if not sb:
                continue
            inter = sa & sb
            if not inter:
                continue
            union = sa | sb
            if not union:
                continue
            similarity = len(inter) / len(union)
            if similarity < min_similarity:
                continue
            pairs.append(
                {
                    "a": {
                        "path": str(a.relpath()),
                        "category": a.category,
                        "pack": a.pack,
                    },
                    "b": {
                        "path": str(b.relpath()),
                        "category": b.category,
                        "pack": b.pack,
                    },
                    "similarity": similarity,
                    "intersection": len(inter),
                    "union": len(union),
                }
            )
    return pairs


__all__ = [
    "build_shingle_index",
    "duplication_matrix",
]
