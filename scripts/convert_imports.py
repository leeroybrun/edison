#!/usr/bin/env python3
"""
Bulk convert Edison imports from lib.* to edison.core.*

This script transforms all Python files in src/edison/ to use the new
package structure.
"""

import re
from pathlib import Path


def convert_file(path: Path) -> bool:
    """
    Convert imports in a single file.

    Returns True if file was modified.
    """
    try:
        content = original = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print(f"Skipping {path} (encoding error)")
        return False

    # Remove sys.path manipulation blocks
    content = re.sub(
        r'^.*(?:CORE_DIR|_ROOT|ROOT|_CORE_ROOT|EDISON_ROOT).*=.*Path.*parents.*\n'
        r'(?:if.*sys\.path.*\n)?'
        r'.*sys\.path\.insert.*\n?',
        '', content, flags=re.MULTILINE
    )

    # Remove standalone sys.path lines
    content = re.sub(
        r'^.*sys\.path\.insert\(0,.*\n',
        '', content, flags=re.MULTILINE
    )

    # Convert imports: from lib.X to from edison.core.X
    content = re.sub(r'from lib\.', 'from edison.core.', content)
    content = re.sub(r'import lib\.', 'import edison.core.', content)
    content = re.sub(r'from lib import', 'from edison.core import', content)

    # Remove type: ignore for import hacks
    content = re.sub(r'\s*#\s*type:\s*ignore\[import.*?\]', '', content)

    # Remove type: ignore standalone on import lines
    content = re.sub(r'(from edison\.core\.[^\n]+)\s+#\s*type:\s*ignore\s*$', r'\1', content, flags=re.MULTILINE)

    if content != original:
        path.write_text(content, encoding="utf-8")
        return True
    return False


def main():
    """Convert all imports in the Edison package."""
    base = Path(__file__).parent.parent / "src" / "edison"

    modified = 0
    scanned = 0

    for f in base.rglob("*.py"):
        scanned += 1
        if convert_file(f):
            print(f"Modified: {f.relative_to(base)}")
            modified += 1

    # Also convert tests
    tests_base = Path(__file__).parent.parent / "tests"
    if tests_base.exists():
        for f in tests_base.rglob("*.py"):
            scanned += 1
            if convert_file(f):
                print(f"Modified: tests/{f.relative_to(tests_base)}")
                modified += 1

    print(f"\nDone! Modified {modified}/{scanned} files.")


if __name__ == "__main__":
    main()
