"""
Edison session prompts command.

SUMMARY: List available session start prompts
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root

SUMMARY = "List available session start prompts"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--format",
        choices=["id", "filename"],
        default="id",
        help="Output format (default: id)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    try:
        project_root = get_repo_root(args)
        from edison.core.session.start_prompts import list_start_prompts

        prompts = list_start_prompts(project_root)
        if args.format == "filename":
            prompts_out = [f"START_{p}.md" for p in prompts]
        else:
            prompts_out = prompts

        if formatter.json_mode:
            formatter.json_output({"prompts": prompts_out})
        else:
            if not prompts_out:
                formatter.text("No start prompts found.")
            else:
                formatter.text("Start prompts:")
                for p in prompts_out:
                    formatter.text(f"- {p}")
        return 0
    except Exception as e:
        formatter.error(e, error_code="prompts_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))

