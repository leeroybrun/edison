"""Shared utilities for QA module.

This module contains helper functions used across the QA module to avoid duplication.
"""
from __future__ import annotations

from typing import List


def parse_primary_files(content: str) -> List[str]:
    """Extract primary files from task markdown content.

    This function parses task markdown to find the "Primary Files / Areas" section
    and extracts file paths from it. It handles multiple formats:

    1. Inline format: "Primary Files / Areas: file1, file2"
    2. Bulleted list format:
       ## Primary Files / Areas
       - file1
       - file2
    3. Alternative header: "- **Primary Files / Areas**"
    4. Combined inline + bulleted format

    Args:
        content: The task markdown content as a string.

    Returns:
        List of file paths extracted from the primary files section.
        Empty list if section not found or has no files.

    Examples:
        >>> content = '''
        ... ## Primary Files / Areas
        ... - src/app.ts
        ... - src/utils.ts
        ... '''
        >>> parse_primary_files(content)
        ['src/app.ts', 'src/utils.ts']

        >>> content = "Primary Files / Areas: src/main.ts, src/helper.ts"
        >>> parse_primary_files(content)
        ['src/main.ts', 'src/helper.ts']
    """
    files: List[str] = []
    capture = False

    for line in content.splitlines():
        # Check if this is the Primary Files / Areas header
        if "Primary Files / Areas" in line or "- **Primary Files" in line:
            capture = True

            # Handle inline format: "Primary Files / Areas: file1, file2"
            if ":" in line:
                parts = line.split(":", 1)
                if len(parts) > 1 and parts[1].strip():
                    # Extract comma-separated files from the inline format
                    inline_files = [f.strip() for f in parts[1].split(",") if f.strip()]
                    files.extend(inline_files)
            continue

        # Stop capturing at the next section header
        if capture and line.startswith("## "):
            break

        # Extract files from bullet points
        if capture and line.strip().startswith("-"):
            # Split on the first '-' and take the rest
            file_path = line.split("-", 1)[1].strip()
            if file_path:
                files.append(file_path)

    return files


__all__ = ["parse_primary_files"]
