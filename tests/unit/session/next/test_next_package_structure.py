"""
Tests for session/next package structure.

STRICT TDD: These tests verify the new package structure works correctly.
NO MOCKS: Testing real imports and function behavior.
"""
import pytest


class TestNextPackageStructure:
    """Test the new session/next/ package structure."""

    def test_compute_next_import_from_package(self):
        """Ensure compute_next is importable from edison.core.session.next"""
        from edison.core.session.next import compute_next
        assert callable(compute_next)

    def test_old_file_does_not_exist(self):
        """Ensure the old session/next.py file is deleted."""
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[4]
        old_file = repo_root / "src" / "edison" / "core" / "session" / "next.py"
        assert not old_file.exists(), "Old session/next.py file should be deleted"

    def test_new_package_directory_exists(self):
        """Ensure the new session/next/ directory exists."""
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[4]
        next_dir = repo_root / "src" / "edison" / "core" / "session" / "next"
        assert next_dir.exists(), "session/next/ directory should exist"
        assert next_dir.is_dir(), "session/next should be a directory"

    def test_package_has_required_modules(self):
        """Ensure all required modules exist in the package."""
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[4]
        next_dir = repo_root / "src" / "edison" / "core" / "session" / "next"
        # Note: status.py was merged into actions.py for consolidation
        required_modules = ["__init__.py", "compute.py", "actions.py", "rules.py", "utils.py", "output.py"]

        for module in required_modules:
            module_path = next_dir / module
            assert module_path.exists(), f"{module} should exist in session/next/"

    def test_compute_next_signature_preserved(self):
        """Ensure compute_next function signature is preserved."""
        from edison.core.session.next import compute_next
        import inspect

        sig = inspect.signature(compute_next)
        params = list(sig.parameters.keys())

        # Expected parameters: session_id, scope, limit
        assert "session_id" in params
        assert "scope" in params
        assert "limit" in params

    def test_internal_modules_not_exposed(self):
        """Ensure internal module functions are not exposed at package level."""
        from edison.core.session import next as next_module

        # Only compute_next should be exposed, not internal helpers
        assert hasattr(next_module, "compute_next")

        # Internal helpers should not be exposed
        internal_names = ["_slugify", "_infer_task_status", "_infer_qa_status", "_rules_for", "_expand_rules"]
        for name in internal_names:
            assert not hasattr(next_module, name), f"Internal function {name} should not be exposed"

    def test_no_circular_imports(self):
        """Ensure no circular imports in the new package structure."""
        # This test will fail if there are circular imports
        try:
            from edison.core.session.next import compute_next
            from edison.core.session.next import compute
            from edison.core.session.next import actions
            from edison.core.session.next import rules
            from edison.core.session.next import utils
            from edison.core.session.next import output
        except ImportError as e:
            pytest.fail(f"Circular import detected: {e}")

    def test_file_size_constraints(self):
        """Ensure no module exceeds 500 LOC."""
        from pathlib import Path

        next_dir = Path(__file__).parent.parent.parent / "src" / "edison" / "core" / "session" / "next"
        # Note: status.py was merged into actions.py for consolidation
        modules = ["compute.py", "actions.py", "rules.py", "utils.py", "output.py"]

        for module in modules:
            module_path = next_dir / module
            if module_path.exists():
                lines = len(module_path.read_text().splitlines())
                assert lines <= 500, f"{module} has {lines} lines, should be <= 500 LOC"
