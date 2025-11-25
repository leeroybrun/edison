#!/usr/bin/env python3
"""
Fix test files that have broken import patterns after conversion.

Many test files had dynamic import patterns like:
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    import lib.something

The main conversion script removed sys.path.insert but left incomplete if statements.
This script rewrites these patterns to use direct edison.core imports.
"""

import re
from pathlib import Path


def fix_file(path: Path) -> bool:
    """Fix broken import patterns in a test file."""
    try:
        content = original = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False

    # Pattern 1: Remove the _core_root() helper function and its usage
    # These test files were finding core root dynamically - no longer needed
    content = re.sub(
        r'def _core_root\(\).*?raise AssertionError\([^)]+\)\n\n',
        '',
        content,
        flags=re.DOTALL
    )

    # Pattern 2: Remove dynamic import helper functions that used old patterns
    # Match functions like _import_io_utils, _import_something that do path manipulation
    content = re.sub(
        r'def _import_\w+\(\):\n'
        r'(?:.*?core_root.*?\n)*'
        r'(?:.*?sys\.path.*?\n)*'
        r'(?:.*?if str.*?not in sys\.path:\n)?'
        r'(?:.*?import importlib\n)?'
        r'\n?'
        r'(?:.*?return importlib\.import_module.*?\n)?',
        '',
        content,
        flags=re.MULTILINE
    )

    # Pattern 3: Fix incomplete if statements (if ... not in sys.path: with no body)
    content = re.sub(
        r'^\s*if str\([^)]+\) not in sys\.path:\n(?=\s*import|\s*from|\s*$)',
        '',
        content,
        flags=re.MULTILINE
    )

    # Pattern 4: Remove empty if blocks
    content = re.sub(
        r'if str\([^)]+\) not in sys\.path:\n\s*\n',
        '',
        content,
        flags=re.MULTILINE
    )

    # Pattern 5: Convert remaining lib imports to edison.core
    content = re.sub(r'from lib\.', 'from edison.core.', content)
    content = re.sub(r'import lib\.', 'import edison.core.', content)
    content = re.sub(r'"lib\.', '"edison.core.', content)

    # Pattern 6: Remove importlib.import_module("lib.*") patterns
    content = re.sub(
        r'importlib\.import_module\("lib\.([^"]+)"\)',
        r'__import__("edison.core.\1", fromlist=["\1".split(".")[-1]])',
        content
    )

    # Clean up multiple blank lines
    content = re.sub(r'\n{3,}', '\n\n', content)

    if content != original:
        path.write_text(content, encoding="utf-8")
        return True
    return False


def main():
    """Fix test files."""
    tests_base = Path(__file__).parent.parent / "tests"

    modified = 0
    scanned = 0

    for f in tests_base.rglob("*.py"):
        scanned += 1
        if fix_file(f):
            print(f"Fixed: {f.relative_to(tests_base)}")
            modified += 1

    print(f"\nDone! Fixed {modified}/{scanned} files.")


if __name__ == "__main__":
    main()
