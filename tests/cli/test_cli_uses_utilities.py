"""TDD tests for CLI utility usage validation.

These tests ensure CLI commands use shared utilities instead of inline patterns.
Following STRICT TDD: Write failing tests FIRST (RED), then implement (GREEN).
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

# Get CLI directory
CLI_DIR = Path(__file__).parent.parent.parent / "src" / "edison" / "cli"


class TestNoInlineRepoRootPattern:
    """Ensure CLI commands use get_repo_root() instead of manual Path(args.repo_root)."""

    def test_no_manual_repo_root_resolution(self):
        """Commands should use get_repo_root(args), not Path(args.repo_root) if args.repo_root."""
        pattern = re.compile(r'Path\(args\.repo_root\)\s*if\s*args\.repo_root')
        violations = []

        for py_file in CLI_DIR.rglob("*.py"):
            if py_file.name.startswith("_"):
                continue  # Skip utility modules (_utils.py, _output.py, _args.py)

            content = py_file.read_text()
            if pattern.search(content):
                violations.append(str(py_file.relative_to(CLI_DIR.parent.parent.parent)))

        assert not violations, (
            f"Files using manual Path(args.repo_root) pattern instead of get_repo_root():\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


class TestNoInlineRecordTypeDetection:
    """Ensure CLI commands use detect_record_type() instead of inline detection."""

    def test_no_inline_record_type_detection(self):
        """Commands should use detect_record_type(), not inline if "-qa" in record_id checks."""
        # Pattern for inline record type detection
        pattern = re.compile(r'if\s+["\']?-qa["\']?\s+in\s+.*record_id')
        violations = []

        for py_file in CLI_DIR.rglob("*.py"):
            if py_file.name.startswith("_"):
                continue  # Skip utility modules

            content = py_file.read_text()
            if pattern.search(content):
                violations.append(str(py_file.relative_to(CLI_DIR.parent.parent.parent)))

        assert not violations, (
            f"Files using inline record type detection instead of detect_record_type():\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


class TestNoInlineRepositoryGetting:
    """Ensure CLI commands use get_repository() instead of inline repository instantiation."""

    def test_no_inline_repository_getting(self):
        """Commands should use get_repository(), not inline if record_type == 'qa' checks."""
        # Pattern for inline repository getting - inside main() functions only
        pattern = re.compile(
            r'if\s+record_type\s*==\s*["\']qa["\']\s*:.*?'
            r'from\s+edison\.core\.qa\.repository\s+import\s+QARepository',
            re.DOTALL
        )
        violations = []

        for py_file in CLI_DIR.rglob("*.py"):
            if py_file.name.startswith("_"):
                continue  # Skip utility modules

            content = py_file.read_text()
            if pattern.search(content):
                violations.append(str(py_file.relative_to(CLI_DIR.parent.parent.parent)))

        assert not violations, (
            f"Files using inline repository getting instead of get_repository():\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


class TestCLIUtilitiesAreImported:
    """Ensure CLI commands import utilities from edison.cli package."""

    def test_get_repo_root_imported_when_project_root_used(self):
        """Files using project_root should import get_repo_root from edison.cli."""
        violations = []

        for py_file in CLI_DIR.rglob("*.py"):
            if py_file.name.startswith("_"):
                continue

            content = py_file.read_text()

            # Check if file uses project_root = get_repo_root(args)
            uses_get_repo_root = "get_repo_root(args)" in content or "get_repo_root(" in content
            has_import = "from edison.cli import" in content and "get_repo_root" in content

            # If file assigns project_root but doesn't use get_repo_root
            if "project_root = " in content and "get_repo_root" not in content:
                # Check if it's using manual pattern
                if "Path(args.repo_root)" in content:
                    violations.append(str(py_file.relative_to(CLI_DIR.parent.parent.parent)))

        assert not violations, (
            f"Files should import and use get_repo_root from edison.cli:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )
