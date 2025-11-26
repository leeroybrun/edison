from __future__ import annotations

"""
Guideline audit package for duplication and purity checks.

This package was split from a single audit.py file (299 lines) into focused modules:
- discovery: Find guideline files across layers
- analysis: Build shingle index and duplication matrix
- purity: Detect cross-layer term leakage

All previous exports are re-exported here for backward compatibility.
"""

# Discovery exports
from .discovery import (
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
    DEFAULT_PROJECT_TERMS,
    PACK_TECH_TERMS,
    project_terms,
    purity_violations,
)

# Backward compatibility: global constant that was in original audit.py
project_TERMS = project_terms()

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
    "project_TERMS",  # Backward compatibility
]
