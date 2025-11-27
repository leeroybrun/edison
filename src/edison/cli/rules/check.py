"""
Edison rules check command.

SUMMARY: Check rules applicable to a specific context or transition
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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
    """Check rules for context - delegates to RulesEngine."""
    from edison.core.rules import RulesEngine
    from edison.core.config import ConfigManager
    from edison.core.utils.paths import resolve_project_root

    try:
        repo_root = Path(args.repo_root) if args.repo_root else resolve_project_root()
        cfg_mgr = ConfigManager(repo_root)
        config = cfg_mgr.load_config(validate=False)
        engine = RulesEngine(config)

        # Determine what to check
        if not args.context and not args.transition:
            print("Error: Must specify --context or --transition", file=sys.stderr)
            return 1

        # Get applicable rules based on context
        applicable_rules = []
        if args.context:
            for ctx in args.context:
                rules = engine.get_rules_for_context(ctx)
                for rule in rules:
                    rule_dict = {
                        "id": rule.id,
                        "description": rule.description,
                        "blocking": rule.blocking,
                        "enforced": rule.enforced,
                        "contexts": (rule.config or {}).get("contexts", []),
                        "priority": (rule.config or {}).get("priority", "normal"),
                    }
                    if rule_dict not in applicable_rules:
                        applicable_rules.append(rule_dict)

        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "normal": 2, "low": 3}
        applicable_rules.sort(key=lambda r: priority_order.get(r.get("priority", "normal"), 2))

        if args.json:
            print(json.dumps({
                "rules": applicable_rules,
                "count": len(applicable_rules),
                "check_params": check_params,
            }, indent=2))
        elif args.format == "full":
            print(f"Applicable rules ({len(applicable_rules)}):")
            print()
            for rule in applicable_rules:
                print(f"RULE.{rule['id'].upper()}")
                print(f"  Priority: {rule.get('priority', 'normal')}")
                print(f"  Contexts: {', '.join(rule.get('contexts', []))}")
                if rule.get("content"):
                    print(f"  Content:\n    {rule['content'][:300]}...")
                print()
        elif args.format == "markdown":
            print("# Applicable Rules")
            print()
            for rule in applicable_rules:
                print(f"## RULE.{rule['id'].upper()}")
                print(f"**Priority**: {rule.get('priority', 'normal')}")
                print(f"**Contexts**: {', '.join(rule.get('contexts', []))}")
                if rule.get("content"):
                    print(f"\n{rule['content']}\n")
                print("---")
                print()
        else:  # short format
            if applicable_rules:
                print(f"Applicable rules ({len(applicable_rules)}):")
                for rule in applicable_rules:
                    priority = rule.get('priority', 'normal')
                    priority_marker = "🔴" if priority == "critical" else "🟡" if priority == "high" else "⚪"
                    print(f"  {priority_marker} RULE.{rule['id'].upper()}")
            else:
                print("No applicable rules found.")

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
