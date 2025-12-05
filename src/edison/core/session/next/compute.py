#!/usr/bin/env python3
"""Compute deterministic next actions for a session (main computation logic).

This module contains the core compute_next function and CLI facade.
Action building logic is in builders.py, processing logic is in processors.py.

Rule Types:
  1. ENFORCEMENT rules: Linked to state machine transitions in workflow.yaml,
     enforced by guard CLIs (edison tasks ready, edison qa promote, etc.).
     Example: RULE.GUARDS.FAIL_CLOSED, RULE.VALIDATION.FIRST

  2. GUIDANCE rules: Registered in rules/registry.yml but not linked to transitions.
     Shown by session next for orchestration hints to help make proactive decisions.
     Example: RULE.DELEGATION.PRIORITY_CHAIN, RULE.SESSION.NEXT_LOOP_DRIVER

  Both types are valid and intentional. Guidance rules help orchestrators make decisions
  proactively rather than enforcing specific actions via guards.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any

from edison.core.config.domains.workflow import WorkflowConfig
from edison.core.session import lifecycle as session_manager
from edison.core.session._config import get_config
from edison.core.session.core.context import SessionContext
from edison.core.session.core.id import validate_session_id as session_store_validate_session_id
from edison.core.session.next.actions import build_reports_missing
from edison.core.session.next.output import format_human_readable
from edison.core.session.next.processors import (
    add_bundle_actions,
    add_delegation_hints,
    add_evidence_blockers,
    add_followups_plan,
    add_guard_previews,
    add_qa_create_actions,
    add_qa_validation_actions,
    add_qa_waiting_to_todo_actions,
    add_task_promote_done_actions,
    add_task_unblock_actions,
    add_validator_analysis_actions,
    build_rules_engine_summary,
    get_state_mappings,
)
from edison.core.session.next.utils import project_cfg_dir
from edison.core.utils.cli.arguments import parse_common_args
from edison.core.utils.cli.output import output_json
from edison.core.utils.io import read_json as io_read_json

load_session = session_manager.get_session
validate_session_id = session_store_validate_session_id


def compute_next(session_id: str, scope: str | None, limit: int) -> dict[str, Any]:
    """Compute next recommended actions for a session.

    Args:
        session_id: Session identifier
        scope: Optional scope filter (tasks, qa, session)
        limit: Maximum number of actions to return

    Returns:
        Dictionary with actions, blockers, and recommendations
    """
    session = load_session(session_id)
    cfg = get_config()
    workflow_cfg = WorkflowConfig()

    # Get semantic state names from config
    STATES = get_state_mappings(workflow_cfg)

    # state_spec structure expected by rules_for
    state_spec = cfg._state_config
    actions: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    followups_plan: list[dict[str, Any]] = []
    tasks_map: dict[str, Any] = session.get("tasks", {}) or {}

    # Process all action types using processors
    add_qa_validation_actions(actions, tasks_map, STATES, scope, session_id, workflow_cfg, state_spec)
    add_task_unblock_actions(actions, tasks_map, STATES, scope, workflow_cfg)
    add_task_promote_done_actions(actions, session, tasks_map, STATES, scope, state_spec)
    add_qa_create_actions(actions, tasks_map, STATES, scope)
    add_evidence_blockers(blockers, tasks_map, STATES)
    add_qa_waiting_to_todo_actions(actions, tasks_map, STATES, scope, state_spec)
    add_delegation_hints(actions, session, STATES, scope)
    add_followups_plan(followups_plan, session, STATES)
    add_bundle_actions(actions, session, STATES, scope, state_spec)
    add_validator_analysis_actions(actions, session, STATES, scope, session_id, workflow_cfg)

    # Apply limit
    if limit and len(actions) > limit:
        actions = actions[:limit]

    # Build additional context
    reports_missing = build_reports_missing(session)
    rules_engine_summary = build_rules_engine_summary()
    add_guard_previews(actions, session, session_id, STATES, rules_engine_summary)

    return {
        "sessionId": session_id,
        "summary": "Next actions computed",
        "actions": actions,
        "blockers": blockers,
        "reportsMissing": reports_missing,
        "followUpsPlan": followups_plan,
        "rulesEngine": rules_engine_summary,
        "rules": [
            "Use bundle-first validation; keep one QA per task.",
            "All moves must go through guarded CLIs.",
        ],
        "recommendations": [
            "Run 'edison session verify' periodically to detect metadata drift (manual edits)",
            "Context7 enforcement cross-checks task metadata + git diff for accuracy",
        ],
    }


def main() -> None:
    """CLI entry point for compute_next."""
    parser = argparse.ArgumentParser()
    parser.add_argument("session_id")
    parse_common_args(parser)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--scope", choices=["tasks", "qa", "session"])
    args = parser.parse_args()
    session_id = validate_session_id(args.session_id)

    if args.repo_root:
        os.environ["AGENTS_PROJECT_ROOT"] = str(args.repo_root)

    if args.limit == 0:
        try:
            manifest = io_read_json(project_cfg_dir() / "manifest.json")
            limit = int(manifest.get("orchestration", {}).get("maxConcurrentAgents", 5))
        except Exception:
            limit = 5
    else:
        limit = args.limit

    with SessionContext.in_session_worktree(session_id):
        payload = compute_next(session_id, args.scope, limit)

    if args.json:
        print(output_json(payload))
    else:
        print(format_human_readable(payload))


if __name__ == "__main__":
    sys.exit(main())
