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
    """Tests should be consolidated under a single pytest root.

    This assumes pytest is invoked from PYTEST_ROOT (tests/ in repo root) and discovers:
    - unit tests under unit/
    - integration tests under integration/
    - e2e tests under e2e/
    - QA tests under qa/
    - tdd tests under tdd/
    - process tests under process/
    - etc.

    Note: After migration from `.edison/core/scripts/*` to Python modules,
    all tests are now under the main tests/ directory.
    """
    assert PYTEST_ROOT.is_dir(), f"Pytest root should exist: {PYTEST_ROOT}"

    # Legacy scripts/tests directory no longer exists after migration
    scripts_tests_root = PROJECT_ROOT / ".edison" / "core" / "scripts" / "tests"
    if scripts_tests_root.exists():
        # If it still exists, ensure it's empty or being phased out
        scripts_paths = {p.resolve() for p in _iter_test_files(scripts_tests_root)}
        assert not scripts_paths, f"Found legacy tests that should be migrated: {sorted(scripts_paths)}"


def test_no_duplicate_test_files_across_locations():
    """Ensure no duplicate test files exist in legacy locations.

    After migration, Python test files should exist only under tests/.
    Legacy `.edison/core/scripts/tests` should not exist or should be empty.
    """
    scripts_tests_root = PROJECT_ROOT / ".edison" / "core" / "scripts" / "tests"

    # If legacy path doesn't exist, migration is complete - test passes
    if not scripts_tests_root.exists():
        return

    # If it exists, ensure there are no test files (migration incomplete)
    core_paths = {p.relative_to(PROJECT_ROOT) for p in _iter_test_files(PYTEST_ROOT)}
    scripts_paths = {p.relative_to(PROJECT_ROOT) for p in _iter_test_files(scripts_tests_root)}

    # Check for duplicates
    duplicates = core_paths & scripts_paths
    assert not duplicates, f"Duplicate test modules across locations: {sorted(duplicates)}"

    # Ensure legacy location has no tests
    assert not scripts_paths, f"Legacy tests found that should be migrated: {sorted(scripts_paths)}"


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
