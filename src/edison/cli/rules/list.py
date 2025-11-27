"""
Edison rules list command.

SUMMARY: List all available rules
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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
    """List rules - delegates to rules library."""
    from edison.core.rules import RulesRegistry
    from edison.core.utils.paths import resolve_project_root

    try:
        repo_root = Path(args.repo_root) if args.repo_root else resolve_project_root()
        registry = RulesRegistry(repo_root)

        # Load all rules
        rules = registry.load_composed_rules()

        # Apply filters
        if args.context:
            rules = [r for r in rules if args.context in r.get("contexts", [])]

        if args.priority:
            rules = [r for r in rules if r.get("priority") == args.priority]

        if args.json:
            print(json.dumps({
                "rules": rules,
                "count": len(rules),
            }, indent=2))
        elif args.format == "full":
            for rule in rules:
                print(f"RULE.{rule['id'].upper()}")
                print(f"  Contexts: {', '.join(rule.get('contexts', []))}")
                print(f"  Priority: {rule.get('priority', 'normal')}")
                if rule.get("anchor"):
                    print(f"  Anchor: {rule['anchor']}")
                if rule.get("file"):
                    print(f"  File: {rule['file']}")
                if rule.get("content"):
                    # Truncate long content
                    content = rule['content'][:200]
                    if len(rule['content']) > 200:
                        content += "..."
                    print(f"  Content:\n    {content}")
                print()
        elif args.format == "markdown":
            print("# Edison Rules")
            print()
            for rule in rules:
                print(f"## RULE.{rule['id'].upper()}")
                print(f"**Contexts**: {', '.join(rule.get('contexts', []))}")
                print(f"**Priority**: {rule.get('priority', 'normal')}")
                if rule.get("content"):
                    print(f"\n{rule['content']}\n")
                print("---")
                print()
        else:  # short format
            print(f"Rules ({len(rules)}):")
            for rule in rules:
                contexts = ', '.join(rule.get('contexts', []))
                priority = rule.get('priority', 'normal')
                print(f"  RULE.{rule['id'].upper()} [{contexts}] (priority: {priority})")

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
