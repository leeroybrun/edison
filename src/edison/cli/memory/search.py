"""
Edison memory search command.

SUMMARY: Search optional long-term memory providers (episodic / KG)
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root

SUMMARY = "Search optional long-term memory providers (episodic / KG)"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("query", help="Search query")
    parser.add_argument("--limit", type=int, default=0, help="Max hits (0 = config default)")
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        project_root = get_repo_root(args)
        from edison.core.memory import MemoryManager

        mgr = MemoryManager(project_root=project_root)
        limit = None if int(getattr(args, "limit", 0) or 0) == 0 else int(args.limit)
        hits = mgr.search(str(args.query), limit=limit)
        payload = {"hits": [h.to_dict() for h in hits], "count": len(hits)}
        formatter.json_output(payload) if formatter.json_mode else formatter.text(
            "\n".join(h.get("text", "") for h in payload["hits"]) if payload["hits"] else "No hits."
        )
        return 0
    except Exception as exc:
        formatter.error(exc, error_code="memory_search_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))

