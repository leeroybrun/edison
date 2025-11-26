from __future__ import annotations

"""
Guideline purity checking module.

Responsibilities:
- Detect purity violations: project-specific terms leaking into core or pack guidelines
- Detect pack/technology terms appearing inside project overlays
- Configurable term detection via environment variables

Purity ensures clean separation between generic (core/pack) and project-specific
(project) guidelines, maintaining reusability and portability.
"""

import os
from typing import Dict, Iterable, List, Set, Any

from .guideline_discovery import GuidelineRecord


# Default banned tokens should stay generic; project-specific terms are injected via env
DEFAULT_PROJECT_TERMS = ["project", "app_", "better-auth", "odoo"]
PACK_TECH_TERMS = [
    "nextjs",
    "nextjs",
    "react",
    "prisma",
    "uistyles",
    "fastify",
    "vitest",
    "typescript",
]


def _scan_terms(
    rec: GuidelineRecord,
    terms: List[str],
) -> List[Dict[str, Any]]:
    """Return list of term hits with line numbers for a given record."""
    hits: List[Dict[str, Any]] = []
    text = rec.path.read_text(encoding="utf-8", errors="ignore")
    for lineno, line in enumerate(text.splitlines(), start=1):
        lower = line.lower()
        for term in terms:
            if term in lower:
                hits.append(
                    {
                        "path": str(rec.relpath()),
                        "category": rec.category,
                        "pack": rec.pack,
                        "line": lineno,
                        "term": term,
                        "text": line.rstrip(),
                    }
                )
    return hits


def project_terms() -> List[str]:
    """Return project-specific terms to keep out of core/pack guidelines.

    Sources:
    - Default sentinels that often leak from project overlays.
    - PROJECT_NAME env var (adds slug and space-stripped variant).
    - PROJECT_TERMS env var (comma-separated list).
    """
    terms: List[str] = list(DEFAULT_PROJECT_TERMS)

    project_name = os.environ.get("PROJECT_NAME", "").strip()
    if project_name:
        terms.append(project_name.lower())
        terms.append(project_name.replace("-", " ").lower())

    extra = os.environ.get("PROJECT_TERMS", "")
    terms.extend(
        t.strip().lower()
        for t in extra.split(",")
        if t.strip()
    )

    # De-duplicate while preserving order
    seen: Set[str] = set()
    unique_terms: List[str] = []
    for term in terms:
        if term and term not in seen:
            unique_terms.append(term)
            seen.add(term)
    return unique_terms


def purity_violations(
    records: Iterable[GuidelineRecord],
) -> Dict[str, List[Dict[str, Any]]]:
    """Detect purity issues across guideline categories.

    Returns a dict with keys:
    - core_project_terms: project/project terms in core guidelines.
    - pack_project_terms: project/project terms in pack guidelines.
    - project_pack_terms: Pack/tech terms inside project guidelines.
    """
    recs = list(records)
    core_recs = [r for r in recs if r.category == "core"]
    pack_recs = [r for r in recs if r.category == "pack"]
    project_recs = [r for r in recs if r.category == "project"]
    terms = project_terms()

    return {
        "core_project_terms": [
            hit for r in core_recs for hit in _scan_terms(r, terms)
        ],
        "pack_project_terms": [
            hit for r in pack_recs for hit in _scan_terms(r, terms)
        ],
        "project_pack_terms": [
            hit for r in project_recs for hit in _scan_terms(r, PACK_TECH_TERMS)
        ],
    }


__all__ = [
    "DEFAULT_PROJECT_TERMS",
    "PACK_TECH_TERMS",
    "project_terms",
    "purity_violations",
]
