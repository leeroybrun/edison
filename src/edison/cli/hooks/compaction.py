"""CLI entrypoint to trigger compaction hooks."""

from __future__ import annotations

import argparse
from pathlib import Path

from edison.core.hooks import CompactionHook

SUMMARY = "Trigger compaction reminder and log the event"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--role",
        help="Role whose constitution should be re-read",
    )
    parser.add_argument(
        "--source",
        help="Optional source label recorded in the compaction log",
    )
    parser.add_argument(
        "--repo-root",
        help="Project root override (defaults to auto-detected repository root)",
    )


def main(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).expanduser().resolve() if getattr(args, "repo_root", None) else None

    hook = CompactionHook(repo_root=repo_root)
    role = getattr(args, "role", None) or hook.settings.default_role
    source = getattr(args, "source", None) or hook.settings.default_source

    hook.trigger(role=role, source=source)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=SUMMARY)
    register_args(parser)
    cli_args = parser.parse_args()
    raise SystemExit(main(cli_args))
