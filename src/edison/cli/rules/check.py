"""
Edison rules check command.

SUMMARY: Check rules applicable to a specific context or transition
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root
from edison.core.rules import RulesEngine
from edison.core.rules.checker import get_rules_for_context_formatted, format_rules_output
from edison.core.config import ConfigManager
from edison.core.utils.profiling import span

SUMMARY = "Check rules applicable to a specific context or transition"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--context",
        type=str,
        action="append",
        help="Rule context to check (can be specified multiple times)",
    )
    parser.add_argument(
        "--transition",
        type=str,
        help="State transition to check (e.g., 'wip->done', 'todo->wip')",
    )
    parser.add_argument(
        "--task-id",
        type=str,
        help="Task ID for context-aware rule checking",
    )
    parser.add_argument(
        "--format",
        choices=["short", "full", "markdown"],
        default="short",
        help="Output format (default: short)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Check rules for context - delegates to RulesEngine."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))


    try:
        with span("rules.check.repo_root"):
            repo_root = get_repo_root(args)
        cfg_mgr = ConfigManager(repo_root)
        with span("rules.check.config.load"):
            config = cfg_mgr.load_config(validate=False)
        with span("rules.check.engine.init"):
            engine = RulesEngine(config)

        # Determine what to check
        if not args.context and not args.transition:
            formatter.error("Must specify --context or --transition", error_code="error")
            return 1

        # Get formatted rules data from core
        with span("rules.check.evaluate"):
            rules_data = get_rules_for_context_formatted(
                engine=engine,
                contexts=args.context,
                transition=args.transition,
                task_id=args.task_id,
            )

        if args.json:
            formatter.json_output(rules_data)
        else:
            # Use core formatting logic
            with span("rules.check.format", mode=str(args.format)):
                output = format_rules_output(rules_data, format_mode=args.format)
            formatter.text(output)

        return 0

    except Exception as e:
        formatter.error(e, error_code="error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
