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

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root
from edison.cli._utils import resolve_existing_task_id

SUMMARY = "Manage Context7 marker files"


def register_args(parser: argparse.ArgumentParser) -> None:
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    template_parser = subparsers.add_parser("template", help="Print a marker template for a package")
    template_parser.add_argument("package", help="Package name (e.g., fastapi)")
    add_json_flag(template_parser)
    add_repo_root_flag(template_parser)

    save_parser = subparsers.add_parser("save", help="Save a Context7 marker into the task evidence round")
    save_parser.add_argument("task_id", help="Task identifier")
    save_parser.add_argument("package", help="Package name (e.g., fastapi)")
    save_parser.add_argument("--library-id", dest="library_id", required=True, help="Context7 library ID (e.g. /tiangolo/fastapi)")
    save_parser.add_argument("--topics", required=True, help="Comma-separated list of topics queried")
    save_parser.add_argument("--round", type=int, dest="round_num", help="Explicit round number (default: latest)")
    add_json_flag(save_parser)
    add_repo_root_flag(save_parser)

    list_parser = subparsers.add_parser("list", help="List Context7 markers for a task")
    list_parser.add_argument("task_id", help="Task identifier")
    list_parser.add_argument("--round", type=int, dest="round_num", help="Explicit round number (default: latest)")
    add_json_flag(list_parser)
    add_repo_root_flag(list_parser)


def _marker_frontmatter(*, package: str, library_id: str, topics: list[str]) -> str:
    from edison.core.utils.text.frontmatter import format_frontmatter

    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return format_frontmatter(
        {
            "package": package,
            "libraryId": library_id,
            "topics": topics,
            "queriedAt": now,
        }
    )


def _handle_template(args: argparse.Namespace) -> int:
    pkg = str(args.package).strip()
    content = _marker_frontmatter(package=pkg, library_id=f"/<org>/{pkg}", topics=["topic1", "topic2"])
    sys.stdout.write(content)
    return 0


def _handle_save(args: argparse.Namespace, formatter: OutputFormatter, project_root: Path) -> int:
    raw_task_id = str(args.task_id)
    task_id = resolve_existing_task_id(project_root=project_root, raw_task_id=raw_task_id)
    package = str(args.package).strip()
    library_id = str(args.library_id).strip()
    topics = [t.strip() for t in str(args.topics).split(",") if t.strip()]
    round_num = getattr(args, "round_num", None)

    from edison.core.qa.evidence import EvidenceService, rounds
    from edison.core.qa.context.context7 import classify_marker

    ev = EvidenceService(task_id=task_id, project_root=project_root)
    if round_num is not None:
        rd = ev.get_round_dir(int(round_num))
        if not rd.exists():
            formatter.error(RuntimeError(f"Round {round_num} does not exist"), error_code="round_not_found")
            return 1
    else:
        rd = ev.get_current_round_dir()
        if rd is None:
            formatter.error(
                RuntimeError(f"No QA round exists. Run `edison qa round prepare {task_id}` first."),
                error_code="no_round",
            )
            return 1
        round_num = rounds.get_round_number(rd)

    marker_path = rd / f"context7-{package}.txt"
    marker_path.write_text(_marker_frontmatter(package=package, library_id=library_id, topics=topics), encoding="utf-8")

    # Validate after write (fail-closed if invalid)
    classification = classify_marker(rd, package)
    if classification.get("status") != "valid":
        missing_fields = classification.get("missing_fields") or []
        formatter.error(
            RuntimeError(f"Context7 marker written but invalid (missing: {', '.join(missing_fields)})"),
            error_code="context7_invalid_marker",
        )
        return 1

    payload = {"taskId": task_id, "package": package, "path": str(marker_path), "round": int(round_num or 1)}
    formatter.json_output(payload) if formatter.json_mode else formatter.text(f"Saved Context7 marker: {marker_path}")
    return 0


def _handle_list(args: argparse.Namespace, formatter: OutputFormatter, project_root: Path) -> int:
    raw_task_id = str(args.task_id)
    task_id = resolve_existing_task_id(project_root=project_root, raw_task_id=raw_task_id)
    round_num = getattr(args, "round_num", None)

    from edison.core.qa.evidence import EvidenceService, rounds
    from edison.core.qa.context.context7 import _parse_marker_frontmatter  # type: ignore

    ev = EvidenceService(task_id=task_id, project_root=project_root)
    if round_num is not None:
        rd = ev.get_round_dir(int(round_num))
        if not rd.exists():
            formatter.error(RuntimeError(f"Round {round_num} does not exist"), error_code="round_not_found")
            return 1
    else:
        rd = ev.get_current_round_dir()
        if rd is None:
            formatter.error(
                RuntimeError(f"No QA round exists. Run `edison qa round prepare {task_id}` first."),
                error_code="no_round",
            )
            return 1
        round_num = rounds.get_round_number(rd)

    markers: list[dict[str, Any]] = []
    for p in sorted(rd.glob("context7-*.txt")):
        try:
            fm = _parse_marker_frontmatter(p.read_text(encoding="utf-8"))  # type: ignore[arg-type]
        except Exception:
            fm = {}
        if fm:
            markers.append(fm)

    payload = {"taskId": task_id, "round": int(round_num or 1), "markers": markers}
    if formatter.json_mode:
        formatter.json_output(payload)
    else:
        if not markers:
            formatter.text(f"No Context7 markers in round-{round_num}")
        else:
            formatter.text(f"Context7 markers in round-{round_num}:")
            for m in markers:
                formatter.text(f"  - {m.get('package','unknown')}: {m.get('libraryId','')}")
    return 0


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    try:
        subcommand = getattr(args, "subcommand", None)
        project_root = get_repo_root(args)

        if subcommand == "template":
            return _handle_template(args)
        if subcommand == "save":
            return _handle_save(args, formatter, project_root)
        if subcommand == "list":
            return _handle_list(args, formatter, project_root)

        formatter.error(ValueError(f"Unknown subcommand: {subcommand}"), error_code="unknown_subcommand")
        return 1
    except Exception as e:
        formatter.error(e, error_code="context7_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
