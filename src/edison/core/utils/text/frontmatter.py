"""YAML frontmatter parsing utilities.

This module provides utilities for parsing and formatting YAML frontmatter
in task and QA markdown files. The frontmatter is delimited by '---' markers
at the start of the file.

Example:
    ```yaml
    ---
    id: "task-150"
    owner: claude
    session_id: python-pid-123
    ---

    # Task Title
    ```
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import yaml


# Regex pattern to match YAML frontmatter at the start of a file
# Matches content between the first pair of '---' markers
FRONTMATTER_PATTERN = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n?",
    re.DOTALL | re.MULTILINE,
)


@dataclass
class ParsedDocument:
    """Result of parsing a document with YAML frontmatter.
    
    Attributes:
        frontmatter: Parsed YAML frontmatter as a dictionary
        content: The markdown content after the frontmatter
        raw_frontmatter: The raw YAML string (for debugging)
    """
    frontmatter: Dict[str, Any]
    content: str
    raw_frontmatter: str


def parse_frontmatter(content: str) -> ParsedDocument:
    """Parse YAML frontmatter from markdown content.
    
    Extracts the YAML frontmatter from between the first pair of '---'
    delimiters at the start of the file. The frontmatter is parsed
    as YAML and returned along with the remaining content.
    
    Args:
        content: Full markdown content including frontmatter
        
    Returns:
        ParsedDocument with frontmatter dict, content, and raw YAML
        
    Raises:
        ValueError: If frontmatter is malformed or YAML is invalid
        
    Example:
        >>> doc = parse_frontmatter('''---
        ... id: "task-150"
        ... owner: claude
        ... ---
        ... 
        ... # Task Title
        ... ''')
        >>> doc.frontmatter['id']
        'task-150'
        >>> doc.content.strip()
        '# Task Title'
    """
    match = FRONTMATTER_PATTERN.match(content)
    
    if not match:
        # No frontmatter found - return empty frontmatter and full content
        return ParsedDocument(
            frontmatter={},
            content=content,
            raw_frontmatter="",
        )
    
    raw_yaml = match.group(1)
    remaining_content = content[match.end():]
    
    try:
        parsed = yaml.safe_load(raw_yaml)
        if parsed is None:
            parsed = {}
        if not isinstance(parsed, dict):
            raise ValueError(f"Frontmatter must be a YAML mapping, got {type(parsed).__name__}")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in frontmatter: {e}") from e
    
    return ParsedDocument(
        frontmatter=parsed,
        content=remaining_content,
        raw_frontmatter=raw_yaml,
    )


def format_frontmatter(data: Dict[str, Any], *, exclude_none: bool = True) -> str:
    """Format a dictionary as YAML frontmatter.
    
    Converts a dictionary to YAML format wrapped in '---' delimiters.
    The output is suitable for prepending to markdown content.
    
    Args:
        data: Dictionary to format as frontmatter
        exclude_none: If True, exclude keys with None values (default: True)
        
    Returns:
        YAML frontmatter string with '---' delimiters
        
    Example:
        >>> print(format_frontmatter({'id': 'task-150', 'owner': 'claude'}))
        ---
        id: task-150
        owner: claude
        ---
        <BLANKLINE>
    """
    if exclude_none:
        data = {k: v for k, v in data.items() if v is not None}
    
    # Use safe_dump with settings for readable output
    yaml_content = yaml.safe_dump(
        data,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,  # Preserve insertion order
    )
    
    return f"---\n{yaml_content}---\n"


def extract_frontmatter_batch(file_contents: List[Tuple[str, str]]) -> List[Tuple[str, Dict[str, Any]]]:
    """Extract frontmatter from multiple files efficiently.
    
    This function is designed for batch processing when you need to
    extract frontmatter from many files (e.g., for indexing).
    
    Args:
        file_contents: List of (file_path, content) tuples
        
    Returns:
        List of (file_path, frontmatter_dict) tuples
        Files with invalid/missing frontmatter will have empty dicts
        
    Example:
        >>> files = [
        ...     ("task-1.md", "---\\nid: task-1\\n---\\n# Task 1"),
        ...     ("task-2.md", "---\\nid: task-2\\n---\\n# Task 2"),
        ... ]
        >>> results = extract_frontmatter_batch(files)
        >>> results[0][1]['id']
        'task-1'
    """
    results: List[Tuple[str, Dict[str, Any]]] = []
    
    for file_path, content in file_contents:
        try:
            doc = parse_frontmatter(content)
            results.append((file_path, doc.frontmatter))
        except (ValueError, yaml.YAMLError):
            # Skip files with invalid frontmatter
            results.append((file_path, {}))
    
    return results


def has_frontmatter(content: str) -> bool:
    """Check if content has YAML frontmatter.
    
    Args:
        content: Markdown content to check
        
    Returns:
        True if content starts with '---' frontmatter delimiters
    """
    return bool(FRONTMATTER_PATTERN.match(content))


def update_frontmatter(
    content: str,
    updates: Dict[str, Any],
    *,
    remove_keys: Optional[List[str]] = None,
) -> str:
    """Update frontmatter values in existing content.
    
    Parses the existing frontmatter, applies updates, and returns
    the full content with updated frontmatter.
    
    Args:
        content: Original markdown content with frontmatter
        updates: Dictionary of key-value pairs to update/add
        remove_keys: Optional list of keys to remove from frontmatter
        
    Returns:
        Full content with updated frontmatter
        
    Example:
        >>> original = "---\\nid: task-1\\n---\\n# Title"
        >>> updated = update_frontmatter(original, {'owner': 'claude'})
        >>> 'owner: claude' in updated
        True
    """
    doc = parse_frontmatter(content)
    
    # Apply updates
    doc.frontmatter.update(updates)
    
    # Remove specified keys
    if remove_keys:
        for key in remove_keys:
            doc.frontmatter.pop(key, None)
    
    # Reconstruct document
    new_frontmatter = format_frontmatter(doc.frontmatter)
    return new_frontmatter + doc.content


__all__ = [
    "ParsedDocument",
    "parse_frontmatter",
    "format_frontmatter",
    "extract_frontmatter_batch",
    "has_frontmatter",
    "update_frontmatter",
    "FRONTMATTER_PATTERN",
]

