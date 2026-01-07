"""
Edison rules inject command.

SUMMARY: Get applicable rules with rendered injection text for clients

This command provides a stable API for clients (Claude hooks, OpenCode plugin)
to get applicable Edison rules and a rendered injection block. Edison remains
the source of truth for rule selection and wording.

Output shape (JSON mode):
{
    "sessionId": "...",
    "taskId": "...",
    "contexts": ["..."],
    "rules": [{"id": "...", "title": "...", "content": "...", "priority": "..."}],
    "injection": "## Edison Rules ..."
}
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from edison.cli import OutputFormatter, add_repo_root_flag, get_repo_root
from edison.core.config import ConfigManager
from edison.core.rules import RulesEngine
from edison.core.utils.profiling import span

SUMMARY = "Get applicable rules with rendered injection text for clients"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--session-id",
        type=str,
        help="Session ID for context (auto-detected if not provided)",
    )
    parser.add_argument(
        "--task-id",
        type=str,
        help="Task ID for context-aware rule filtering",
    )
    parser.add_argument(
        "--context",
        type=str,
        action="append",
        help="Rule context to include (can be specified multiple times)",
    )
    parser.add_argument(
        "--transition",
        type=str,
        help="State transition to check (e.g., 'wip->done', 'todo->wip')",
    )
    parser.add_argument(
        "--state",
        type=str,
        help="Current task state (auto-maps to expected transition: wip->done, done->validated)",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (markdown injection text or json payload).",
    )
    add_repo_root_flag(parser)


# Centralized state-to-transition mapping (single source of truth)
STATE_TO_TRANSITION: dict[str, str] = {
    "wip": "wip->done",
    "done": "done->validated",
}


def _state_to_transition(state: str) -> str | None:
    """Map current task state to the expected transition.

    This is the single source of truth for state-to-transition mapping.
    Clients (hooks, plugins) should use --state instead of hardcoding this logic.
    """
    return STATE_TO_TRANSITION.get(state)


def _render_injection(rules: list[dict[str, Any]]) -> str:
    """Render rules into markdown injection block.

    Args:
        rules: List of rule dicts with id, title, content, priority

    Returns:
        Markdown string for injection, empty if no rules
    """
    if not rules:
        return ""

    lines: list[str] = []
    lines.append("## Edison Rules")
    lines.append("")

    for rule in rules:
        rule_id = rule.get("id", "")
        title = rule.get("title", rule_id)
        content = rule.get("content", "")
        priority = rule.get("priority", "normal")

        # Include rule header
        lines.append(f"### {rule_id}")
        if title and title != rule_id:
            lines.append(f"**{title}** (priority: {priority})")
        else:
            lines.append(f"Priority: {priority}")
        lines.append("")

        # Include content (truncated for injection)
        if content:
            # Limit content to reasonable injection size
            content_str = content.strip()
            if len(content_str) > 1000:
                content_str = content_str[:997] + "..."
            lines.extend(content_str.splitlines())
            lines.append("")

    return "\n".join(lines).rstrip()


def _get_rules_for_inject(
    engine: RulesEngine,
    repo_root: Path,
    contexts: list[str] | None = None,
    transition: str | None = None,
) -> list[dict[str, Any]]:
    """Get rules for injection.

    Args:
        engine: RulesEngine instance
        repo_root: Repository root used to resolve workflow transition rules
        contexts: List of contexts to filter by
        transition: State transition (e.g., 'wip->done')

    Returns:
        List of rule dicts with id, title, content, priority
    """
    rules_out: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    # Transition-based rules (from WorkflowConfig, not RulesEngine)
    if transition:
        from_state, sep, to_state = str(transition).partition("->")
        if sep and from_state.strip() and to_state.strip():
            from edison.core.config.domains.workflow import WorkflowConfig
            workflow_cfg = WorkflowConfig(repo_root=repo_root)
            rule_ids = workflow_cfg.get_transition_rules(
                "task", from_state.strip(), to_state.strip()
            ) or []
            # Look up rule content from engine's rules_map directly
            for rid in rule_ids:
                if rid and rid not in seen_ids:
                    entry = engine.get_rule(rid)
                    if entry:
                        seen_ids.add(rid)
                        rules_out.append({
                            "id": rid,
                            "title": entry.get("title", rid),
                            "content": entry.get("body", ""),
                            "priority": "normal",  # workflow rules don't have priority
                        })

    # Context-based rules
    if contexts:
        for ctx in contexts:
            ctx_rules = engine.get_rules_for_context(ctx)
            for rule in ctx_rules:
                rid = rule.id
                if rid and rid not in seen_ids:
                    seen_ids.add(rid)
                    rules_out.append({
                        "id": rid,
                        "title": rule.description or rid,
                        "content": rule.content or "",
                        "priority": (rule.config or {}).get("priority", "normal"),
                    })

    return rules_out


def main(args: argparse.Namespace) -> int:
    """Get applicable rules with rendered injection text."""
    json_mode = getattr(args, "format", "markdown") == "json"
    formatter = OutputFormatter(json_mode=json_mode)

    try:
        with span("rules.inject.repo_root"):
            repo_root = get_repo_root(args)

        cfg_mgr = ConfigManager(repo_root)
        with span("rules.inject.config.load"):
            config = cfg_mgr.load_config(validate=False)

        with span("rules.inject.engine.init"):
            engine = RulesEngine(config, repo_root=repo_root)

        # Extract contexts and transition
        contexts = args.context or []
        transition = args.transition

        # If --state provided, auto-map to transition (centralized logic)
        if args.state and not transition:
            transition = _state_to_transition(args.state)

        # Get applicable rules
        with span("rules.inject.get_rules"):
            rules = _get_rules_for_inject(
                engine=engine,
                repo_root=repo_root,
                contexts=contexts,
                transition=transition,
            )

        # Render injection text
        with span("rules.inject.render"):
            injection = _render_injection(rules)

        # Build output payload
        session_id = getattr(args, "session_id", None) or ""
        task_id = getattr(args, "task_id", None) or ""

        payload: dict[str, Any] = {
            "sessionId": session_id,
            "taskId": task_id,
            "contexts": contexts,
            "rules": rules,
            "injection": injection,
        }

        if json_mode:
            formatter.json_output(payload)
        else:
            # Non-JSON mode: just output the injection text
            if injection:
                formatter.text(injection)
            # Empty injection = no output (success, but nothing to inject)

        return 0

    except Exception as e:
        formatter.error(e, error_code="error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
