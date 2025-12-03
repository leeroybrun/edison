"""Markdown parsing utilities for test helpers.

Consolidates markdown parsing logic for extracting structured data from
task and QA markdown files.

NOTE: All task/QA files use YAML frontmatter format (not HTML comments).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.utils.text import format_frontmatter, parse_frontmatter


def parse_task_metadata(content: str, task_id: str, state: Optional[str] = None) -> Dict[str, Any]:
    """Parse task markdown file and extract metadata.

    Args:
        content: Markdown file content
        task_id: Task ID
        state: Current state (if known)

    Returns:
        Dict with parsed metadata fields
    """
    # Try YAML frontmatter first
    doc = parse_frontmatter(content)
    if doc.frontmatter:
        metadata = dict(doc.frontmatter)
        metadata["id"] = metadata.get("id", task_id)
        if state is not None:
            metadata["state"] = state
        return metadata

    # Fallback for legacy format (shouldn't happen with new code)
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
    # Try YAML frontmatter first
    doc = parse_frontmatter(content)
    if doc.frontmatter:
        metadata = dict(doc.frontmatter)
        metadata["id"] = metadata.get("id", qa_id)
        if state is not None:
            metadata["state"] = state
        return metadata

    # Fallback for legacy format (shouldn't happen with new code)
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


def create_task_file(
    path: Path,
    task_id: str,
    title: str = "Test Task",
    state: str = "todo",
    session_id: str | None = None,
) -> Path:
    """Create a markdown task file with YAML frontmatter.

    Args:
        path: Where to create the file
        task_id: Task identifier
        title: Task title
        state: Task state (todo, wip, done)
        session_id: Optional session ID

    Returns:
        Path to created file
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    frontmatter_data: Dict[str, Any] = {
        "id": task_id,
        "title": title,
    }
    if session_id:
        frontmatter_data["session_id"] = session_id

    content = format_frontmatter(frontmatter_data)
    content += f"\n# {title}\n\nTask description here.\n"

    path.write_text(content, encoding="utf-8")
    return path


def create_qa_file(
    path: Path,
    qa_id: str,
    title: str = "Test QA",
    state: str = "pending",
    validator: str = "test-validator",
    task_id: str | None = None,
) -> Path:
    """Create a markdown QA file with YAML frontmatter.

    Args:
        path: Where to create the file
        qa_id: QA identifier
        title: QA title
        state: QA state
        validator: Validator owner
        task_id: Associated task ID

    Returns:
        Path to created file
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    frontmatter_data: Dict[str, Any] = {
        "id": qa_id,
        "title": title,
        "validator_owner": validator,
    }
    if task_id:
        frontmatter_data["task_id"] = task_id

    content = format_frontmatter(frontmatter_data)
    content += f"\n# {title}\n\nQA description here.\n"

    path.write_text(content, encoding="utf-8")
    return path


def create_markdown_task(
    path: Path,
    task_id: str,
    title: str,
    state: str | None = None,
    session_id: str | None = None,
) -> None:
    """Create a raw markdown task file for testing with YAML frontmatter.

    This helper creates task files directly as markdown, bypassing the repository layer.
    Used for testing task discovery and parsing logic.

    Args:
        path: Full path where to create the task file (including filename)
        task_id: Task identifier
        title: Task title
        state: Task state (e.g., 'todo', 'wip', 'done'). If None, infers from parent directory name.
        session_id: Optional session ID to include in metadata

    Note:
        - Creates parent directories if they don't exist
        - If state is not provided, uses path.parent.name as the state
        - This matches the filesystem convention where tasks are in state-named directories
        - Uses YAML frontmatter format (not HTML comments)
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    # Infer state from parent directory if not provided
    if state is None:
        state = path.parent.name

    frontmatter_data: Dict[str, Any] = {
        "id": task_id,
        "title": title,
    }
    if session_id:
        frontmatter_data["session_id"] = session_id

    content = format_frontmatter(frontmatter_data)
    content += f"\n# {title}\n\nTask description here.\n"

    path.write_text(content, encoding="utf-8")
