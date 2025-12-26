"""Unified file writer for composition output.

Provides consistent file writing with:
- Directory creation
- Encoding handling
- Permission setting for executables
- JSON/YAML formatting
"""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml


class CompositionFileWriter:
    """Unified file writer for composed content.

    Handles all composition output writing with consistent behavior:
    - Creates parent directories automatically
    - Uses UTF-8 encoding by default
    - Formats JSON with consistent indentation
    - Handles YAML serialization
    - Sets executable permissions when needed
    """

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        encoding: str = "utf-8",
        json_indent: int = 2,
    ) -> None:
        """Initialize the file writer.

        Args:
            base_dir: Base directory for relative paths (optional).
            encoding: File encoding (default: utf-8).
            json_indent: JSON indentation level (default: 2).
        """
        self.base_dir = base_dir
        self.encoding = encoding
        self.json_indent = json_indent

    def _resolve_path(self, path: Union[str, Path]) -> Path:
        """Resolve path, making absolute if base_dir is set."""
        path = Path(path)
        if not path.is_absolute() and self.base_dir:
            return self.base_dir / path
        return path

    def _ensure_parent(self, path: Path) -> None:
        """Ensure parent directory exists."""
        path.parent.mkdir(parents=True, exist_ok=True)

    def write_text(
        self,
        path: Union[str, Path],
        content: str,
        encoding: Optional[str] = None,
    ) -> Path:
        """Write text content to file.

        Args:
            path: Output file path.
            content: Text content to write.
            encoding: Optional encoding override.

        Returns:
            Resolved path that was written.
        """
        resolved = self._resolve_path(path)
        self._ensure_parent(resolved)
        resolved.write_text(content, encoding=encoding or self.encoding)
        return resolved

    def write_text_with_policy(
        self,
        path: Union[str, Path],
        content: str,
        *,
        policy: Optional["WritePolicy"] = None,  # type: ignore[name-defined]
        encoding: Optional[str] = None,
    ) -> Path:
        """Write content applying an optional write policy."""
        if policy is None or getattr(policy, "mode", "replace") == "replace":
            return self.write_text(path, content, encoding=encoding)

        mode = getattr(policy, "mode", "replace")
        if mode != "markers":
            return self.write_text(path, content, encoding=encoding)

        begin = getattr(policy, "begin_marker", None)
        end = getattr(policy, "end_marker", None)
        on_missing = getattr(policy, "on_missing", "prepend")
        if not isinstance(begin, str) or not begin.strip():
            raise ValueError("markers write_policy requires begin_marker")
        if not isinstance(end, str) or not end.strip():
            raise ValueError("markers write_policy requires end_marker")

        from edison.core.composition.output.managed_blocks import apply_managed_block

        resolved = self._resolve_path(path)
        existing = ""
        if resolved.exists():
            existing = resolved.read_text(encoding=encoding or self.encoding)

        updated = apply_managed_block(
            existing_text=existing,
            begin_marker=begin,
            end_marker=end,
            new_body=content,
            on_missing=on_missing,
        ).updated_text

        return self.write_text(resolved, updated, encoding=encoding)

    def write_json(
        self,
        path: Union[str, Path],
        data: Any,
        indent: Optional[int] = None,
        sort_keys: bool = False,
    ) -> Path:
        """Write JSON data to file.

        Args:
            path: Output file path.
            data: Data to serialize as JSON.
            indent: Optional indent override.
            sort_keys: Whether to sort keys (default: False).

        Returns:
            Resolved path that was written.
        """
        resolved = self._resolve_path(path)
        self._ensure_parent(resolved)

        json_str = json.dumps(
            data,
            indent=indent or self.json_indent,
            sort_keys=sort_keys,
            ensure_ascii=False,
        )
        resolved.write_text(json_str + "\n", encoding=self.encoding)
        return resolved

    def write_yaml(
        self,
        path: Union[str, Path],
        data: Any,
        default_flow_style: bool = False,
        allow_unicode: bool = True,
    ) -> Path:
        """Write YAML data to file.

        Args:
            path: Output file path.
            data: Data to serialize as YAML.
            default_flow_style: Use flow style for simple values.
            allow_unicode: Allow unicode characters.

        Returns:
            Resolved path that was written.
        """
        resolved = self._resolve_path(path)
        self._ensure_parent(resolved)

        yaml_str = yaml.dump(
            data,
            default_flow_style=default_flow_style,
            allow_unicode=allow_unicode,
            sort_keys=False,
        )
        resolved.write_text(yaml_str, encoding=self.encoding)
        return resolved

    def write_executable(
        self,
        path: Union[str, Path],
        content: str,
        encoding: Optional[str] = None,
    ) -> Path:
        """Write executable script file.

        Sets executable permissions (chmod +x) after writing.

        Args:
            path: Output file path.
            content: Script content to write.
            encoding: Optional encoding override.

        Returns:
            Resolved path that was written.
        """
        resolved = self.write_text(path, content, encoding)

        # Set executable permissions
        current_mode = resolved.stat().st_mode
        resolved.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        return resolved

    def write_markdown(
        self,
        path: Union[str, Path],
        content: str,
        frontmatter: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """Write markdown file with optional YAML frontmatter.

        Args:
            path: Output file path.
            content: Markdown content.
            frontmatter: Optional frontmatter dict to prepend.

        Returns:
            Resolved path that was written.
        """
        if frontmatter:
            yaml_str = yaml.dump(
                frontmatter,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
            full_content = f"---\n{yaml_str}---\n\n{content}"
        else:
            full_content = content

        return self.write_text(path, full_content)

    def copy_file(
        self,
        source: Union[str, Path],
        dest: Union[str, Path],
    ) -> Path:
        """Copy file from source to destination.

        Args:
            source: Source file path.
            dest: Destination file path.

        Returns:
            Resolved destination path.
        """
        source_path = Path(source)
        dest_resolved = self._resolve_path(dest)
        self._ensure_parent(dest_resolved)

        content = source_path.read_bytes()
        dest_resolved.write_bytes(content)

        return dest_resolved
