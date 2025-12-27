"""
Edison list command.

SUMMARY: List composed artifacts under `.edison/_generated/`
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root

SUMMARY = "List composed artifacts under `.edison/_generated/`"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--type",
        type=str,
        default="",
        help="Generated subfolder to list (e.g., start, guidelines/shared, agents). Empty means _generated root.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively list files under the selected type folder.",
    )
    parser.add_argument(
        "--format",
        choices=["relpath", "detail"],
        default="relpath",
        help="Output format (default: relpath).",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    try:
        repo_root = get_repo_root(args)
        from edison.core.generated.files import list_generated_files, list_generated_files_payload

        if str(getattr(args, "format", "relpath")) == "detail":
            rows = list_generated_files_payload(repo_root, type=str(args.type or ""), recursive=bool(args.recursive))
            if formatter.json_mode:
                formatter.json_output({"files": rows})
            else:
                if not rows:
                    formatter.text("No generated files found.")
                else:
                    for r in rows:
                        formatter.text(str(r.get("relpath") or r.get("name") or ""))
            return 0

        files = list_generated_files(repo_root, type=str(args.type or ""), recursive=bool(args.recursive))
        if formatter.json_mode:
            formatter.json_output({"files": [{"relpath": f.relpath, "name": f.name, "path": str(f.path)} for f in files]})
        else:
            if not files:
                formatter.text("No generated files found.")
            else:
                for f in files:
                    formatter.text(f.relpath)
        return 0
    except Exception as e:
        formatter.error(e, error_code="list_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
