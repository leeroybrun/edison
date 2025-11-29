"""
Edison rules show-for-context command.

SUMMARY: Show rules applicable to specific contexts
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_repo_root_flag, get_repo_root
from edison.core.rules import RulesRegistry

SUMMARY = "Show rules applicable to specific contexts"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "contexts",
        nargs="+",
        help="Rule contexts to filter by (e.g., guidance delegation, transition wip→done)",
    )
    parser.add_argument(
        "--format",
        choices=["short", "full", "markdown", "json"],
        default="short",
        help="Output format (default: short)",
    )
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Show rules for given contexts."""
    json_mode = args.format == "json"
    formatter = OutputFormatter(json_mode=json_mode)

    
    try:
        repo_root = get_repo_root(args)
        registry = RulesRegistry(repo_root)

        # Compose all rules that match any of the contexts
        all_rules = registry.load_composed_rules()

        # Build context filter from arguments
        # Support both "guidance delegation" and "guidance:delegation" formats
        context_filters = []
        i = 0
        while i < len(args.contexts):
            if ":" in args.contexts[i]:
                # Single arg with colon separator
                context_filters.append(args.contexts[i])
                i += 1
            elif i + 1 < len(args.contexts):
                # Two separate args - combine them
                context_filters.append(f"{args.contexts[i]}:{args.contexts[i+1]}")
                i += 2
            else:
                # Single arg without match
                context_filters.append(args.contexts[i])
                i += 1

        # Filter rules by context
        matching = []
        for rule in all_rules:
            rule_guidance = rule.get("guidance", "")
            # Check if any context filter matches
            for ctx_filter in context_filters:
                if ":" in ctx_filter:
                    parts = ctx_filter.split(":", 1)
                    # Match if guidance contains all parts
                    if all(part.lower() in rule_guidance.lower() for part in parts):
                        matching.append(rule)
                        break
                else:
                    # Match if guidance contains the filter
                    if ctx_filter.lower() in rule_guidance.lower():
                        matching.append(rule)
                        break

        # Output
        if args.format == "json":
            formatter.json_output(matching)
        elif args.format == "full":
            formatter.text(f"Applicable Rules for {' '.join(args.contexts)}\n")
            for rule in matching:
                formatter.text(f"RULE: {rule['id']}")
                formatter.text(f"  Title: {rule.get('title', 'N/A')}")
                formatter.text(f"  Category: {rule.get('category', 'N/A')}")
                formatter.text(f"  Guidance: {rule.get('guidance', 'N/A')}")
                formatter.text(f"  Blocking: {rule.get('blocking', False)}")
                if rule.get("content"):
                    formatter.text(f"  Content: {rule['content'][:200]}...")
                formatter.text("")
        elif args.format == "markdown":
            formatter.text(f"# Applicable Rules for {' '.join(args.contexts)}\n")
            for rule in matching:
                formatter.text(f"## {rule['id']}")
                formatter.text(f"\n**Title**: {rule.get('title', 'N/A')}")
                formatter.text(f"**Category**: {rule.get('category', 'N/A')}")
                formatter.text(f"**Guidance**: {rule.get('guidance', 'N/A')}\n")
                formatter.text(rule.get("content", ""))
                formatter.text("")
        else:
            formatter.text(f"Applicable Rules for {' '.join(args.contexts)}\n")
            for rule in matching:
                formatter.text(f"  {rule['id']}")
                formatter.text(f"    {rule.get('title', 'N/A')}")

        return 0

    except Exception as e:
        formatter.error(e, error_code="error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
