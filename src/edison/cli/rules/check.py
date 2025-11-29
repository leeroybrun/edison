"""
Edison rules check command.

SUMMARY: Check rules applicable to a specific context or transition
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root

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

    from edison.core.rules import RulesEngine
    from edison.core.config import ConfigManager
    
    try:
        repo_root = get_repo_root(args)
        cfg_mgr = ConfigManager(repo_root)
        config = cfg_mgr.load_config(validate=False)
        engine = RulesEngine(config)

        # Determine what to check
        if not args.context and not args.transition:
            formatter.error("Must specify --context or --transition", error_code="error")
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
            formatter.json_output({
                "rules": applicable_rules,
                "count": len(applicable_rules),
            })
        elif args.format == "full":
            formatter.text(f"Applicable rules ({len(applicable_rules)}):")
            formatter.text("")
            for rule in applicable_rules:
                formatter.text(f"RULE.{rule['id'].upper()}")
                formatter.text(f"  Priority: {rule.get('priority', 'normal')}")
                formatter.text(f"  Contexts: {', '.join(rule.get('contexts', []))}")
                if rule.get("content"):
                    formatter.text(f"  Content:\n    {rule['content'][:300]}...")
                formatter.text("")
        elif args.format == "markdown":
            formatter.text("# Applicable Rules")
            formatter.text("")
            for rule in applicable_rules:
                formatter.text(f"## RULE.{rule['id'].upper()}")
                formatter.text(f"**Priority**: {rule.get('priority', 'normal')}")
                formatter.text(f"**Contexts**: {', '.join(rule.get('contexts', []))}")
                if rule.get("content"):
                    formatter.text(f"\n{rule['content']}\n")
                formatter.text("---")
                formatter.text("")
        else:  # short format
            if applicable_rules:
                formatter.text(f"Applicable rules ({len(applicable_rules)}):")
                for rule in applicable_rules:
                    priority = rule.get('priority', 'normal')
                    priority_marker = "🔴" if priority == "critical" else "🟡" if priority == "high" else "⚪"
                    formatter.text(f"  {priority_marker} RULE.{rule['id'].upper()}")
            else:
                formatter.text("No applicable rules found.")

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
