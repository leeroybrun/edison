"""
Edison evidence context7 command.

SUMMARY: Manage Context7 marker files for evidence
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root

SUMMARY = "Manage Context7 marker files"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command arguments."""
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # template subcommand
    template_parser = subparsers.add_parser(
        "template",
        help="Output YAML template for a Context7 marker file",
    )
    template_parser.add_argument(
        "package",
        help="Package name (e.g., fastapi, pytest)",
    )
    add_json_flag(template_parser)
    add_repo_root_flag(template_parser)

    # save subcommand
    save_parser = subparsers.add_parser(
        "save",
        help="Save a Context7 marker file to evidence directory",
    )
    save_parser.add_argument(
        "task_id",
        help="Task identifier (e.g., test-task-123)",
    )
    save_parser.add_argument(
        "package",
        help="Package name (e.g., fastapi, pytest)",
    )
    save_parser.add_argument(
        "--library-id",
        dest="library_id",
        help="Context7 library ID (e.g., /tiangolo/fastapi)",
    )
    save_parser.add_argument(
        "--topics",
        help="Comma-separated list of topics queried",
    )
    save_parser.add_argument(
        "--round",
        type=int,
        dest="round_num",
        help="Explicit round number (default: latest)",
    )
    add_json_flag(save_parser)
    add_repo_root_flag(save_parser)

    # list subcommand
    list_parser = subparsers.add_parser(
        "list",
        help="List saved Context7 markers for a task",
    )
    list_parser.add_argument(
        "task_id",
        help="Task identifier (e.g., test-task-123)",
    )
    list_parser.add_argument(
        "--round",
        type=int,
        dest="round_num",
        help="Explicit round number (default: latest)",
    )
    add_json_flag(list_parser)
    add_repo_root_flag(list_parser)


def _handle_template(args: argparse.Namespace, formatter: OutputFormatter) -> int:
    """Handle the template subcommand."""
    package = str(args.package)
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    template = {
        "package": package,
        "libraryId": f"/<org>/{package}",
        "topics": ["topic1", "topic2"],
        "queriedAt": now,
    }

    yaml_content = yaml.safe_dump(
        template,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
    print(yaml_content, end="")
    return 0


def _handle_save(
    args: argparse.Namespace,
    formatter: OutputFormatter,
    project_root: Path,
) -> int:
    """Handle the save subcommand."""
    task_id = str(args.task_id)
    package = str(args.package)
    library_id = getattr(args, "library_id", None)
    topics_str = getattr(args, "topics", None)
    round_num = getattr(args, "round_num", None)

    # Validate required fields
    if not library_id:
        formatter.error(
            ValueError("--library-id is required"),
            error_code="missing_library_id",
        )
        return 1

    # Parse topics
    topics = [t.strip() for t in topics_str.split(",")] if topics_str else []

    # Get evidence service and round directory
    from edison.core.qa.evidence import EvidenceService

    service = EvidenceService(task_id=task_id, project_root=project_root)

    if round_num is not None:
        round_dir = service.get_round_dir(round_num)
        if not round_dir.exists():
            formatter.error(
                RuntimeError(f"Round {round_num} does not exist"),
                error_code="round_not_found",
            )
            return 1
    else:
        round_dir = service.get_current_round_dir()
        if round_dir is None:
            formatter.error(
                RuntimeError("No evidence round exists. Run 'evidence init' first."),
                error_code="no_round",
            )
            return 1
        from edison.core.qa.evidence import rounds
        round_num = rounds.get_round_number(round_dir)

    # Build marker content
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    frontmatter = {
        "package": package,
        "libraryId": library_id,
        "topics": topics,
        "queriedAt": now,
    }

    yaml_content = yaml.safe_dump(
        frontmatter,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
    content = f"---\n{yaml_content}---\n"

    # Write marker file
    marker_path = round_dir / f"context7-{package}.txt"
    marker_path.write_text(content, encoding="utf-8")

    if formatter.json_mode:
        formatter.json_output({
            "path": str(marker_path),
            "package": package,
            "libraryId": library_id,
            "topics": topics,
            "round": round_num,
        })
    else:
        formatter.text(f"Saved Context7 marker: {marker_path}")

    return 0


def _handle_list(
    args: argparse.Namespace,
    formatter: OutputFormatter,
    project_root: Path,
) -> int:
    """Handle the list subcommand."""
    task_id = str(args.task_id)
    round_num = getattr(args, "round_num", None)

    # Get evidence service and round directory
    from edison.core.qa.evidence import EvidenceService

    service = EvidenceService(task_id=task_id, project_root=project_root)

    if round_num is not None:
        round_dir = service.get_round_dir(round_num)
        if not round_dir.exists():
            formatter.error(
                RuntimeError(f"Round {round_num} does not exist"),
                error_code="round_not_found",
            )
            return 1
    else:
        round_dir = service.get_current_round_dir()
        if round_dir is None:
            formatter.error(
                RuntimeError("No evidence round exists. Run 'evidence init' first."),
                error_code="no_round",
            )
            return 1
        from edison.core.qa.evidence import rounds
        round_num = rounds.get_round_number(round_dir)

    # Find all context7 marker files
    markers: list[dict[str, Any]] = []
    for marker_path in round_dir.glob("context7-*.txt"):
        content = marker_path.read_text(encoding="utf-8")
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 2:
                frontmatter = yaml.safe_load(parts[1])
                if frontmatter:
                    markers.append(frontmatter)

    if formatter.json_mode:
        formatter.json_output({
            "taskId": task_id,
            "round": round_num,
            "markers": markers,
        })
    else:
        if markers:
            formatter.text(f"Context7 markers in round {round_num}:")
            for marker in markers:
                package = marker.get("package", "unknown")
                library_id = marker.get("libraryId", "")
                topics = marker.get("topics", [])
                formatter.text(f"  - {package}: {library_id} ({', '.join(topics)})")
        else:
            formatter.text(f"No Context7 markers in round {round_num}")

    return 0


def main(args: argparse.Namespace) -> int:
    """Manage Context7 marker files."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    try:
        subcommand = getattr(args, "subcommand", None)
        project_root = get_repo_root(args)

        if subcommand == "template":
            return _handle_template(args, formatter)
        elif subcommand == "save":
            return _handle_save(args, formatter, project_root)
        elif subcommand == "list":
            return _handle_list(args, formatter, project_root)
        else:
            formatter.error(
                ValueError(f"Unknown subcommand: {subcommand}"),
                error_code="unknown_subcommand",
            )
            return 1

    except Exception as e:
        formatter.error(e, error_code="context7_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
