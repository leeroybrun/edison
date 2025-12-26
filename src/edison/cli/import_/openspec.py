"""
Edison import openspec command.

SUMMARY: Import/sync OpenSpec changes into Edison tasks
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import (
    add_dry_run_flag,
    add_json_flag,
    add_repo_root_flag,
    OutputFormatter,
    get_repo_root,
)
from edison.core.import_.openspec import (
    OpenSpecImportError,
    parse_openspec_source,
    sync_openspec_changes,
)

SUMMARY = "Import/sync OpenSpec changes into Edison"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "source",
        help="Path to repo root, openspec/ directory, openspec/changes, or a change folder",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        help="Task ID prefix (default: openspec)",
    )
    parser.add_argument(
        "--include-archived",
        action="store_true",
        help="Include archived changes under openspec/changes/archive",
    )
    parser.add_argument(
        "--no-qa",
        action="store_true",
        help="Skip creating QA records for imported tasks",
    )
    add_dry_run_flag(parser)
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)
        source_path = Path(args.source)

        if not source_path.exists():
            formatter.error(
                f"Source not found: {source_path}",
                error_code="source_not_found",
            )
            return 1

        try:
            src = parse_openspec_source(source_path)
        except OpenSpecImportError as exc:
            formatter.error(str(exc), error_code="parse_error")
            return 1

        prefix = args.prefix if args.prefix else "openspec"
        create_qa = not getattr(args, "no_qa", False)
        dry_run = getattr(args, "dry_run", False)
        include_archived = bool(getattr(args, "include_archived", False))

        result = sync_openspec_changes(
            src,
            prefix=prefix,
            create_qa=create_qa,
            dry_run=dry_run,
            include_archived=include_archived,
            project_root=repo_root,
        )

        output = {
            "prefix": prefix,
            "dry_run": dry_run,
            "include_archived": include_archived,
            "created": result.created,
            "updated": result.updated,
            "flagged": result.flagged,
            "skipped": result.skipped,
            "errors": result.errors,
        }

        if formatter.json_mode:
            formatter.json_output(output)
        else:
            _print_text_summary(formatter, output, dry_run)

        if result.errors:
            return 1
        return 0

    except Exception as exc:
        formatter.error(exc, error_code="import_error")
        return 1


def _print_text_summary(formatter: OutputFormatter, output: dict, dry_run: bool) -> None:
    prefix_label = "DRY RUN: " if dry_run else ""
    formatter.text(f"{prefix_label}OpenSpec Import")
    formatter.text(f"Prefix: {output['prefix']}")
    if output.get("include_archived"):
        formatter.text("Including archived changes: Yes")
    formatter.text("")

    if output["created"]:
        formatter.text(f"Created ({len(output['created'])} tasks):")
        for task_id in output["created"]:
            formatter.text(f"  + {task_id}")
    if output["updated"]:
        formatter.text(f"Updated ({len(output['updated'])} tasks):")
        for task_id in output["updated"]:
            formatter.text(f"  ~ {task_id}")
    if output["flagged"]:
        formatter.text(f"Flagged as removed ({len(output['flagged'])} tasks):")
        for task_id in output["flagged"]:
            formatter.text(f"  ! {task_id}")
    if output["skipped"]:
        formatter.text(f"Skipped (state preserved) ({len(output['skipped'])} tasks):")
        for task_id in output["skipped"]:
            formatter.text(f"  - {task_id}")
    if output["errors"]:
        formatter.text(f"Errors ({len(output['errors'])}):")
        for err in output["errors"]:
            formatter.text(f"  ERROR: {err}")

    total = (
        len(output["created"])
        + len(output["updated"])
        + len(output["flagged"])
        + len(output["skipped"])
    )
    formatter.text("")
    formatter.text(f"Total: {total} tasks processed")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    register_args(p)
    parsed = p.parse_args()
    sys.exit(main(parsed))

