from __future__ import annotations

from pathlib import Path

from edison.core.guideline_audit import ( 
    discover_guidelines,
    duplication_matrix,
    purity_violations,
)


def test_core_and_packs_are_free_of_project_terms() -> None:
    """Core and pack guidelines must be project‑agnostic.

    project‑specific tokens such as 'project', 'app_', 'better-auth',
    'odoo', and any repo-configured custom terms are not allowed in core or
    pack guideline files.
    """
    repo_root = Path.cwd()
    records = discover_guidelines(repo_root)
    violations = purity_violations(records)

    offending = violations["core_project_terms"] + violations["pack_project_terms"]
    assert not offending, (
        "Expected no project-specific terms in core/packs guidelines, "
        f"found {len(offending)} hits; first few: {offending[:5]}"
    )


def test_project_overlays_do_not_contain_pack_technology_rules() -> None:
    """project overlays should not own generic pack/technology rules.

    Any references to core pack technologies (nextjs, React, prisma,
    uistyles, Fastify, Vitest, TypeScript) inside .agents/guidelines
    indicate misplaced generic guidance that should live in packs or core.
    """
    repo_root = Path.cwd()
    records = discover_guidelines(repo_root)
    violations = purity_violations(records)

    misplaced = violations["project_pack_terms"]
    # RED phase: this assertion is expected to fail until guidelines are extracted.
    assert not misplaced, (
        "project guidelines contain pack/technology-specific rules; "
        f"move these into core/packs. First few: {misplaced[:5]}"
    )


def test_no_near_duplicate_guidelines_across_repo() -> None:
    """Guideline files should not be near-identical copies.

    Using 12-word shingles and Jaccard similarity, any pair of guideline
    files with similarity >= 0.8 is treated as a duplication that should be
    consolidated or layered via includes instead of copy/paste.
    """
    repo_root = Path.cwd()
    all_records = discover_guidelines(repo_root)
    # Only enforce duplication constraints on active guideline layers
    # (core, packs, project overlays). Archived/migration fixtures are
    # allowed to mirror current content verbatim.
    active_records = [r for r in all_records if r.category in ("core", "pack", "project")]
    duplicates = duplication_matrix(active_records, min_similarity=0.8)

    # RED phase: current auto-generated core guidelines are expected to
    # trigger this assertion until they are cleaned up.
    assert not duplicates, (
        "Found highly-similar guideline pairs (similarity >= 0.8); "
        f"candidates for consolidation include: {duplicates[:5]}"
    )


if __name__ == "__main__":  # pragma: no cover
    # Allow ad-hoc execution: `python test_guidelines_audit.py`
    import pytest

    raise SystemExit(pytest.main([__file__]))
