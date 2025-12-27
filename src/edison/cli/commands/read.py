"""
Edison read command.

SUMMARY: Read a composed artifact under `.edison/_generated/`
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root

SUMMARY = "Read a composed artifact under `.edison/_generated/`"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "name",
        type=str,
        help="File name (without extension is OK; defaults to .md), e.g. START_NEW_SESSION",
    )
    parser.add_argument(
        "--type",
        type=str,
        default="",
        help="Generated subfolder (e.g., start, guidelines, agents). Empty means _generated root.",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    try:
        repo_root = get_repo_root(args)
        from edison.core.generated.files import resolve_generated_file_path

        path = resolve_generated_file_path(repo_root, type=str(args.type or ""), name=str(args.name))
        content = path.read_text(encoding="utf-8", errors="strict")

        if formatter.json_mode:
            formatter.json_output({"path": str(path), "content": content})
        else:
            formatter.text(content)
        return 0
    except Exception as e:
        formatter.error(e, error_code="read_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))

