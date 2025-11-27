"""Unit tests for session/current.py - worktree-aware session ID resolution."""
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from edison.core.session.current import (
    get_current_session,
    set_current_session,
    clear_current_session,
    _is_in_worktree,
    _get_session_id_file,
    _read_session_id_file,
    _write_session_id_file,
    _delete_session_id_file,
    _SESSION_ID_FILENAME,
)
from edison.core.exceptions import SessionError


class TestIsInWorktree:
    """Tests for _is_in_worktree() helper."""

    def test_returns_true_when_in_worktree(self) -> None:
        """Should return True when is_worktree() returns True."""
        with patch("edison.core.utils.git.worktree.is_worktree", return_value=True):
            assert _is_in_worktree() is True

    def test_returns_false_when_not_in_worktree(self) -> None:
        """Should return False when is_worktree() returns False."""
        with patch("edison.core.utils.git.worktree.is_worktree", return_value=False):
            assert _is_in_worktree() is False

    def test_returns_false_on_exception(self) -> None:
        """Should return False when is_worktree() raises an exception."""
        with patch(
            "edison.core.utils.git.worktree.is_worktree",
            side_effect=Exception("Test error"),
        ):
            assert _is_in_worktree() is False


class TestGetSessionIdFile:
    """Tests for _get_session_id_file() helper."""

    def test_returns_path_when_in_worktree(self, tmp_path: Path) -> None:
        """Should return file path when in worktree."""
        with patch("edison.core.session.current._is_in_worktree", return_value=True):
            with patch(
                "edison.core.utils.paths.PathResolver.resolve_project_root",
                return_value=tmp_path,
            ):
                result = _get_session_id_file()
                assert result == tmp_path / ".project" / _SESSION_ID_FILENAME

    def test_returns_none_when_not_in_worktree(self) -> None:
        """Should return None when not in worktree."""
        with patch("edison.core.session.current._is_in_worktree", return_value=False):
            result = _get_session_id_file()
            assert result is None

    def test_returns_none_on_exception(self) -> None:
        """Should return None when PathResolver raises exception."""
        with patch("edison.core.session.current._is_in_worktree", return_value=True):
            with patch(
                "edison.core.utils.paths.PathResolver.resolve_project_root",
                side_effect=Exception("Test error"),
            ):
                result = _get_session_id_file()
                assert result is None


class TestReadSessionIdFile:
    """Tests for _read_session_id_file() helper."""

    def test_reads_valid_session_id(self, tmp_path: Path) -> None:
        """Should read and validate session ID from file."""
        session_file = tmp_path / ".session-id"
        session_file.write_text("test-session-123\n")

        with patch(
            "edison.core.session.current.validate_session_id",
            return_value="test-session-123",
        ):
            result = _read_session_id_file(session_file)
            assert result == "test-session-123"

    def test_returns_none_for_empty_file(self, tmp_path: Path) -> None:
        """Should return None for empty file."""
        session_file = tmp_path / ".session-id"
        session_file.write_text("")

        result = _read_session_id_file(session_file)
        assert result is None

    def test_returns_none_for_whitespace_only(self, tmp_path: Path) -> None:
        """Should return None for whitespace-only file."""
        session_file = tmp_path / ".session-id"
        session_file.write_text("   \n\t\n  ")

        result = _read_session_id_file(session_file)
        assert result is None

    def test_returns_none_on_read_error(self, tmp_path: Path) -> None:
        """Should return None when file cannot be read."""
        session_file = tmp_path / "nonexistent" / ".session-id"

        result = _read_session_id_file(session_file)
        assert result is None


class TestWriteSessionIdFile:
    """Tests for _write_session_id_file() helper."""

    def test_writes_session_id(self, tmp_path: Path) -> None:
        """Should write session ID to file."""
        session_file = tmp_path / ".project" / ".session-id"

        _write_session_id_file(session_file, "test-session-123")

        assert session_file.exists()
        assert session_file.read_text() == "test-session-123\n"

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """Should create parent directories if they don't exist."""
        session_file = tmp_path / "nested" / "dirs" / ".session-id"

        _write_session_id_file(session_file, "test-session-123")

        assert session_file.exists()
        assert session_file.parent.exists()

    def test_raises_session_error_on_write_failure(self, tmp_path: Path) -> None:
        """Should raise SessionError when write fails."""
        # Create a directory where file should be (causes write failure)
        session_file = tmp_path / ".session-id"
        session_file.mkdir()

        with pytest.raises(SessionError):
            _write_session_id_file(session_file, "test-session-123")


class TestDeleteSessionIdFile:
    """Tests for _delete_session_id_file() helper."""

    def test_deletes_existing_file(self, tmp_path: Path) -> None:
        """Should delete existing file."""
        session_file = tmp_path / ".session-id"
        session_file.write_text("test-session-123")

        _delete_session_id_file(session_file)

        assert not session_file.exists()

    def test_handles_nonexistent_file(self, tmp_path: Path) -> None:
        """Should not raise error for nonexistent file."""
        session_file = tmp_path / "nonexistent" / ".session-id"

        # Should not raise
        _delete_session_id_file(session_file)


class TestGetCurrentSession:
    """Tests for get_current_session() function."""

    def test_returns_stored_id_in_worktree(self, tmp_path: Path) -> None:
        """Should return stored session ID when in worktree and file exists."""
        session_file = tmp_path / ".project" / ".session-id"
        session_file.parent.mkdir(parents=True)
        session_file.write_text("stored-session-123\n")

        with patch("edison.core.session.current._is_in_worktree", return_value=True):
            with patch(
                "edison.core.session.current._get_session_id_file",
                return_value=session_file,
            ):
                with patch(
                    "edison.core.session.current._session_exists",
                    return_value=True,
                ):
                    with patch(
                        "edison.core.session.current.validate_session_id",
                        return_value="stored-session-123",
                    ):
                        result = get_current_session()
                        assert result == "stored-session-123"

    def test_falls_back_to_inference_when_stored_session_not_exists(
        self, tmp_path: Path
    ) -> None:
        """Should fall back to inference when stored session no longer exists."""
        session_file = tmp_path / ".project" / ".session-id"
        session_file.parent.mkdir(parents=True)
        session_file.write_text("stale-session-123\n")

        with patch("edison.core.session.current._is_in_worktree", return_value=True):
            with patch(
                "edison.core.session.current._get_session_id_file",
                return_value=session_file,
            ):
                with patch(
                    "edison.core.session.current._session_exists",
                    return_value=False,
                ):
                    with patch(
                        "edison.core.session.current._auto_session_for_owner",
                        return_value="inferred-session-456",
                    ):
                        with patch(
                            "edison.core.session.current.validate_session_id",
                            return_value="stale-session-123",
                        ):
                            result = get_current_session()
                            assert result == "inferred-session-456"

    def test_falls_back_to_inference_when_no_file(self) -> None:
        """Should fall back to inference when no session file exists."""
        with patch("edison.core.session.current._is_in_worktree", return_value=True):
            with patch(
                "edison.core.session.current._get_session_id_file",
                return_value=None,
            ):
                with patch(
                    "edison.core.session.current._auto_session_for_owner",
                    return_value="inferred-session-456",
                ):
                    result = get_current_session()
                    assert result == "inferred-session-456"

    def test_uses_inference_when_not_in_worktree(self) -> None:
        """Should use only inference when not in worktree."""
        with patch("edison.core.session.current._is_in_worktree", return_value=False):
            with patch(
                "edison.core.session.current._auto_session_for_owner",
                return_value="inferred-session-789",
            ):
                result = get_current_session()
                assert result == "inferred-session-789"

    def test_returns_none_when_no_session_found(self) -> None:
        """Should return None when no session can be determined."""
        with patch("edison.core.session.current._is_in_worktree", return_value=False):
            with patch(
                "edison.core.session.current._auto_session_for_owner",
                return_value=None,
            ):
                result = get_current_session()
                assert result is None


class TestSetCurrentSession:
    """Tests for set_current_session() function."""

    def test_writes_session_id_in_worktree(self, tmp_path: Path) -> None:
        """Should write session ID to file when in worktree."""
        session_file = tmp_path / ".project" / ".session-id"

        with patch("edison.core.session.current._is_in_worktree", return_value=True):
            with patch(
                "edison.core.session.current._get_session_id_file",
                return_value=session_file,
            ):
                with patch(
                    "edison.core.session.current.validate_session_id",
                    return_value="new-session-123",
                ):
                    set_current_session("new-session-123")

                    assert session_file.exists()
                    assert "new-session-123" in session_file.read_text()

    def test_raises_error_when_not_in_worktree(self) -> None:
        """Should raise SessionError when not in worktree."""
        with patch("edison.core.session.current._is_in_worktree", return_value=False):
            with patch(
                "edison.core.session.current.validate_session_id",
                return_value="test-session-123",
            ):
                with pytest.raises(SessionError) as exc_info:
                    set_current_session("test-session-123")

                assert "worktree" in str(exc_info.value).lower()

    def test_validates_session_id_format(self) -> None:
        """Should validate session ID format before writing."""
        from edison.core.session.id import SessionIdError

        with patch(
            "edison.core.session.current.validate_session_id",
            side_effect=SessionIdError("Invalid session ID"),
        ):
            with pytest.raises(SessionIdError):
                set_current_session("invalid..id")


class TestClearCurrentSession:
    """Tests for clear_current_session() function."""

    def test_deletes_file_in_worktree(self, tmp_path: Path) -> None:
        """Should delete session file when in worktree."""
        session_file = tmp_path / ".project" / ".session-id"
        session_file.parent.mkdir(parents=True)
        session_file.write_text("test-session-123\n")

        with patch("edison.core.session.current._is_in_worktree", return_value=True):
            with patch(
                "edison.core.session.current._get_session_id_file",
                return_value=session_file,
            ):
                clear_current_session()

                assert not session_file.exists()

    def test_noop_when_not_in_worktree(self) -> None:
        """Should be a no-op when not in worktree."""
        with patch("edison.core.session.current._is_in_worktree", return_value=False):
            # Should not raise
            clear_current_session()

    def test_handles_missing_file(self, tmp_path: Path) -> None:
        """Should handle case when file doesn't exist."""
        session_file = tmp_path / ".project" / ".session-id"

        with patch("edison.core.session.current._is_in_worktree", return_value=True):
            with patch(
                "edison.core.session.current._get_session_id_file",
                return_value=session_file,
            ):
                # Should not raise
                clear_current_session()
