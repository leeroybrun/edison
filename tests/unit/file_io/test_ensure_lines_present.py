from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.utils.io import ensure_lines_present


def test_ensure_lines_present_creates_file_when_missing(tmp_path: Path) -> None:
    target = tmp_path / ".gitignore"
    assert not target.exists()

    changed = ensure_lines_present(target, [".edison/_generated/", ".project/sessions/"])
    assert changed is True
    assert target.exists()

    text = target.read_text(encoding="utf-8")
    assert ".edison/_generated/" in text
    assert ".project/sessions/" in text


def test_ensure_lines_present_appends_only_missing_lines(tmp_path: Path) -> None:
    target = tmp_path / ".gitignore"
    target.write_text(".edison/_generated/\n", encoding="utf-8")

    changed = ensure_lines_present(target, [".edison/_generated/", ".project/sessions/"])
    assert changed is True

    text = target.read_text(encoding="utf-8")
    assert text.count(".edison/_generated/") == 1
    assert ".project/sessions/" in text


def test_ensure_lines_present_is_idempotent(tmp_path: Path) -> None:
    target = tmp_path / ".gitignore"
    target.write_text(".edison/_generated/\n.project/sessions/\n", encoding="utf-8")

    changed = ensure_lines_present(target, [".edison/_generated/", ".project/sessions/"])
    assert changed is False


def test_ensure_lines_present_does_not_create_when_create_false(tmp_path: Path) -> None:
    target = tmp_path / ".gitignore"
    with pytest.raises(FileNotFoundError):
        ensure_lines_present(target, [".edison/_generated/"], create=False)

