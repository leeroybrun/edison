from __future__ import annotations

import pytest
from edison.data import get_data_path


def _read_motion_guide() -> str:
    """Read the bundled MOTION_12_PATTERNS guideline content."""
    path = get_data_path("guidelines/shared", "MOTION_12_PATTERNS.md")
    if not path.exists():
        pytest.fail("MOTION_12_PATTERNS.md not found in guidelines/shared")
    return path.read_text(encoding="utf-8")


def test_motion_guideline_exists() -> None:
    """The Motion 12 patterns guideline must exist."""
    path = get_data_path("guidelines/shared", "MOTION_12_PATTERNS.md")
    assert path.exists(), "MOTION_12_PATTERNS.md should exist"


def test_motion_guideline_includes_required_sections() -> None:
    """Motion guideline must include all required animation pattern sections."""
    content = _read_motion_guide()
    
    required_headings = [
        "## Overview",
        "## Basic Animations",
        "## Variants",
        "## AnimatePresence",
        "## Layout Animations",
        "## Gestures",
        "## Scroll Animations",
        "## Best Practices",
    ]
    
    missing = [heading for heading in required_headings if heading not in content]
    assert not missing, f"Missing required sections: {missing}"


def test_motion_guideline_uses_correct_import_syntax() -> None:
    """Must use 'motion/react' instead of 'framer-motion' (Motion 12)."""
    content = _read_motion_guide()
    
    assert "from 'motion/react'" in content, "Must use Motion 12 import syntax: from 'motion/react'"
    assert "from 'framer-motion'" not in content, "Should not encourage 'framer-motion' imports for new code"


def test_motion_guideline_includes_code_examples() -> None:
    """Guideline must include code examples for patterns."""
    content = _read_motion_guide()
    
    required_snippets = [
        "<motion.div",
        "initial={{ opacity: 0 }}",
        "animate={{ opacity: 1 }}",
        "variants={container}",
        "variants={item}",
        "AnimatePresence mode=\"wait\"",
        "layoutId=",
        "whileHover=",
        "whileTap=",
        "useScroll",
    ]
    
    missing = [snippet for snippet in required_snippets if snippet not in content]
    assert not missing, f"Missing code examples/snippets: {missing}"


def test_motion_guideline_includes_performance_considerations() -> None:
    """Must include performance best practices."""
    content = _read_motion_guide()
    
    performance_keywords = [
        "will-change",
        "layout thrashing",
        "transform",
        "opacity",
        "LazyMotion",
        "domAnimation"
    ]
    
    # Check that at least some performance concepts are mentioned
    found = [kw for kw in performance_keywords if kw in content]
    assert len(found) >= 3, f"Should mention performance concepts, found: {found}"

