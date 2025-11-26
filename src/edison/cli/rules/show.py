"""
Edison rules show command.

SUMMARY: Show rules applicable to a context
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        help="Override repository root path",
    )


def main(args: argparse.Namespace) -> int:
    """Show rules for context - delegates to rules library."""
    from edison.core.rules import RulesRegistry
    from edison.core.utils.paths import resolve_project_root

    try:
        repo_root = Path(args.repo_root) if args.repo_root else resolve_project_root()
        registry = RulesRegistry(repo_root)

        # Load rules
        rules = registry.load_rules()

        # Filter by contexts
        matching = []
        for rule in rules:
            rule_contexts = rule.get("contexts", [])
            if any(ctx in rule_contexts for ctx in args.contexts):
                matching.append(rule)

        if args.json:
            print(json.dumps(matching, indent=2))
        elif args.format == "full":
            for rule in matching:
                print(f"RULE.{rule['id'].upper()}")
                print(f"  Contexts: {', '.join(rule.get('contexts', []))}")
                print(f"  Priority: {rule.get('priority', 'normal')}")
                if rule.get("anchor"):
                    print(f"  Anchor: {rule['anchor']}")
                if rule.get("content"):
                    print(f"  Content:\n    {rule['content'][:200]}...")
                print()
        elif args.format == "markdown":
            for rule in matching:
                print(f"## RULE.{rule['id'].upper()}")
                print(f"**Contexts**: {', '.join(rule.get('contexts', []))}")
                if rule.get("content"):
                    print(f"\n{rule['content']}\n")
        else:
            for rule in matching:
                print(f"RULE.{rule['id'].upper()} [{', '.join(rule.get('contexts', []))}]")

        return 0

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
