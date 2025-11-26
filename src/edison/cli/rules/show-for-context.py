"""
Edison rules show-for-context command.

SUMMARY: Show rules applicable to specific contexts
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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
    parser.add_argument(
        "--repo-root",
        type=str,
        help="Override repository root path",
    )


def main(args: argparse.Namespace) -> int:
    """Show rules for given contexts."""
    from edison.core.rules import RulesRegistry
    from edison.core.paths import PathResolver

    try:
        repo_root = Path(args.repo_root) if args.repo_root else PathResolver.resolve_project_root()
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
            print(json.dumps(matching, indent=2))
        elif args.format == "full":
            print(f"Applicable Rules for {' '.join(args.contexts)}\n")
            for rule in matching:
                print(f"RULE: {rule['id']}")
                print(f"  Title: {rule.get('title', 'N/A')}")
                print(f"  Category: {rule.get('category', 'N/A')}")
                print(f"  Guidance: {rule.get('guidance', 'N/A')}")
                print(f"  Blocking: {rule.get('blocking', False)}")
                if rule.get("content"):
                    print(f"  Content: {rule['content'][:200]}...")
                print()
        elif args.format == "markdown":
            print(f"# Applicable Rules for {' '.join(args.contexts)}\n")
            for rule in matching:
                print(f"## {rule['id']}")
                print(f"\n**Title**: {rule.get('title', 'N/A')}")
                print(f"**Category**: {rule.get('category', 'N/A')}")
                print(f"**Guidance**: {rule.get('guidance', 'N/A')}\n")
                print(rule.get("content", ""))
                print()
        else:
            print(f"Applicable Rules for {' '.join(args.contexts)}\n")
            for rule in matching:
                print(f"  {rule['id']}")
                print(f"    {rule.get('title', 'N/A')}")

        return 0

    except Exception as e:
        if args.format == "json":
            print(json.dumps({"error": str(e)}))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
