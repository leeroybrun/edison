from __future__ import annotations

"""
Guideline audit package for duplication and purity checks.

This package was split from a single audit.py file (299 lines) into focused modules:
- discovery: Find guideline files across layers
- analysis: Build shingle index and duplication matrix
- purity: Detect cross-layer term leakage
"""

# Discovery exports
from .guideline_discovery import (
    GuidelineRecord,
    GuidelineCategory,
    discover_guidelines,
)

# Analysis exports
from .analysis import (
    build_shingle_index,
    duplication_matrix,
)

# Purity exports
from .purity import (
    PACK_TECH_TERMS,
    project_terms,
    purity_violations,
)
from edison.core.config.domains.project import DEFAULT_PROJECT_TERMS

__all__ = [
    # Discovery
    "GuidelineRecord",
    "GuidelineCategory",
    "discover_guidelines",
    # Analysis
    "build_shingle_index",
    "duplication_matrix",
    # Purity
    "purity_violations",
    "project_terms",
    "DEFAULT_PROJECT_TERMS",
    "PACK_TECH_TERMS",
]
