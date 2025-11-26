#!/usr/bin/env python3
"""Compute deterministic next actions for a session (main computation logic).

This module contains the core compute_next function and CLI facade.

Rule Types:
  1. ENFORCEMENT rules: Linked to state machine transitions in session-workflow.json,
     enforced by guard CLIs (scripts/tasks/ready, scripts/qa/promote, etc.).
     Example: RULE.GUARDS.FAIL_CLOSED, RULE.VALIDATION.FIRST

  2. GUIDANCE rules: Registered in rules/registry.json but not linked to transitions.
     Shown by session next for orchestration hints to help make proactive decisions.
     Example: RULE.DELEGATION.PRIORITY_CHAIN, RULE.SESSION.NEXT_LOOP_DRIVER

  Both types are valid and intentional. Guidance rules help orchestrators make decisions
  proactively rather than enforcing specific actions via guards.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.utils.cli_arguments import parse_common_args
from edison.core.utils.cli_output import output_json
from edison.core.session._config import get_config
from edison.core.session import manager as session_manager
from edison.core.session import store as session_store
from edison.core.session import graph as session_graph
from edison.core.session.context import SessionContext
from edison.core import task
from edison.core.qa import validator as qa_validator
from edison.core.qa import evidence as qa_evidence
from edison.core.file_io.utils import read_json_safe as io_read_json_safe

from edison.core.session.next.utils import (
    project_cfg_dir,
    slugify,
    similar_tasks,
    extract_wave_and_base_id,
    allocate_child_id,
)
from edison.core.session.next.rules import RULE_IDS, rules_for, expand_rules
from edison.core.session.next.actions import (
    infer_task_status,
    infer_qa_status,
    missing_evidence_blockers,
    read_validator_jsons,
    load_impl_followups,
    load_bundle_followups,
    find_related_in_session,
    build_reports_missing,
)
from edison.core.session.next.output import format_human_readable


load_session = session_manager.get_session
build_validation_bundle = session_graph.build_validation_bundle
normalize_session_id = session_store.normalize_session_id


def compute_next(session_id: str, scope: Optional[str], limit: int) -> Dict[str, Any]:
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
    # state_spec structure expected by rules_for: {"domain": {"transitions": ...}}
    state_spec = cfg._state_config # Accessing internal for now to minimize refactor of rules_for
    actions: List[Dict[str, Any]] = []
    blockers: List[Dict[str, Any]] = []
    followups_plan: List[Dict[str, Any]] = []
    tasks_map: Dict[str, Any] = session.get("tasks", {}) or {}

    # Validation-first: QA in todo with task done → start validators (promote to wip)
    for task_id, task_entry in tasks_map.items():
        t_status = infer_task_status(task_id)
        q_status = infer_qa_status(task_id)
        if q_status == "todo" and t_status == "done" and scope in (None, "qa"):
            rule_ids = rules_for("qa", "todo", "wip", state_spec) or [RULE_IDS["validation_first"]]
            rule_ids = list(rule_ids)
            # Build validator roster for this action (with session ID for git-based detection)
            roster = qa_validator.build_validator_roster(task_id, session_id=session_id)
            actions.append({
                "id": "qa.promote.wip",
                "entity": "qa",
                "recordId": f"{task_id}-qa",
                "cmd": ["scripts/qa/promote", "--task", task_id, "--to", "wip"],
                "rationale": "Validation-first: launch validator wave",
                "ruleRef": {"id": rule_ids[0]},
                "ruleIds": rule_ids,
                "blocking": True,
                "validatorRoster": roster,  # NEW: Complete validator info (git-diff based!)
            })

    # Auto-unblock parents when all children are ready (done or validated)
    for task_id, task_entry in tasks_map.items():
        # Consider only tasks explicitly marked blocked
        if task_entry.get("status") != "blocked":
            continue
        children = task_entry.get("childIds", []) or []
        if not children:
            continue
        # A parent is ready to unblock when every child is done or validated.
        # Prefer the session graph view first (status stored in session["tasks"])
        # and fall back to filesystem inference for backward compatibility.
        def _child_ready(cid: str) -> bool:
            entry = tasks_map.get(cid, {}) or {}
            status = str(entry.get("status") or "").lower()
            if status in {"done", "validated"}:
                return True
            return infer_task_status(cid) in {"done", "validated"}

        all_children_ready = all(_child_ready(cid) for cid in children)
        if all_children_ready and scope in (None, "tasks", "session"):
            actions.append({
                "id": "task.unblock.wip",
                "entity": "task",
                "recordId": task_id,
                "cmd": ["scripts/tasks/status", task_id, "--status", "wip"],
                "rationale": "All child tasks are done/validated; move parent from blocked → wip",
                "ruleRef": {"id": RULE_IDS["fail_closed"]},
                "ruleIds": [RULE_IDS["fail_closed"]],
                "blocking": True,
            })

    # Suggest parent promotion to done when children are ready and evidence is present
    for task_id, task_entry in session.get("tasks", {}).items():
        if task_entry.get("status") != "wip":
            continue
        children = task_entry.get("childIds", []) or []
        if children and not all((tasks_map.get(cid, {}) or {}).get("status") in {"done", "validated"} for cid in children):
            continue
        missing = missing_evidence_blockers(task_id)
        # Only propose if automation evidence exists (i.e., missing list empty)
        if not missing and scope in (None, "tasks", "session"):
            rule_ids = rules_for("task", "wip", "done", state_spec) or [RULE_IDS["fail_closed"]]
            actions.append({
                "id": "task.promote.done",
                "entity": "task",
                "recordId": task_id,
                "cmd": ["scripts/tasks/status", task_id, "--status", "done"],
                "rationale": "Children ready and automation evidence present; promote parent wip → done",
                "ruleRef": {"id": rule_ids[0]},
                "ruleIds": rule_ids,
                "blocking": True,
            })

    # Fix invariants: create missing QA for owned wip tasks (suggestion)
    for task_id, task_entry in tasks_map.items():
        if task_entry.get("status") == "wip" and infer_qa_status(task_id) == "missing" and scope in (None, "qa"):
            actions.append({
                "id": "qa.create",
                "entity": "qa",
                "recordId": f"{task_id}-qa",
                "cmd": ["scripts/qa/new", task_id],
                "rationale": "Pair QA with active task",
                "ruleRef": {"id": RULE_IDS["fail_closed"]},
                "ruleIds": [RULE_IDS["fail_closed"]],
                "blocking": True,
            })

    # Automation/Context7 blockers (evidence files)
    for task_id, task_entry in tasks_map.items():
        if task_entry.get("status") == "wip":
            blockers.extend(missing_evidence_blockers(task_id))

    # waiting->todo when task done
    for task_id, task_entry in tasks_map.items():
        if infer_task_status(task_id) == "done" and infer_qa_status(task_id) == "waiting" and scope in (None, "qa"):
            rule_ids = rules_for("qa", "waiting", "todo", state_spec) or [RULE_IDS["validation_first"]]
            rule_ids = list(rule_ids)
            actions.append({
                "id": "qa.promote.todo",
                "entity": "qa",
                "recordId": f"{task_id}-qa",
                "cmd": ["scripts/qa/promote", "--task", task_id, "--to", "todo"],
                "rationale": "Task done; get QA ready",
                "ruleRef": {"id": rule_ids[0]},
                "ruleIds": rule_ids,
                "blocking": True,
            })

    # Delegation hints for wip tasks (non-mutating suggestions)
    for task_id, task_entry in session.get("tasks", {}).items():
        if task_entry.get("status") == "wip" and scope in (None, "tasks"):
            basic_hint = qa_validator.simple_delegation_hint(
                task_id, rule_id=RULE_IDS["delegation"]
            )
            if basic_hint:
                # Enhance hint with detailed reasoning
                enhanced_hint = qa_validator.enhance_delegation_hint(task_id, basic_hint)
                # Find related tasks for context
                related = find_related_in_session(session_id, task_id)

                actions.append({
                    **basic_hint,
                    "delegationDetails": enhanced_hint,  # NEW: Detailed reasoning
                    "relatedTasks": related,  # NEW: Parent/child/sibling context
                })

    # Follow-ups suggestions (claim vs create-only)
    for task_id, task_entry in session.get("tasks", {}).items():
        t_status = infer_task_status(task_id)
        if t_status not in {"wip", "done"}:
            continue
        impl_fus = load_impl_followups(task_id)
        val_fus = load_bundle_followups(task_id)
        if not impl_fus and not val_fus:
            continue
        # Build suggestions with commands
        fus_cmds: List[Dict[str, Any]] = []
        wave, base = extract_wave_and_base_id(task_id)
        for fu in impl_fus:
            slug = slugify(fu.get("title") or "follow-up")
            next_id = allocate_child_id(base)
            if fu.get("blockingBeforeValidation"):
                cmd = ["scripts/tasks/new", "--id", next_id, "--wave", wave, "--slug", slug, "--parent", task_id, "--session", session_id]
                fus_cmds.append({
                    "kind": "create-link-claim",
                    "title": fu.get("title"),
                    "cmd": cmd,
                    "note": "Blocking follow-up: link to parent and claim into session",
                    "similar": similar_tasks(fu.get("title") or "follow-up"),
                })
            else:
                cmd = ["scripts/tasks/new", "--id", next_id, "--wave", wave, "--slug", slug]
                fus_cmds.append({
                    "kind": "create-only",
                    "title": fu.get("title"),
                    "cmd": cmd,
                    "note": "Non-blocking (implementation): create in tasks/todo without linking",
                    "similar": similar_tasks(fu.get("title") or "follow-up"),
                })
        for fu in val_fus:
            slug = slugify(fu.get("title") or "follow-up")
            next_id = allocate_child_id(base)
            cmd = ["scripts/tasks/new", "--id", next_id, "--wave", wave, "--slug", slug]
            fus_cmds.append({
                "kind": "create-only",
                "title": fu.get("title"),
                "cmd": cmd,
                "note": "Non-blocking (validator): create in tasks/todo without linking",
                "similar": similar_tasks(fu.get("title") or "follow-up"),
            })
        if fus_cmds:
            followups_plan.append({
                "taskId": task_id,
                "suggestions": fus_cmds,
            })

    # Build bundles for roots if children ready
    for task_id, task_entry in session.get("tasks", {}).items():
        if not task_entry.get("parentId"):
            children = task_entry.get("childIds", [])
            if children and all(infer_task_status(cid) in {"done", "validated"} for cid in children) and scope in (None, "qa"):
                rule_id = ( rules_for("qa", "todo", "wip", state_spec) or [RULE_IDS["bundle_first"]] )[0]
                actions.append({
                    "id": "bundle.build",
                    "entity": "qa",
                    "recordId": f"{task_id}-qa",
                    "cmd": ["scripts/qa/bundle", task_id],
                    "rationale": "Bundle related tasks for validation",
                    "ruleRef": {"id": rule_id},
                    "ruleIds": [rule_id],
                    "blocking": True,
                })

    # Analyze validator JSON to propose QA next steps
    for task_id, task_entry in session.get("tasks", {}).items():
        q_status = infer_qa_status(task_id)
        if q_status not in {"wip", "todo"}:
            continue
        v = read_validator_jsons(task_id)
        reports = v.get("reports", [])
        if not reports:
            continue
        # Suggest follow-ups based on reports
        suggestions = []
        for r in reports:
            for s in r.get("suggestedFollowups", []) or []:
                suggestions.append(s)
        # Propose creation commands for suggestions
        for s in suggestions:
            parent_id = s.get("parentId") or task_id
            wave, base = extract_wave_and_base_id(parent_id)
            new_id = allocate_child_id(base)
            slug = s.get("suggestedSlug") or slugify(s.get("title","follow-up"))
            # Build guarded Python tasks/new command
            cmd = ["scripts/tasks/new", "--id", new_id, "--wave", wave, "--slug", slug, "--owner", session["meta"]["sessionId"], "--parent", parent_id, "--session", session_id]
            actions.append({
                "id": "task.create.followup",
                "entity": "task",
                "recordId": new_id,
                "cmd": cmd,
                "rationale": f"Follow-up from {r.get('validatorId','validator')}: {s.get('title')}",
                "ruleRef": {"id": RULE_IDS["validation_first"]},
                "ruleIds": [RULE_IDS["validation_first"]],
                "blocking": bool(s.get("blocking")),
            })
            if s.get("claimNow"):
                actions.append({
                    "id": "task.claim",
                    "entity": "task",
                    "recordId": new_id,
                    "cmd": ["scripts/tasks/claim", new_id, "--session", session_id],
                    "rationale": "Suggestion marked claimNow by validator",
                    "ruleRef": {"id": RULE_IDS["validation_first"]},
                    "ruleIds": [RULE_IDS["validation_first"]],
                    "blocking": False,
                })
            if s.get("blocking"):
                actions.append({
                    "id": "task.block",
                    "entity": "task",
                    "recordId": parent_id,
                    "cmd": ["scripts/tasks/status", parent_id, "--status", "blocked"],
                    "rationale": "Follow-up marked blocking; set parent to blocked",
                    "ruleRef": {"id": RULE_IDS["validation_first"]},
                    "ruleIds": [RULE_IDS["validation_first"]],
                    "blocking": True,
                })
        blocking_failed = [r for r in reports if not r.get("approved")]
        if blocking_failed and scope in (None, "qa"):
            actions.append({
                "id": "qa.round.rejected",
                "entity": "qa",
                "recordId": f"{task_id}-qa",
                "cmd": ["scripts/qa/round", "--task", task_id, "--status", "rejected", "--note", f"validators: {', '.join(r.get('validatorId','?') for r in blocking_failed)}"],
                "rationale": "Blocking validators failed; record Round and return QA to waiting",
                "ruleRef": {"id": RULE_IDS["validation_first"]},
                "ruleIds": [RULE_IDS["validation_first"], RULE_IDS["bundle_first"]],
                "blocking": True,
            })
        elif not blocking_failed and q_status == "wip" and scope in (None, "qa"):
            actions.append({
                "id": "qa.promote.done",
                "entity": "qa",
                "recordId": f"{task_id}-qa",
                "cmd": ["scripts/qa/promote", "--task", task_id, "--to", "done"],
                "rationale": "All blocking validators approved; close QA",
                "ruleRef": {"id": RULE_IDS["validation_first"]},
                "ruleIds": [RULE_IDS["validation_first"]],
                "blocking": True,
            })

    if limit and len(actions) > limit:
        actions = actions[:limit]

    # Build reportsMissing list for visibility
    reports_missing = build_reports_missing(session)

    # Collect all unique rule IDs from actions
    all_rule_ids: List[str] = []
    for a in actions:
        for rid in a.get("ruleIds", []):
            if rid not in all_rule_ids:
                all_rule_ids.append(rid)

    # Always expand rules (no flag needed - default behavior)
    expanded_rules = expand_rules(all_rule_ids)

    # Phase 1B: context-aware rules + guard previews via RulesEngine.
    rules_engine_summary: Dict[str, Any] = {}
    engine = None
    try:
        from edison.core.config import ConfigManager
        from edison.core.rules import RulesEngine
        cfg = ConfigManager().load_config(validate=False)
        engine = RulesEngine(cfg)

        ctx_map = {
            "validation": {"operation": "session/next"},
            "delegation": {"operation": "delegation/plan"},
            "guidance": {"operation": "session/next"},
            "transition": {"operation": "session/next"},
        }
        for ctx_type, meta in ctx_map.items():
            ctx_rules = engine.get_rules_for_context(
                context_type=ctx_type,
                task_state=None,
                changed_files=None,
                operation=meta.get("operation"),
            )
            if ctx_rules:
                rules_engine_summary[ctx_type] = [
                    {
                        "id": r.id,
                        "description": r.description,
                        "blocking": r.blocking,
                    }
                    for r in ctx_rules
                ]
    except Exception:
        rules_engine_summary = {}
        engine = None

    # Guard previews for key task transitions (best-effort; non-fatal).
    if engine is not None:
        for a in actions:
            entity = a.get("entity")
            aid = a.get("id")
            record_id = str(a.get("recordId") or "")
            from_state: Optional[str] = None
            to_state: Optional[str] = None

            if entity == "task" and aid == "task.promote.done":
                from_state, to_state = "wip", "done"
            elif entity == "task" and aid == "task.claim":
                from_state, to_state = "todo", "wip"

            if not from_state or not to_state or not record_id:
                continue

            task_ctx = {"id": record_id}
            sess_ctx: Dict[str, Any] = {"id": session.get("id") or session_id}
            allowed, msg = engine.check_transition_guards(
                from_state, to_state, task_ctx, sess_ctx, validation_results=None
            )
            guard_status = "allowed" if allowed else "blocked"
            guard_obj: Dict[str, Any] = {
                "from": from_state,
                "to": to_state,
                "status": guard_status,
            }
            if msg:
                guard_obj["message"] = msg
            a["guard"] = guard_obj

    return {
        "sessionId": session_id,
        "summary": "Next actions computed",
        "actions": actions,
        "blockers": blockers,
        "reportsMissing": reports_missing,
        "followUpsPlan": followups_plan,
        "rulesExpanded": expanded_rules,  # Always include expanded rules
        "rulesEngine": rules_engine_summary,  # Context-aware rules (git diff + config)
        "rules": [
            "Use bundle-first validation; keep one QA per task.",
            "All moves must go through guarded CLIs.",
        ],
        "recommendations": [
            "Run 'scripts/session verify' periodically to detect metadata drift (manual edits)",
            "Context7 enforcement cross-checks task metadata + git diff for accuracy",
        ],
    }


def main() -> None:  # CLI facade for direct execution
    """CLI entry point for compute_next."""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("session_id")
    parse_common_args(parser)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--scope", choices=["tasks", "qa", "session"])
    args = parser.parse_args()
    session_id = normalize_session_id(args.session_id)

    if args.repo_root:
        os.environ["AGENTS_PROJECT_ROOT"] = str(args.repo_root)

    if args.limit == 0:
        try:
            manifest = io_read_json_safe(project_cfg_dir() / "manifest.json")
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
        # Enhanced human-readable output with rules, validators, delegation details
        print(format_human_readable(payload))


if __name__ == "__main__":
    sys.exit(main())
