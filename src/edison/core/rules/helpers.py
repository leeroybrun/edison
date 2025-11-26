"""
Helper functions for the Edison Rules system.

This module contains shared utility functions used by the registry
and engine components, including anchor extraction and file pattern matching.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from .errors import AnchorNotFoundError


def extract_anchor_content(source_file: Path, anchor: str) -> str:
    """
    Extract content between ANCHOR markers in a guideline file.

    Supports both explicit END markers and implicit termination at the next
    ANCHOR marker (or EOF when no END marker is present).

    Args:
        source_file: Path to the guideline file
        anchor: Name of the anchor to extract

    Returns:
        The content between the anchor markers

    Raises:
        FileNotFoundError: If the source file doesn't exist
        AnchorNotFoundError: If the anchor isn't found in the file
    """
    if not source_file.exists():
        raise FileNotFoundError(f"Guideline file not found: {source_file}")

    lines = source_file.read_text(encoding="utf-8").splitlines()
    start_idx: Optional[int] = None
    end_idx: Optional[int] = None

    start_marker = f"<!-- ANCHOR: {anchor} -->"
    end_marker = f"<!-- END ANCHOR: {anchor} -->"
    # Any ANCHOR start (used to detect implicit end)
    anchor_start_re = re.compile(r"<!--\s*ANCHOR:\s*.+?-->")

    for i, line in enumerate(lines):
        if start_marker in line:
            start_idx = i + 1  # content begins after the marker
            break

    if start_idx is None:
        raise AnchorNotFoundError(f"Anchor '{anchor}' not found in {source_file}")

    for j in range(start_idx, len(lines)):
        line = lines[j]
        if end_marker in line:
            end_idx = j
            break
        if anchor_start_re.search(line):
            end_idx = j
            break

    if end_idx is None:
        end_idx = len(lines)

    body_lines = lines[start_idx:end_idx]
    body = "\n".join(body_lines).rstrip()
    if body:
        body += "\n"
    return body


__all__ = [
    "extract_anchor_content",
]
