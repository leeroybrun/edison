from __future__ import annotations

"""
Guideline audit helpers for duplication and purity checks.

Responsibilities:
- Discover guideline markdown files across core, packs, project overlays, and
  any additional guideline directories in the repository.
- Build a duplication matrix using 12‑word shingles (headings/code ignored).
- Detect purity violations:
    * project‑specific terms leaking into core or pack guidelines.
    * Pack/technology terms appearing inside project overlays.

This module is intentionally dependency‑light so it can be used both from
pytest and from standalone CLI scripts.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple, Literal, Any
import os

from .composition import (  # type: ignore
    _strip_headings_and_code,
    _tokenize,
    _shingles,
    _repo_root as _composition_repo_root,
)
from .paths.project import get_project_config_dir


GuidelineCategory = Literal["core", "pack", "project", "other"]


@dataclass
class GuidelineRecord:
    """Represents a single guideline markdown file."""

    path: Path
    category: GuidelineCategory
    pack: Optional[str] = None  # for category == "pack"

    def relpath(self, repo_root: Optional[Path] = None) -> Path:
        root = repo_root or _composition_repo_root()
        try:
            return self.path.relative_to(root)
        except ValueError:
            return self.path


def _repo_root() -> Path:
    """Delegate to composition engine root resolution."""
    return _composition_repo_root()


def discover_guidelines(repo_root: Optional[Path] = None) -> List[GuidelineRecord]:
    """Discover guideline files across the repository.

    Categories:
    - core:    .edison/core/guidelines/**/*.md
    - pack:    .edison/packs/*/guidelines/**/*.md
    - project:  <project_config_dir>/guidelines/**/*.md (including overlays)
    - other:   any additional guidelines/*.md directories not covered above
    """
    root = repo_root or _repo_root()
    records: List[GuidelineRecord] = []

    # Core guidelines
    core_dir = root / ".edison" / "core" / "guidelines"
    if core_dir.exists():
        for path in sorted(core_dir.rglob("*.md")):
            if path.name == "README.md":
                continue
            records.append(GuidelineRecord(path=path, category="core"))

    # Pack guidelines
    packs_root = root / ".edison" / "packs"
    if packs_root.exists():
        for pack_dir in sorted(p for p in packs_root.iterdir() if p.is_dir()):
            gdir = pack_dir / "guidelines"
            if not gdir.exists():
                continue
            for path in sorted(gdir.rglob("*.md")):
                if path.name == "README.md":
                    continue
                records.append(
                    GuidelineRecord(path=path, category="pack", pack=pack_dir.name)
                )

    # project project guidelines (including overlays)
    project_dir = get_project_config_dir(root) / "guidelines"
    if project_dir.exists():
        for path in sorted(project_dir.rglob("*.md")):
            if "README.md" == path.name:
                continue
            records.append(GuidelineRecord(path=path, category="project"))

    # Any other guidelines directories in the repo
    known_roots = {
        core_dir.resolve(),
        *(r.path.parent.resolve() for r in records if r.category in ("pack", "project")),
    }
    for gdir in root.rglob("guidelines"):
        if not gdir.is_dir():
            continue
        if any(str(gdir).startswith(str(known)) for known in known_roots):
            continue
        for path in sorted(gdir.glob("*.md")):
            if path.name == "README.md":
                continue
            records.append(GuidelineRecord(path=path, category="other"))

    return records


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


project_TERMS = project_terms()

__all__ = [
    "GuidelineRecord",
    "GuidelineCategory",
    "discover_guidelines",
    "build_shingle_index",
    "duplication_matrix",
    "purity_violations",
    "project_terms",
    "DEFAULT_PROJECT_TERMS",
    "PACK_TECH_TERMS",
]
