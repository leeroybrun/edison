"""Composition utilities for partially managed text files using begin/end markers.

Used to preserve manual edits outside a managed block while allowing Edison to
fully control the content inside the block.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


OnMissingMode = Literal["prepend", "append", "error"]


@dataclass(frozen=True)
class ManagedBlockResult:
    """Result of applying a managed block update."""

    updated_text: str
    changed: bool
    action: str  # "replaced" | "inserted" | "unchanged"


def apply_managed_block(
    *,
    existing_text: str,
    begin_marker: str,
    end_marker: str,
    new_body: str,
    on_missing: OnMissingMode = "prepend",
) -> ManagedBlockResult:
    """Replace or insert a managed block delimited by markers.

    Rules:
    - If both markers exist (in order), replace the entire block (markers included).
    - If neither marker exists, insert a new block at top or bottom.
    - If only one marker exists, fail closed.
    """
    if not begin_marker.strip() or not end_marker.strip():
        raise ValueError("Markers must be non-empty strings")

    begin_idx = _find_marker_on_own_line(existing_text, begin_marker)
    end_idx = (
        _find_marker_on_own_line(
            existing_text,
            end_marker,
            from_index=begin_idx + len(begin_marker),
        )
        if begin_idx != -1
        else _find_marker_on_own_line(existing_text, end_marker)
    )

    has_begin = begin_idx != -1
    has_end = end_idx != -1
    if has_begin != has_end:
        raise ValueError("Invalid marker state: only one marker present")

    block = _format_block(begin_marker=begin_marker, end_marker=end_marker, body=new_body)

    if has_begin and has_end:
        if end_idx < begin_idx:
            raise ValueError("Invalid marker state: end marker appears before begin marker")

        end_line_end = _line_end_index(existing_text, end_idx + len(end_marker))
        replaced = existing_text[:begin_idx] + block + existing_text[end_line_end:]
        if replaced == existing_text:
            return ManagedBlockResult(updated_text=existing_text, changed=False, action="unchanged")
        return ManagedBlockResult(updated_text=replaced, changed=True, action="replaced")

    if on_missing == "error":
        raise ValueError("Markers not found")

    if not existing_text:
        return ManagedBlockResult(updated_text=block, changed=True, action="inserted")

    if on_missing == "prepend":
        updated = block + "\n" + existing_text.lstrip("\n")
        return ManagedBlockResult(updated_text=updated, changed=True, action="inserted")

    updated = existing_text.rstrip() + "\n\n" + block
    return ManagedBlockResult(updated_text=updated, changed=True, action="inserted")


def _format_block(*, begin_marker: str, end_marker: str, body: str) -> str:
    b = (body or "").rstrip()
    if b:
        return f"{begin_marker}\n{b}\n{end_marker}\n"
    return f"{begin_marker}\n{end_marker}\n"


def _line_end_index(text: str, from_index: int) -> int:
    """Return the index immediately after the line containing from_index."""
    nl = text.find("\n", from_index)
    if nl == -1:
        return len(text)
    return nl + 1


def _find_marker_on_own_line(text: str, marker: str, *, from_index: int = 0) -> int:
    """Find marker ensuring it appears alone on a line (ignoring whitespace)."""
    idx = text.find(marker, from_index)
    while idx != -1:
        if _marker_on_own_line(text, idx, len(marker)):
            return idx
        idx = text.find(marker, idx + len(marker))
    return -1


def _marker_on_own_line(text: str, idx: int, marker_len: int) -> bool:
    left = idx - 1
    while left >= 0 and text[left] != "\n":
        if text[left] not in (" ", "\t", "\r"):
            return False
        left -= 1

    right = idx + marker_len
    while right < len(text) and text[right] != "\n":
        if text[right] not in (" ", "\t", "\r"):
            return False
        right += 1

    return True


__all__ = ["OnMissingMode", "ManagedBlockResult", "apply_managed_block"]

