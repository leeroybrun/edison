"""
Edison rules list command.

SUMMARY: List all available rules
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag

SUMMARY = "List all available rules"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--context",
        type=str,
        help="Filter by context (e.g., delegation, guidance, transition)",
    )
    parser.add_argument(
        "--priority",
        choices=["critical", "high", "normal", "low"],
        help="Filter by priority level",
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
    """List rules - delegates to rules library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    from edison.core.rules import RulesRegistry
    
    try:
        repo_root = get_repo_root(args)
        registry = RulesRegistry(repo_root)

        # Load all rules
        rules = registry.load_composed_rules()

        # Apply filters
        if args.context:
            rules = [r for r in rules if args.context in r.get("contexts", [])]

        if args.priority:
            rules = [r for r in rules if r.get("priority") == args.priority]

        if args.json:
            formatter.json_output({
                "rules": rules,
                "count": len(rules),
            })
        elif args.format == "full":
            for rule in rules:
                formatter.text(f"RULE.{rule['id'].upper()}")
                formatter.text(f"  Contexts: {', '.join(rule.get('contexts', []))}")
                formatter.text(f"  Priority: {rule.get('priority', 'normal')}")
                if rule.get("anchor"):
                    formatter.text(f"  Anchor: {rule['anchor']}")
                if rule.get("file"):
                    formatter.text(f"  File: {rule['file']}")
                if rule.get("content"):
                    # Truncate long content
                    content = rule['content'][:200]
                    if len(rule['content']) > 200:
                        content += "..."
                    formatter.text(f"  Content:\n    {content}")
                formatter.text("")
        elif args.format == "markdown":
            formatter.text("# Edison Rules")
            formatter.text("")
            for rule in rules:
                formatter.text(f"## RULE.{rule['id'].upper()}")
                formatter.text(f"**Contexts**: {', '.join(rule.get('contexts', []))}")
                formatter.text(f"**Priority**: {rule.get('priority', 'normal')}")
                if rule.get("content"):
                    formatter.text(f"\n{rule['content']}\n")
                formatter.text("---")
                formatter.text("")
        else:  # short format
            formatter.text(f"Rules ({len(rules)}):")
            for rule in rules:
                contexts = ', '.join(rule.get('contexts', []))
                priority = rule.get('priority', 'normal')
                formatter.text(f"  RULE.{rule['id'].upper()} [{contexts}] (priority: {priority})")

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
