"""CLI facade for session-next computation.

This module intentionally keeps argparse and output formatting separate from the
core computation logic in :mod:`edison.core.session.next.compute`.
"""
from __future__ import annotations

import argparse
import os
import sys

from edison.core.session.core.context import SessionContext
from edison.core.session.next.compute import compute_next, _reduce_payload_to_completion_only
from edison.core.session.next.output import format_human_readable
from edison.core.session.next.utils import project_cfg_dir
from edison.core.utils.cli.arguments import parse_common_args
from edison.core.utils.cli.output import output_json
from edison.core.utils.io import read_json as io_read_json

from ..core.id import validate_session_id


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for session-next computation."""
    parser = argparse.ArgumentParser()
    parser.add_argument("session_id")
    parse_common_args(parser)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--scope", choices=["tasks", "qa", "session"])
    parser.add_argument(
        "--completion-only",
        action="store_true",
        help="Return only {sessionId, completion, continuation} (useful for hooks/plugins)",
    )
    args = parser.parse_args(argv)
    session_id = validate_session_id(args.session_id)

    # parse_common_args() exposes --repo-root as `project_root`
    if getattr(args, "project_root", None):
        os.environ["AGENTS_PROJECT_ROOT"] = str(args.project_root)

    if args.limit == 0:
        try:
            manifest = io_read_json(project_cfg_dir() / "manifest.json")
            limit = int(manifest.get("orchestration", {}).get("maxConcurrentAgents", 5))
        except Exception:
            limit = 5
    else:
        limit = args.limit

    with SessionContext.in_session_worktree(session_id):
        payload = compute_next(session_id, args.scope, limit)

    if getattr(args, "completion_only", False):
        payload = _reduce_payload_to_completion_only(payload)

    if args.json:
        print(output_json(payload))
    else:
        print(format_human_readable(payload))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

