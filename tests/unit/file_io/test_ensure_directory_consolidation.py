"""Test ensure_directory() consolidation - removing duplicate ensure_dir().

This test verifies that ensure_directory() with default create=True behaves
identically to the old ensure_dir() function, validating the consolidation.

Following STRICT TDD: This test is written FIRST (RED phase).
"""
from __future__ import annotations

import pytest
from pathlib import Path
from edison.core.utils.io import ensure_directory


def test_ensure_directory_creates_missing_directory(tmp_path: Path) -> None:
    """Test ensure_directory() creates directory if missing (default behavior)."""
    target = tmp_path / "new_dir"
    assert not target.exists()

    result = ensure_directory(target)

    assert target.exists()
    assert target.is_dir()
    assert result == target


def test_ensure_directory_idempotent_on_existing(tmp_path: Path) -> None:
    """Test ensure_directory() is idempotent - safe to call multiple times."""
    target = tmp_path / "existing_dir"
    target.mkdir()
    assert target.exists()

    result1 = ensure_directory(target)
    result2 = ensure_directory(target)

    assert result1 == target
    assert result2 == target
    assert target.is_dir()


def test_ensure_directory_creates_nested_paths(tmp_path: Path) -> None:
    """Test ensure_directory() creates nested directory structure."""
    target = tmp_path / "level1" / "level2" / "level3"
    assert not target.exists()

    result = ensure_directory(target)

    assert target.exists()
    assert target.is_dir()
    assert result == target


def test_ensure_directory_returns_path_for_chaining(tmp_path: Path) -> None:
    """Test ensure_directory() returns path for chaining operations."""
    target = tmp_path / "chain_test"

    returned = ensure_directory(target)

    assert returned == target
    assert isinstance(returned, Path)


def test_ensure_directory_with_create_false_raises_on_missing(tmp_path: Path) -> None:
    """Test ensure_directory(create=False) raises if directory missing."""
    target = tmp_path / "nonexistent"
    assert not target.exists()

    with pytest.raises(FileNotFoundError, match="Directory does not exist"):
        ensure_directory(target, create=False)


def test_ensure_directory_with_create_false_succeeds_on_existing(tmp_path: Path) -> None:
    """Test ensure_directory(create=False) succeeds if directory exists."""
    target = tmp_path / "existing"
    target.mkdir()

    result = ensure_directory(target, create=False)

    assert result == target


def test_ensure_directory_raises_on_file_conflict(tmp_path: Path) -> None:
    """Test ensure_directory() raises if path exists as file."""
    target = tmp_path / "file.txt"
    target.write_text("content")

    with pytest.raises(NotADirectoryError, match="not a directory"):
        ensure_directory(target)


def test_no_ensure_dir_in_exports() -> None:
    """Test ensure_dir is NOT exported in __all__ (consolidation complete)."""
    import edison.core.utils.io as io_pkg

    assert "ensure_directory" in io_pkg.__all__
    assert "ensure_dir" not in io_pkg.__all__, (
        "ensure_dir should be removed from __all__ - "
        "use ensure_directory() as single source of truth"
    )


def test_no_ensure_dir_function_exists() -> None:
    """Test ensure_dir function no longer exists (complete removal)."""
    import edison.core.utils.io as io_pkg

    assert hasattr(io_pkg, "ensure_directory"), "ensure_directory should exist"
    assert not hasattr(io_pkg, "ensure_dir"), (
        "ensure_dir should be completely removed - "
        "use ensure_directory() as single source of truth"
    )
