"""
Edison audit event command.

SUMMARY: Write a structured audit event

Designed for:
- IDE hooks (shell scripts) to record lifecycle events
- External integrations that want to append to Edison audit logs
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from edison.cli import OutputFormatter, add_repo_root_flag
from edison.cli._utils import get_repo_root
from edison.core.audit.logger import audit_event

SUMMARY = "Write a structured audit event"


def _parse_fields(fields: list[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for raw in fields:
        if "=" not in raw:
            out[raw] = True
            continue
        k, v = raw.split("=", 1)
        k = k.strip()
        if not k:
            continue
        out[k] = v
    return out


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("event", help="Event name to write (e.g., hook.compaction)")
    parser.add_argument(
        "--field",
        action="append",
        default=[],
        help="Add a field as key=value (repeatable)",
    )
    parser.add_argument(
        "--payload-json",
        dest="payload_json",
        default=None,
        help="Optional JSON string to merge into the payload",
    )
    parser.add_argument(
        "--stdin-json",
        action="store_true",
        help="Read JSON from stdin and merge into the payload",
    )
    parser.add_argument(
        "--session",
        dest="session_id",
        default=None,
        help="Optional session id (used for scoping when audit invocation is enabled)",
    )
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=False)
    try:
        repo_root = get_repo_root(args)

        payload: Dict[str, Any] = {}
        payload.update(_parse_fields(list(getattr(args, "field", []) or [])))

        if getattr(args, "payload_json", None):
            try:
                extra = json.loads(str(args.payload_json))
                if isinstance(extra, dict):
                    payload.update(extra)
            except Exception as e:
                formatter.text(f"Invalid --payload-json: {e}")
                return 2

        if bool(getattr(args, "stdin_json", False)):
            try:
                stdin_text = sys.stdin.read()
                if stdin_text.strip():
                    extra2 = json.loads(stdin_text)
                    if isinstance(extra2, dict):
                        payload.update(extra2)
            except Exception as e:
                formatter.text(f"Invalid JSON on stdin: {e}")
                return 2

        # Include session_id as an explicit field; the audit context (if any)
        # is managed by the CLI dispatcher.
        if getattr(args, "session_id", None):
            payload.setdefault("session_id", str(args.session_id))

        audit_event(str(args.event), repo_root=Path(repo_root), **payload)
        return 0
    except Exception as e:
        formatter.text(f"Error: {e}")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    sys.exit(main(parser.parse_args()))

