"""
Edison rules show command.

SUMMARY: Show rules applicable to a context
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root

SUMMARY = "Show rules applicable to a context"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "contexts",
        nargs="+",
        help="Rule contexts to filter by (e.g., delegation, guidance, transition)",
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
    """Show rules for context - delegates to rules library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    from edison.core.rules import RulesRegistry
    
    try:
        repo_root = get_repo_root(args)
        registry = RulesRegistry(repo_root)

        # Load rules
        rules = registry.load_composed_rules()

        # Filter by contexts
        matching = []
        for rule in rules:
            rule_contexts = rule.get("contexts", [])
            if any(ctx in rule_contexts for ctx in args.contexts):
                matching.append(rule)

        if args.json:
            formatter.json_output(matching)
        elif args.format == "full":
            for rule in matching:
                formatter.text(f"RULE.{rule['id'].upper()}")
                formatter.text(f"  Contexts: {', '.join(rule.get('contexts', []))}")
                formatter.text(f"  Priority: {rule.get('priority', 'normal')}")
                if rule.get("anchor"):
                    formatter.text(f"  Anchor: {rule['anchor']}")
                if rule.get("content"):
                    formatter.text(f"  Content:\n    {rule['content'][:200]}...")
                formatter.text("")
        elif args.format == "markdown":
            for rule in matching:
                formatter.text(f"## RULE.{rule['id'].upper()}")
                formatter.text(f"**Contexts**: {', '.join(rule.get('contexts', []))}")
                if rule.get("content"):
                    formatter.text(f"\n{rule['content']}\n")
        else:
            for rule in matching:
                formatter.text(f"RULE.{rule['id'].upper()} [{', '.join(rule.get('contexts', []))}]")

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
