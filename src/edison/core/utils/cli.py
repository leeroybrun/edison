from __future__ import annotations

"""CLI utilities shared across Edison scripts.

All defaults are hardcoded here to avoid circular dependencies with ConfigManager.
The helpers are intentionally small and side‑effect free to keep them easy to
test without mocks.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable, List, Mapping, Sequence

# Default configuration (hardcoded to avoid circular dependency with ConfigManager)
DEFAULT_CLI_CONFIG: dict[str, Any] = {
    "json": {
        "indent": 2,
        "sort_keys": True,
        "ensure_ascii": False,
    },
    "table": {
        "padding": 1,
        "column_gap": 2,
    },
    "confirm": {
        "assume_yes_env": "",
        "default": False,
    },
    "output": {
        "success_prefix": "[OK]",
        "error_prefix": "[ERR]",
        "warning_prefix": "[WARN]",
        "use_color": False,
    },
}


def _cfg() -> dict:
    """Return default CLI configuration.

    Note: ConfigManager is intentionally not imported here to avoid circular
    dependencies. Returns hardcoded defaults.
    """
    return DEFAULT_CLI_CONFIG


def parse_common_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Attach common Edison CLI flags to ``parser``.

    Flags:
        --json      Output machine-readable JSON
        -y/--yes    Assume yes for confirmations
        --repo-root Override repository root detection
    """
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("-y", "--yes", dest="yes", action="store_true", help="Assume yes for prompts")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root override (bypasses auto-detection)",
    )
    return parser


def session_parent(help_text: str | None = None, *, required: bool = False) -> argparse.ArgumentParser:
    """Return an argparse parent that adds the ``--session`` flag.

    Args:
        help_text: Override the default help copy.
        required: When ``True``, mark the flag as required for commands that
            must operate within an explicit session.
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--session",
        required=required,
        help=help_text
        or "Session ID to scope the command (e.g., sess-001). Auto-detects from the current worktree when omitted.",
    )
    return parser


def dry_run_parent(help_text: str | None = None) -> argparse.ArgumentParser:
    """Return an argparse parent that adds a standard ``--dry-run`` toggle."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=help_text or "Preview actions without making changes.",
    )
    return parser


def output_json(data: Any, pretty: bool = True) -> str:
    """Return JSON string using config-driven formatting."""
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


def output_table(rows: Iterable[Sequence[Any] | Mapping[str, Any]], headers: Sequence[str]) -> str:
    """Format rows as a plain-text table using config padding and spacing."""
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
    """Prompt the user for confirmation using config defaults and env overrides."""
    cfg = _cfg()["confirm"]
    assume_env = cfg.get("assume_yes_env") or ""
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
    """Print an error message with configured prefix and return the exit code."""
    prefix = _cfg()["output"]["error_prefix"]
    print(f"{prefix} {message}", file=sys.stderr)
    return int(exit_code)


def success(message: str) -> None:
    """Print a success message with configured prefix."""
    prefix = _cfg()["output"]["success_prefix"]
    print(f"{prefix} {message}")
