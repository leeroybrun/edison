"""Test that utc_timestamp is imported from the correct source of truth.

This test enforces NO LEGACY principle by verifying that:
1. utc_timestamp should be imported from edison.core.utils.time (source of truth)
2. NOT from edison.core.file_io.utils (legacy wrapper that should be removed)
"""
from __future__ import annotations

import pytest


def test_utc_timestamp_import_from_correct_source():
    """Verify utc_timestamp can be imported from utils.time (source of truth)."""
    from edison.core.utils.time import utc_timestamp

    # Should return a valid ISO 8601 timestamp string
    timestamp = utc_timestamp()
    assert isinstance(timestamp, str)
    assert len(timestamp) > 0


def test_utc_timestamp_not_in_file_io_utils():
    """Verify that file_io.utils does NOT export utc_timestamp (legacy removed)."""
    from edison.core.file_io import utils as file_io_utils

    # utc_timestamp should NOT be in __all__ export list
    if hasattr(file_io_utils, '__all__'):
        assert 'utc_timestamp' not in file_io_utils.__all__, \
            "utc_timestamp should be removed from file_io.utils.__all__"

    # utc_timestamp should NOT be importable from file_io.utils
    # (or if it exists, it should not be in the public API)
    with pytest.raises(ImportError):
        # This should fail after we remove the wrapper
        exec("from edison.core.file_io.utils import utc_timestamp")


def test_all_imports_use_utils_time():
    """Verify that files that need utc_timestamp import from utils.time."""
    import ast
    from pathlib import Path

    # Files that should import from utils.time
    files_to_check = [
        "src/edison/core/session/manager.py",
        "src/edison/core/session/verify.py",
        "src/edison/core/session/graph.py",
        "src/edison/core/session/recovery.py",
        "src/edison/cli/session/recovery/recover.py",
        "src/edison/cli/session/recovery/repair.py",
        "src/edison/cli/session/track.py",
        "src/edison/core/hooks/compaction.py",
        "tests/file_io/test_io_utils.py",
        "src/edison/cli/qa/round.py",
    ]

    repo_root = Path(__file__).parent.parent.parent.parent

    for file_path in files_to_check:
        full_path = repo_root / file_path
        if not full_path.exists():
            continue

        content = full_path.read_text()

        # Should NOT import from file_io.utils
        # We check line by line to avoid false positives where file imports OTHER things
        # from file_io.utils but imports utc_timestamp correctly from utils.time
        for line in content.splitlines():
            if "from edison.core.file_io.utils import" in line and "utc_timestamp" in line:
                pytest.fail(f"{file_path} imports utc_timestamp from file_io.utils: {line}")
