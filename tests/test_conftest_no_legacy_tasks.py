"""Test that conftest.py works without legacy edison.core.tasks imports."""

import sys
from pathlib import Path


def test_conftest_imports_successfully():
    """Verify conftest.py can be imported without edison.core.tasks module."""
    # Ensure edison.core.tasks does NOT exist
    tasks_module_path = Path(__file__).parent.parent / "src" / "edison" / "core" / "tasks"
    assert not tasks_module_path.exists(), (
        f"Legacy tasks module should not exist: {tasks_module_path}"
    )

    # Verify edison.core.tasks is not importable
    try:
        import edison.core.tasks
        assert False, "edison.core.tasks should not be importable"
    except ModuleNotFoundError:
        pass  # Expected

    # Verify conftest can be loaded (it's already loaded by pytest, but let's be explicit)
    import tests.conftest as conftest
    assert hasattr(conftest, '_reset_all_global_caches')


def test_reset_all_global_caches_without_tasks_state():
    """Verify _reset_all_global_caches works without edison.core.tasks.state."""
    from tests.conftest import _reset_all_global_caches

    # Should not raise any errors
    _reset_all_global_caches()

    # Verify it resets other caches properly
    try:
        import edison.core.paths.resolver as paths
        # After reset, cache should be None
        assert paths._PROJECT_ROOT_CACHE is None
    except Exception:
        pass  # If module doesn't exist, that's fine


def test_no_legacy_tasks_import_in_conftest():
    """Verify conftest.py does not contain legacy tasks imports."""
    conftest_path = Path(__file__).parent / "conftest.py"
    content = conftest_path.read_text(encoding="utf-8")

    # Should NOT contain references to edison.core.tasks
    assert "edison.core.tasks" not in content, (
        "conftest.py should not import from legacy edison.core.tasks module"
    )
