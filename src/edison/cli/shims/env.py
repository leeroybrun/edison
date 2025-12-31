"""
Edison shims env command.

SUMMARY: Print shell snippet to enable Edison shims in the current process
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root
from edison.core.shims import ShimService

SUMMARY = "Print shell snippet to enable Edison shims"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--shell",
        default="sh",
        help="Shell flavor for output (sh|bash|zsh|fish). Default: sh",
    )
    parser.add_argument(
        "--no-sync",
        action="store_true",
        help="Do not sync/generate shims before printing snippet",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    repo_root = get_repo_root(args)
    svc = ShimService(project_root=repo_root)

    snippet = svc.env_snippet(shell=str(args.shell), context="shell", sync=not bool(args.no_sync))

    if formatter.json_mode:
        formatter.json_output(
            {
                "shell": str(args.shell),
                "outputDir": str(svc.output_dir()),
                "snippet": snippet,
            }
        )
        return 0

    # For LLMs/operators, keep it eval-able.
    formatter.text(snippet.rstrip())
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    sys.exit(main(parser.parse_args()))

