"""
Edison session prompts command.

SUMMARY: List available START_* prompts for sessions
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root

SUMMARY = "List available START_* prompts for sessions"


def register_args(parser: argparse.ArgumentParser) -> None:
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    try:
        repo_root = get_repo_root(args)
        from edison.core.session.start_prompts import list_start_prompts

        prompts = list_start_prompts(repo_root)
        payload = {"count": len(prompts), "prompts": prompts}
        if formatter.json_mode:
            formatter.json_output(payload)
        else:
            if not prompts:
                formatter.text("No start prompts found.")
            else:
                for p in prompts:
                    formatter.text(p)
        return 0
    except Exception as exc:
        formatter.error(exc, error_code="session_prompts_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    sys.exit(main(parser.parse_args()))

