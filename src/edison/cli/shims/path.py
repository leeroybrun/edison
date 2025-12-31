"""
Edison shims path command.

SUMMARY: Print the shims output directory path
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root
from edison.core.shims import ShimService

SUMMARY = "Print the shims output directory path"


def register_args(parser: argparse.ArgumentParser) -> None:
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    repo_root = get_repo_root(args)
    svc = ShimService(project_root=repo_root)

    if formatter.json_mode:
        formatter.json_output({"outputDir": str(svc.output_dir())})
        return 0

    formatter.text(str(svc.output_dir()))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    sys.exit(main(parser.parse_args()))

