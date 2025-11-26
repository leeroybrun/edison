from __future__ import annotations

"""
Guideline analysis module - duplication detection using shingles.

Responsibilities:
- Build shingle index for guideline files
- Compute duplication matrix using Jaccard similarity
- Detect content overlap between guidelines to enforce DRY principles

This module uses 12-word shingles with headings and code blocks stripped
to reduce false positives.
"""

from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple, Any

from edison.core.utils.text import (
    _strip_headings_and_code,
    _tokenize,
    _shingles,
)
from .discovery import GuidelineRecord


def _file_shingles(path: Path, *, k: int = 12) -> Set[Tuple[str, ...]]:
    """Return 12‑word shingles for the entire file (headings/code ignored)."""
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
    k: int = 12,
    min_similarity: float = 0.8,
) -> List[Dict[str, Any]]:
    """Return list of highly similar guideline pairs based on 12‑word shingles.

    Similarity metric: Jaccard index between file‑level shingle sets.
    Only pairs with similarity >= min_similarity are returned.
    """
    recs = list(records)
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
