from pathlib import Path


_THIS_FILE = Path(__file__).resolve()
_PROJECT_ROOT = None
for _parent in _THIS_FILE.parents:
    if (_parent / ".edison" / "core" / "lib").exists():
        _PROJECT_ROOT = _parent
        break

if _PROJECT_ROOT is None:
    # Fallback to original heuristic if discovery fails
    _PROJECT_ROOT = _THIS_FILE.parents[4]

PROJECT_ROOT = _PROJECT_ROOT
PYTEST_ROOT = PROJECT_ROOT / ".edison" / "core" / "tests"


def _iter_test_files(root: Path):
    for path in root.rglob("test_*.py"):
        if "/.pytest_cache/" in str(path):
            continue
        yield path


def test_all_tests_discoverable_from_single_root():
    """RED: enforce single pytest root under .edison/core/tests.

    This assumes pytest is invoked from PYTEST_ROOT and discovers:
    - unit tests under unit/
    - integration tests under integration/
    - e2e tests under e2e/
    - QA tests under qa/
    - resilience/shell tests under resilience/

    For now, we assert that .edison/core/scripts/tests does not
    contain standalone Python test files that live outside the
    consolidated PYTEST_ROOT tree.
    """
    assert PYTEST_ROOT.is_dir(), PYTEST_ROOT

    scripts_tests_root = PROJECT_ROOT / ".edison" / "core" / "scripts" / "tests"
    assert scripts_tests_root.is_dir(), scripts_tests_root

    core_paths = {p.resolve() for p in _iter_test_files(PYTEST_ROOT)}
    scripts_paths = {p.resolve() for p in _iter_test_files(scripts_tests_root)}

    # RED: today many tests live only under scripts_paths; enforce eventual consolidation.
    only_in_scripts = scripts_paths - core_paths
    assert not only_in_scripts, f"Found tests outside consolidated pytest root: {sorted(only_in_scripts)}"


def test_no_duplicate_test_files_across_locations():
    """RED: no duplicate test files across core/scripts trees.

    After migration, Python test files should exist only under
    .edison/core/tests; this test currently fails because the
    script framework tests are still separate.
    """
    scripts_tests_root = PROJECT_ROOT / ".edison" / "core" / "scripts" / "tests"
    assert scripts_tests_root.is_dir(), scripts_tests_root

    core_paths = {p.relative_to(PROJECT_ROOT) for p in _iter_test_files(PYTEST_ROOT)}
    scripts_paths = {p.relative_to(PROJECT_ROOT) for p in _iter_test_files(scripts_tests_root)}

    duplicates = core_paths & scripts_paths
    assert not duplicates, f"Duplicate test modules across locations: {sorted(duplicates)}"


def test_import_paths_for_framework_e2e_target_location():
    """RED: importing framework e2e tests from target location works.

    Target structure expects framework E2E tests under
    .edison/core/tests/e2e/framework/.

    Here we simulate the post-migration import path by asserting
    that the package path we expect to use can be resolved as a
    directory. This will fail until the files are moved.
    """
    target_framework_dir = PYTEST_ROOT / "e2e" / "framework"
    assert target_framework_dir.is_dir(), target_framework_dir
