#!/usr/bin/env python3
"""
Validate test naming conventions and pytest markers.

This script checks all test files for compliance with Edison test standards:
1. Test function naming: test_<what>_<when>_<expected>()
2. Test class naming: Test<Feature> (no plural suffix)
3. Fixture naming: <noun>_<qualifier> (no test_ prefix)
4. Pytest markers: integration, e2e, requires_git, requires_subprocess
5. Skip patterns: Use decorators, not inline pytest.skip()

Usage:
    python scripts/validate_test_standards.py
    python scripts/validate_test_standards.py --fix-auto  # Auto-fix where possible
    python scripts/validate_test_standards.py --verbose   # Show all violations
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple
from collections import defaultdict


class TestStandardsValidator:
    """Validates test files against Edison standards."""

    def __init__(self, tests_dir: Path, verbose: bool = False):
        self.tests_dir = tests_dir
        self.verbose = verbose
        self.violations = defaultdict(list)

    def validate_all(self) -> Dict[str, List[str]]:
        """Validate all test files."""
        test_files = list(self.tests_dir.rglob('test_*.py'))

        for filepath in test_files:
            self._validate_file(filepath)

        return dict(self.violations)

    def _validate_file(self, filepath: Path) -> None:
        """Validate a single test file."""
        try:
            content = filepath.read_text()
            lines = content.split('\n')
            rel_path = filepath.relative_to(self.tests_dir)

            # Check test function names
            self._check_test_functions(rel_path, lines)

            # Check test class names
            self._check_test_classes(rel_path, lines)

            # Check fixture names
            self._check_fixtures(rel_path, lines)

            # Check for inline skip calls
            self._check_inline_skips(rel_path, lines)

            # Check for missing markers
            self._check_markers(rel_path, filepath, content)

        except Exception as e:
            self.violations['errors'].append(f"{filepath}: {e}")

    def _check_test_functions(self, rel_path: Path, lines: List[str]) -> None:
        """Check test function naming convention."""
        test_func_pattern = r'^(async\s+)?def\s+(test_\w+)\s*\('

        for i, line in enumerate(lines, 1):
            match = re.match(test_func_pattern, line)
            if match:
                func_name = match.group(2)
                parts = func_name[5:].split('_')  # Remove 'test_' prefix

                # Check if name has at least 3 parts (what, when, expected)
                if len(parts) < 3:
                    self.violations['short_test_names'].append(
                        f"{rel_path}:{i} - {func_name} (needs format: test_<what>_<when>_<expected>)"
                    )

    def _check_test_classes(self, rel_path: Path, lines: List[str]) -> None:
        """Check test class naming convention."""
        class_pattern = r'^class\s+(Test\w+)'

        for i, line in enumerate(lines, 1):
            match = re.match(class_pattern, line)
            if match:
                class_name = match.group(1)

                # Check for bad suffixes
                if class_name.endswith('Tests'):
                    self.violations['bad_class_names'].append(
                        f"{rel_path}:{i} - {class_name} (remove plural 's', use: {class_name[:-1]})"
                    )
                elif class_name.endswith('TestCase'):
                    new_name = class_name.replace('TestCase', '')
                    self.violations['bad_class_names'].append(
                        f"{rel_path}:{i} - {class_name} (remove 'TestCase', use: {new_name})"
                    )

    def _check_fixtures(self, rel_path: Path, lines: List[str]) -> None:
        """Check fixture naming convention."""
        for i, line in enumerate(lines, 1):
            if re.search(r'@pytest\.fixture', line):
                # Look ahead to next line for function def
                if i < len(lines):
                    next_line = lines[i]
                    match = re.match(r'^def\s+(test_\w+)\s*\(', next_line)
                    if match:
                        fixture_name = match.group(1)
                        suggested = fixture_name[5:]  # Remove 'test_' prefix
                        self.violations['fixture_with_test_prefix'].append(
                            f"{rel_path}:{i+1} - {fixture_name} (remove 'test_' prefix, use: {suggested})"
                        )

    def _check_inline_skips(self, rel_path: Path, lines: List[str]) -> None:
        """Check for inline pytest.skip() calls."""
        for i, line in enumerate(lines, 1):
            if re.search(r'pytest\.skip\(', line):
                self.violations['inline_skip_calls'].append(
                    f"{rel_path}:{i} - Use @pytest.mark.skipif decorator instead"
                )

    def _check_markers(self, rel_path: Path, filepath: Path, content: str) -> None:
        """Check for missing pytest markers."""
        is_integration = '/integration/' in str(filepath)
        is_e2e = '/e2e/' in str(filepath)

        # Check integration marker
        if is_integration:
            if '@pytest.mark.integration' not in content and 'pytestmark = pytest.mark.integration' not in content:
                self.violations['missing_integration_marker'].append(str(rel_path))

        # Check e2e marker
        if is_e2e:
            if '@pytest.mark.e2e' not in content and 'pytestmark = pytest.mark.e2e' not in content:
                self.violations['missing_e2e_marker'].append(str(rel_path))

        # Check requires_git marker
        has_git = bool(re.search(r'(git\s+|\.git/|worktree|run_with_timeout.*git)', content, re.I))
        if has_git and 'pytest.mark.requires_git' not in content and 'requires_git' not in content:
            self.violations['missing_requires_git_marker'].append(str(rel_path))

        # Check requires_subprocess marker
        has_subprocess = bool(re.search(r'(subprocess\.|run_with_timeout|Popen)', content))
        if has_subprocess and 'pytest.mark.requires_subprocess' not in content and 'requires_subprocess' not in content:
            self.violations['missing_requires_subprocess_marker'].append(str(rel_path))

    def print_summary(self) -> int:
        """Print validation summary."""
        total_violations = sum(len(v) for v in self.violations.values())

        if total_violations == 0:
            print("✅ All tests comply with naming standards!")
            return 0

        print(f"❌ Found {total_violations} violations:\n")

        # Print counts
        for violation_type, items in sorted(self.violations.items()):
            print(f"  {violation_type}: {len(items)}")

        if self.verbose:
            print("\n" + "=" * 80)
            print("DETAILED VIOLATIONS")
            print("=" * 80 + "\n")

            for violation_type, items in sorted(self.violations.items()):
                print(f"\n{violation_type.upper().replace('_', ' ')}:")
                print("-" * 80)
                for item in items:
                    print(f"  {item}")

        return 1


def main():
    parser = argparse.ArgumentParser(description='Validate test naming standards')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed violations')
    parser.add_argument('--tests-dir', type=Path, default=Path('tests'), help='Tests directory')
    args = parser.parse_args()

    # Find tests directory
    if not args.tests_dir.exists():
        # Try from repo root
        repo_root = Path(__file__).parent.parent
        args.tests_dir = repo_root / 'tests'

    if not args.tests_dir.exists():
        print(f"❌ Tests directory not found: {args.tests_dir}")
        return 1

    print(f"🔍 Validating test files in {args.tests_dir}...\n")

    validator = TestStandardsValidator(args.tests_dir, verbose=args.verbose)
    violations = validator.validate_all()

    return validator.print_summary()


if __name__ == '__main__':
    sys.exit(main())
