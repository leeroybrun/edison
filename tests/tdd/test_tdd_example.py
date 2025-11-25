import os
import sys
from pathlib import Path

# Ensure Edison core lib is importable when running standalone
_THIS_FILE = Path(__file__).resolve()
_PROJECT_ROOT = None
for _parent in _THIS_FILE.parents:
    if (_parent / ".edison" / "core" / "lib").exists():
        _PROJECT_ROOT = _parent
        break

if _PROJECT_ROOT is None:
    # Fallback to original heuristic (kept for safety)
    _PROJECT_ROOT = _THIS_FILE.parents[3]


from tdd_example import slugify  # type: ignore


def test_slugify_basic():
    assert slugify("Hello, World!") == "hello-world"


def test_slugify_spaces_and_dashes():
    assert slugify("  multiple   spaces ") == "multiple-spaces"
    assert slugify("Already-slugified") == "already-slugified"
