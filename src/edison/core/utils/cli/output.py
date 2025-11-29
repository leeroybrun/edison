"""CLI output formatting helpers.

This module provides output formatting functions for JSON, tables, user prompts,
and status messages used by Edison CLI commands.

Extracted from the original cli.py god file to follow Single Responsibility Principle.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Iterable, List, Mapping, Sequence


def _cfg() -> dict:
    """Return CLI configuration from YAML without fallbacks.

    Raises:
        RuntimeError: If config cannot be loaded or cli section is missing
    """
    # Lazy import to avoid circular import
    from edison.core.utils.config import load_validated_section
    return load_validated_section(
        "cli",
        required_subsections=["json", "table", "confirm", "output"]
    )


def output_json(data: Any, pretty: bool = True) -> str:
    """Return JSON string using config-driven formatting.

    Args:
        data: The data to serialize to JSON
        pretty: If True, format with indentation; if False, compact format

    Returns:
        JSON string representation of the data
    """
    cfg = _cfg()["json"]
    kwargs = {
        "sort_keys": cfg["sort_keys"],
        "ensure_ascii": cfg["ensure_ascii"],
    }
    if pretty:
        kwargs["indent"] = cfg["indent"]
    else:
        kwargs["separators"] = (",", ":")
    return json.dumps(data, **kwargs)


def output_table(
    rows: Iterable[Sequence[Any] | Mapping[str, Any]], headers: Sequence[str]
) -> str:
    """Format rows as a plain-text table using config padding and spacing.

    Args:
        rows: Iterable of rows, where each row is either a sequence or a mapping
        headers: Column headers

    Returns:
        Formatted table as a string
    """
    cfg = _cfg()["table"]
    padding = cfg["padding"]
    gap = " " * cfg["column_gap"]

    normalized_rows: List[List[str]] = []
    for row in rows:
        if isinstance(row, Mapping):
            normalized_rows.append([str(row.get(h, "")) for h in headers])
        else:
            normalized_rows.append([str(item) for item in row])

    widths: List[int] = []
    for idx, header in enumerate(headers):
        vals = [len(r[idx]) for r in normalized_rows] if normalized_rows else []
        widths.append(max([len(str(header)), *vals], default=len(str(header))))

    def _format_row(parts: List[str]) -> str:
        padded_cells: List[str] = []
        for idx, cell in enumerate(parts):
            cell_str = str(cell)
            full_width = widths[idx]
            content = cell_str.ljust(full_width)
            padded_cells.append(f"{content}{' ' * padding}")
        return gap.join(padded_cells)

    lines: List[str] = []
    lines.append(_format_row([str(h) for h in headers]))
    if normalized_rows:
        for row in normalized_rows:
            lines.append(_format_row(row))
    return "\n".join(lines)


def confirm(message: str, default: bool = False) -> bool:
    """Prompt the user for confirmation using config defaults and env overrides.

    Args:
        message: The confirmation prompt message
        default: Default value if user just presses Enter

    Returns:
        True if user confirms, False otherwise
    """
    cfg = _cfg()["confirm"]
    assume_env = cfg.get("assume_yes_env") or ""
    # Use function parameter as default for cfg.get
    configured_default = bool(cfg.get("default", default))
    effective_default = configured_default

    prompt_suffix = "[Y/n]" if effective_default else "[y/N]"
    prompt = f"{message} {prompt_suffix} "

    if assume_env and os.environ.get(assume_env):
        print(message)
        return True

    try:
        resp = input(prompt).strip().lower()
    except EOFError:
        resp = ""

    if resp in ("y", "yes"):
        return True
    if resp in ("n", "no"):
        return False
    return bool(effective_default)


def error(message: str, exit_code: int = 1) -> int:
    """Print an error message with configured prefix and return the exit code.

    Args:
        message: Error message to display
        exit_code: Exit code to return (default: 1)

    Returns:
        The exit code value
    """
    prefix = _cfg()["output"]["error_prefix"]
    print(f"{prefix} {message}", file=sys.stderr)
    return int(exit_code)


def success(message: str) -> None:
    """Print a success message with configured prefix.

    Args:
        message: Success message to display
    """
    prefix = _cfg()["output"]["success_prefix"]
    print(f"{prefix} {message}")


__all__ = [
    "output_json",
    "output_table",
    "confirm",
    "error",
    "success",
]



