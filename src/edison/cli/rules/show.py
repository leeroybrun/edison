"""
Edison rules show command.

SUMMARY: Show rules matching filters (context, category, or guidance)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root
from edison.core.rules import RulesRegistry
from edison.core.rules.checker import format_rules_output

SUMMARY = "Show rules matching filters (context, category, or guidance)"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "filters",
        nargs="*",
        help="Filter values (context types like 'guidance', 'validation', or category names)",
    )
    parser.add_argument(
        "--context",
        "-c",
        action="append",
        dest="contexts",
        help="Filter by context type (e.g., guidance, validation, transition)",
    )
    parser.add_argument(
        "--category",
        "-g",
        action="append",
        dest="categories",
        help="Filter by category (e.g., validation, delegation)",
    )
    parser.add_argument(
        "--format",
        choices=["short", "full", "markdown"],
        default="short",
        help="Output format (default: short)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def _filter_rules(rules: List[Dict[str, Any]], filters: List[str], 
                  contexts: List[str], categories: List[str]) -> List[Dict[str, Any]]:
    """Filter rules by context, category, or general filter.
    
    Args:
        rules: All composed rules
        filters: General filters (match against contexts or category)
        contexts: Explicit context filters
        categories: Explicit category filters
        
    Returns:
        List of matching rules
    """
    if not filters and not contexts and not categories:
        return rules  # No filters = return all
    
    matching = []
    all_context_filters = set(contexts or [])
    all_category_filters = set(categories or [])
    
    # General filters can match either context or category
    for f in (filters or []):
        all_context_filters.add(f)
        all_category_filters.add(f)
    
    for rule in rules:
        rule_contexts = set(rule.get("contexts", []))
        rule_category = rule.get("category", "")
        
        # Match if any context filter matches
        if all_context_filters and rule_contexts & all_context_filters:
            matching.append(rule)
            continue
        
        # Match if category matches
        if all_category_filters and rule_category in all_category_filters:
            matching.append(rule)
            continue
        
        # Also check guidance field (legacy compatibility)
        rule_guidance = rule.get("guidance", "")
        for f in (filters or []):
            if f.lower() in rule_guidance.lower():
                matching.append(rule)
                break
    
    return matching


def main(args: argparse.Namespace) -> int:
    """Show rules matching filters."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)
        registry = RulesRegistry(repo_root)

        # Load rules
        rules = registry.load_composed_rules()

        # Filter by contexts, categories, or general filters
        matching = _filter_rules(
            rules, 
            args.filters,
            args.contexts or [],
            args.categories or []
        )

        if args.json:
            formatter.json_output(matching)
        elif args.format == "full":
            for rule in matching:
                formatter.text(f"RULE: {rule['id']}")
                formatter.text(f"  Title: {rule.get('title', 'N/A')}")
                formatter.text(f"  Category: {rule.get('category', 'N/A')}")
                formatter.text(f"  Contexts: {', '.join(rule.get('contexts', []))}")
                formatter.text(f"  Blocking: {rule.get('blocking', False)}")
                if rule.get("content"):
                    formatter.text(f"  Content: {rule['content'][:200]}...")
                formatter.text("")
        elif args.format == "markdown":
            for rule in matching:
                formatter.text(f"## {rule['id']}")
                formatter.text(f"\n**Title**: {rule.get('title', 'N/A')}")
                formatter.text(f"**Category**: {rule.get('category', 'N/A')}")
                formatter.text(f"**Contexts**: {', '.join(rule.get('contexts', []))}\n")
                formatter.text(rule.get("content", ""))
                formatter.text("")
        else:
            # Short format
            for rule in matching:
                contexts_str = ', '.join(rule.get('contexts', [])) if rule.get('contexts') else ''
                category = rule.get('category', '')
                info = []
                if category:
                    info.append(category)
                if contexts_str:
                    info.append(contexts_str)
                info_str = f" [{', '.join(info)}]" if info else ""
                formatter.text(f"{rule['id']}{info_str}")
                if rule.get('title'):
                    formatter.text(f"  {rule['title']}")

        return 0

    except Exception as e:
        formatter.error(e, error_code="error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
