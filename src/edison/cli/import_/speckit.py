"""
Edison import speckit command.

SUMMARY: Import/sync SpecKit tasks into Edison task management
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import (
    add_json_flag,
    add_repo_root_flag,
    add_dry_run_flag,
    OutputFormatter,
    get_repo_root,
)
from edison.core.import_.speckit import (
    parse_feature_folder,
    sync_speckit_feature,
    SpecKitImportError,
)

SUMMARY = "Import/sync SpecKit tasks into Edison"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "source",
        help="Path to SpecKit feature folder or tasks.md file",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        help="Custom task ID prefix (default: feature folder name)",
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
    """Import SpecKit tasks into Edison."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)
        source_path = Path(args.source)

        # Validate source exists
        if not source_path.exists():
            formatter.error(
                f"Source not found: {source_path}",
                error_code="source_not_found",
            )
            return 1

        # Parse the feature folder
        try:
            feature = parse_feature_folder(source_path)
        except SpecKitImportError as e:
            formatter.error(str(e), error_code="parse_error")
            return 1

        # Determine prefix
        prefix = args.prefix if args.prefix else feature.name

        # Determine if we should create QA records
        create_qa = not getattr(args, "no_qa", False)

        # Dry run check
        dry_run = getattr(args, "dry_run", False)

        # Sync the feature
        result = sync_speckit_feature(
            feature,
            prefix=prefix,
            create_qa=create_qa,
            dry_run=dry_run,
            project_root=repo_root,
        )

        # Format output
        output = {
            "feature": feature.name,
            "prefix": prefix,
            "dry_run": dry_run,
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

        # Return error if there were errors
        if result.errors:
            return 1

        return 0

    except Exception as e:
        formatter.error(e, error_code="import_error")
        return 1


def _print_text_summary(
    formatter: OutputFormatter,
    output: dict,
    dry_run: bool,
) -> None:
    """Print human-readable summary of import results."""
    prefix_label = "DRY RUN: " if dry_run else ""

    formatter.text(f"{prefix_label}SpecKit Import: {output['feature']}")
    formatter.text(f"Prefix: {output['prefix']}")
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
        for error in output["errors"]:
            formatter.text(f"  ERROR: {error}")

    # Summary line
    total = (
        len(output["created"])
        + len(output["updated"])
        + len(output["flagged"])
        + len(output["skipped"])
    )
    formatter.text("")
    formatter.text(f"Total: {total} tasks processed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    parsed_args = parser.parse_args()
    sys.exit(main(parsed_args))
