"""Tests for QA-related test helpers."""
from __future__ import annotations

from pathlib import Path

import pytest

from helpers.io_utils import format_round_dir, create_round_dir


class TestFormatRoundDir:
    """Test format_round_dir() helper function."""

    def test_format_default_pattern(self):
        """Should format with default 'round-{num}' pattern."""
        assert format_round_dir(1) == "round-1"
        assert format_round_dir(2) == "round-2"
        assert format_round_dir(10) == "round-10"

    def test_format_custom_pattern(self):
        """Should support custom patterns with {num} placeholder."""
        assert format_round_dir(1, pattern="r{num}") == "r1"
        assert format_round_dir(5, pattern="iteration-{num}") == "iteration-5"
        assert format_round_dir(3, pattern="v{num}.0") == "v3.0"

    def test_format_zero_and_negative(self):
        """Should handle zero and negative numbers."""
        assert format_round_dir(0) == "round-0"
        assert format_round_dir(-1) == "round--1"


class TestCreateRoundDir:
    """Test create_round_dir() helper function."""

    def test_creates_round_directory(self, tmp_path: Path):
        """Should create round-N directory under base path."""
        result = create_round_dir(tmp_path, 1)

        assert result.exists()
        assert result.is_dir()
        assert result == tmp_path / "round-1"

    def test_creates_parent_directories(self, tmp_path: Path):
        """Should create parent directories if they don't exist."""
        base = tmp_path / "deep" / "nested" / "path"
        result = create_round_dir(base, 2)

        assert result.exists()
        assert result == base / "round-2"

    def test_idempotent_mkdir(self, tmp_path: Path):
        """Should not fail if directory already exists."""
        round_dir = create_round_dir(tmp_path, 1)

        # Create again - should not raise
        result = create_round_dir(tmp_path, 1)
        assert result == round_dir
        assert result.exists()

    def test_multiple_rounds(self, tmp_path: Path):
        """Should create multiple round directories in same base."""
        r1 = create_round_dir(tmp_path, 1)
        r2 = create_round_dir(tmp_path, 2)
        r3 = create_round_dir(tmp_path, 3)

        assert r1.exists() and r1.name == "round-1"
        assert r2.exists() and r2.name == "round-2"
        assert r3.exists() and r3.name == "round-3"

    def test_returns_path_object(self, tmp_path: Path):
        """Should return Path object, not string."""
        result = create_round_dir(tmp_path, 1)
        assert isinstance(result, Path)
