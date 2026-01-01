"""
Edison plan show command.

SUMMARY: Show raw plan Markdown
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root

SUMMARY = "Show raw plan Markdown"


def _get_plans_dir(project_root: Path) -> Path:
    """Get the plans directory path."""
    return project_root / ".project" / "plans"


def _find_plan(plans_dir: Path, plan_id: str) -> Optional[Path]:
    """Find a plan file by ID or name.

    Args:
        plans_dir: Directory containing plans
        plan_id: Plan identifier (can be with or without .md extension)

    Returns:
        Path to the plan file if found, None otherwise
    """
    if not plans_dir.exists():
        return None

    # Try exact match first (with .md extension)
    plan_path = plans_dir / f"{plan_id}.md"
    if plan_path.exists():
        return plan_path

    # Try without extension if already has .md
    if plan_id.endswith(".md"):
        plan_path = plans_dir / plan_id
        if plan_path.exists():
            return plan_path

    # Try case-insensitive search
    plan_id_lower = plan_id.lower()
    for p in plans_dir.glob("*.md"):
        if p.stem.lower() == plan_id_lower:
            return p

    return None


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command arguments.

    Args:
        parser: Argument parser to add arguments to
    """
    parser.add_argument(
        "plan_id",
        help="Plan identifier (e.g., 001-feature-auth)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Execute the plan show command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    try:
        project_root = get_repo_root(args)
        plans_dir = _get_plans_dir(project_root)
        plan_id = str(args.plan_id)

        plan_path = _find_plan(plans_dir, plan_id)
        if plan_path is None:
            raise FileNotFoundError(f"Plan '{plan_id}' not found in {plans_dir}")

        content = plan_path.read_text(encoding="utf-8", errors="strict")

        if formatter.json_mode:
            # Normalize the plan ID (stem without extension)
            normalized_id = plan_path.stem
            formatter.json_output(
                {
                    "recordType": "plan",
                    "id": normalized_id,
                    "path": str(plan_path),
                    "content": content,
                }
            )
        else:
            formatter.text(content)
        return 0
    except Exception as e:
        formatter.error(e, error_code="plan_show_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
