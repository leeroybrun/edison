#!/usr/bin/env python3
"""
Fix test files that use the old lib/ directory structure to find CORE_ROOT.

The old pattern:
    for parent in _cur.parents:
        if (parent / "lib" / "composition" / "__init__.py").exists():
            CORE_ROOT = parent
            break
    assert CORE_ROOT is not None, "cannot locate Edison core lib root"

Should now look for the new package structure.
"""

import re
from pathlib import Path


def fix_file(path: Path) -> bool:
    """Fix CORE_ROOT patterns in a test file."""
    try:
        content = original = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False

    # Pattern: Remove the old for loop pattern that looks for lib/composition
    # Replace with a simple REPO_ROOT = tests root
    content = re.sub(
        r'_(?:CUR|cur)\s*=\s*Path\(__file__\)\.resolve\(\)\n'
        r'CORE_ROOT\s*=\s*None\n'
        r'for parent in _(?:CUR|cur)\.parents:\n'
        r'\s+if \(parent / "lib" / "composition" / "__init__\.py"\)\.exists\(\):\n'
        r'\s+CORE_ROOT = parent\n'
        r'\s+break\n\n'
        r'assert CORE_ROOT is not None, "[^"]+"\n\n'
        r'REPO_ROOT = CORE_ROOT\.parents\[1\]\n',
        '# Repository root for test fixtures\n'
        'REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent\n',
        content
    )

    # Simpler pattern variant
    content = re.sub(
        r'_(?:CUR|cur)\s*=\s*Path\(__file__\)\.resolve\(\)\n'
        r'CORE_ROOT\s*=\s*None\n'
        r'for parent in _(?:CUR|cur)\.parents:\n'
        r'\s+if \(parent / "lib" / "composition" / "__init__\.py"\)\.exists\(\):\n'
        r'\s+CORE_ROOT = parent\n'
        r'\s+break\n\n'
        r'assert CORE_ROOT is not None, "[^"]+"\n',
        '# Repository root for test fixtures\n'
        'REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent\n',
        content
    )

    # Another variant
    content = re.sub(
        r'_cur\s*=\s*Path\(__file__\)\.resolve\(\)\n'
        r'CORE_ROOT:\s*(?:Path\s*\|\s*None|Optional\[Path\])\s*=\s*None\n'
        r'for parent in _cur\.parents:\n'
        r'\s+if \(parent / "lib" / "composition" / "__init__\.py"\)\.exists\(\):\n'
        r'\s+CORE_ROOT = parent\n'
        r'\s+break\n\n'
        r'assert CORE_ROOT is not None, "[^"]+"\n',
        '# Repository root for test fixtures\n'
        'REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent\n',
        content
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
