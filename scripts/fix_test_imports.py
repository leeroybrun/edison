#!/usr/bin/env python3
"""
Fix test files that have broken import patterns after conversion.

Many test files had dynamic import patterns like:
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    import lib.something

The main conversion script removed sys.path.insert but left incomplete if statements.
This script removes the broken patterns entirely.
"""

import re
from pathlib import Path


def fix_file(path: Path) -> bool:
    """Fix broken import patterns in a test file."""
    try:
        content = original = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False

    # Pattern 1: Remove incomplete if statements that check sys.path
    # Match: "if str(something) not in sys.path:\n" followed by non-indented line
    content = re.sub(
        r'^\s*if str\([^)]+\) not in sys\.path:\s*\n(?=\s*(?:import|from|def|class|\n|$))',
        '',
        content,
        flags=re.MULTILINE
    )

    # Pattern 2: Remove _core_root() helper functions entirely
    content = re.sub(
        r'def _core_root\(\)[^:]*:.*?(?=\ndef |\nclass |\n\n[A-Z]|\Z)',
        '',
        content,
        flags=re.DOTALL
    )

    # Pattern 3: Remove _import_* helper functions that use importlib
    content = re.sub(
        r'def _import_\w+\(\)[^:]*:.*?(?=\ndef |\nclass |\n\n[A-Z]|\Z)',
        '',
        content,
        flags=re.DOTALL
    )

    # Pattern 4: Remove calls to _import_* functions and replace with direct imports
    # This is tricky - we'll handle common patterns
    content = re.sub(
        r'(\w+)\s*=\s*_import_(\w+)\(\)',
        lambda m: f'from edison.core.{m.group(2)} import {m.group(1)}' if m.group(1) != m.group(2) else f'from edison.core import {m.group(2)}',
        content
    )

    # Pattern 5: Clean up multiple blank lines
    content = re.sub(r'\n{4,}', '\n\n\n', content)

    # Pattern 6: Remove any remaining orphaned if statements
    content = re.sub(
        r'^\s*if str\(core_root\) not in sys\.path:\s*$',
        '',
        content,
        flags=re.MULTILINE
    )

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
