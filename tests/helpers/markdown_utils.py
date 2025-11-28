"""Markdown parsing utilities for test helpers.

Consolidates markdown parsing logic for extracting structured data from
task and QA markdown files.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def parse_task_metadata(content: str, task_id: str, state: Optional[str] = None) -> Dict[str, Any]:
    """Parse task markdown file and extract metadata.

    Args:
        content: Markdown file content
        task_id: Task ID
        state: Current state (if known)

    Returns:
        Dict with parsed metadata fields
    """
    metadata: Dict[str, Any] = {"id": task_id}
    if state is not None:
        metadata["state"] = state

    # Extract key fields from markdown
    for line in content.split("\n"):
        if line.startswith("- **Owner:**"):
            metadata["owner"] = line.split(":", 1)[1].strip()
        elif line.startswith("- **Wave:**"):
            metadata["wave"] = line.split(":", 1)[1].strip()
        elif line.startswith("- **Status:**"):
            metadata["status"] = line.split(":", 1)[1].strip()
        elif line.startswith("- **ID:**"):
            metadata["id"] = line.split(":", 1)[1].strip()

    return metadata


def parse_qa_metadata(content: str, qa_id: str, state: Optional[str] = None) -> Dict[str, Any]:
    """Parse QA markdown file and extract metadata.

    Args:
        content: Markdown file content
        qa_id: QA ID
        state: Current state (if known)

    Returns:
        Dict with parsed metadata fields
    """
    metadata: Dict[str, Any] = {"id": qa_id}
    if state is not None:
        metadata["state"] = state

    # Extract validators if present
    if "## Validators" in content:
        validators_section = content.split("## Validators")[1].split("##")[0]
        metadata["validators"] = []
        for line in validators_section.split("\n"):
            if line.strip().startswith("- "):
                metadata["validators"].append(line.strip()[2:])

    return metadata


def extract_primary_files(content: str) -> List[str]:
    """Extract primary files list from markdown content.

    Args:
        content: Markdown file content

    Returns:
        List of primary file paths
    """
    primary_files: List[str] = []

    if "## Primary Files" in content:
        files_section = content.split("## Primary Files")[1].split("##")[0]
        for line in files_section.split("\n"):
            line = line.strip()
            if line.startswith("- `") and line.endswith("`"):
                # Extract file path between backticks
                file_path = line[3:-1]
                primary_files.append(file_path)

    return primary_files
