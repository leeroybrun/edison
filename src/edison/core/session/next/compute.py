#!/usr/bin/env python3
"""Compute deterministic next actions for a session (main computation logic).

This module contains the core compute_next function and CLI facade.

Rule Types:
  1. ENFORCEMENT rules: Linked to state machine transitions in workflow.yaml,
     enforced by guard CLIs (edison task done, edison qa promote, etc.).
     Example: RULE.GUARDS.FAIL_CLOSED, RULE.VALIDATION.FIRST

  2. GUIDANCE rules: Registered in rules/registry.yml but not linked to transitions.
     Shown by session next for orchestration hints to help make proactive decisions.
     Example: RULE.DELEGATION.PRIORITY_CHAIN, RULE.SESSION.NEXT_LOOP_DRIVER

  Both types are valid and intentional. Guidance rules help orchestrators make decisions
  proactively rather than enforcing specific actions via guards.
"""
from __future__ import annotations

import os
import sys
from typing import Any

from edison.core.config.domains.workflow import WorkflowConfig
from edison.core.qa.engines import ValidationExecutor
from edison.core.session import lifecycle as session_manager
from edison.core.session._config import get_config
from edison.core.session.core.context import SessionContext
from edison.core.session.core.id import validate_session_id as session_store_validate_session_id
from edison.core.session.delegation import enhance_delegation_hint, simple_delegation_hint
from edison.core.session.next.actions import (
    build_reports_missing,
    find_related_in_session,
    infer_qa_status,
    infer_task_status,
    load_bundle_followups,
    load_impl_followups,
    missing_evidence_blockers,
    read_validator_reports,
)
from edison.core.session.next.output import format_human_readable
from edison.core.session.next.rules import get_rules_for_context, rules_for
from edison.core.session.next.utils import (
    allocate_child_id,
    extract_wave_and_base_id,
    project_cfg_dir,
    slugify,
)
from edison.core.utils.cli.arguments import parse_common_args
from edison.core.utils.cli.output import output_json
from edison.core.utils.io import read_json as io_read_json

load_session = session_manager.get_session
validate_session_id = session_store_validate_session_id


def _format_cmd_template(template: list[str], **kwargs) -> list[str]:
    """Format a command template with runtime values.
    
    Args:
        template: Command template list with placeholders like {task_id}, {session_id}
        **kwargs: Values to substitute into placeholders
        
    Returns:
        Formatted command list with placeholders replaced
    """
    return [part.format(**kwargs) if "{" in part else part for part in template]


def _build_action_from_recommendation(
    rec: dict[str, Any],
    from_state: str,
    to_state: str,
    workflow_cfg: WorkflowConfig,
    state_spec: dict[str, Any],
    **format_kwargs,
) -> dict[str, Any]:
    """Build an action dict from a recommendation config.
    
    Args:
        rec: Recommendation dict from workflow.yaml
        from_state: Source state
        to_state: Target state
        workflow_cfg: WorkflowConfig instance
        state_spec: State spec for rules_for lookup
        **format_kwargs: Values for cmd_template (task_id, session_id, etc.)
        
    Returns:
        Action dict ready for the actions list
    """
    domain = rec.get("entity", "task")
    rule_ids = workflow_cfg.get_transition_rules(domain, from_state, to_state) or []

    # Build record ID based on entity type
    task_id = format_kwargs.get("task_id", "")
    if domain == "qa":
        record_id = f"{task_id}-qa"
    else:
        record_id = task_id

    action = {
        "id": rec.get("id", "unknown"),
        "entity": domain,
        "recordId": record_id,
        "cmd": _format_cmd_template(rec.get("cmd_template", []), **format_kwargs),
        "rationale": rec.get("rationale", ""),
        "blocking": rec.get("blocking", False),
        "ruleIds": rule_ids,
    }

    if rule_ids:
        action["ruleRef"] = {"id": rule_ids[0]}

    return action

# Import build_validation_bundle from graph module (will be migrated)
import argparse


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
    STATES = {
        "task": {
            "todo": workflow_cfg.get_semantic_state("task", "todo"),
            "wip": workflow_cfg.get_semantic_state("task", "wip"),
            "done": workflow_cfg.get_semantic_state("task", "done"),
            "validated": workflow_cfg.get_semantic_state("task", "validated"),
            "blocked": workflow_cfg.get_semantic_state("task", "blocked"),
        },
        "qa": {
            "waiting": workflow_cfg.get_semantic_state("qa", "waiting"),
            "todo": workflow_cfg.get_semantic_state("qa", "todo"),
            "wip": workflow_cfg.get_semantic_state("qa", "wip"),
            "done": workflow_cfg.get_semantic_state("qa", "done"),
            "validated": workflow_cfg.get_semantic_state("qa", "validated"),
        },
    }

    # state_spec structure expected by rules_for: {"domain": {"transitions": ...}}
    state_spec = cfg._state_config # Accessing internal for now to minimize refactor of rules_for
    actions: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    followups_plan: list[dict[str, Any]] = []

    def _should_show_session_start_checklist(session_obj: Any) -> bool:
        try:
            if not isinstance(session_obj, dict):
                return True
            meta = session_obj.get("meta") if isinstance(session_obj.get("meta"), dict) else {}
            if not meta:
                return True

            from edison.core.utils.time import parse_iso8601, utc_now
            from edison.core.utils.paths import PathResolver

            created_raw = str(meta.get("createdAt") or "").strip()
            last_raw = str(meta.get("lastActive") or "").strip()
            if not created_raw or not last_raw:
                return True

            created = parse_iso8601(created_raw, repo_root=PathResolver.resolve_project_root())
            last = parse_iso8601(last_raw, repo_root=PathResolver.resolve_project_root())
            now = utc_now(repo_root=PathResolver.resolve_project_root())

            # New sessions often have lastActive ~= createdAt.
            if abs((last - created).total_seconds()) <= 120:
                return True
            # Resumed/stale sessions: show if session hasn't been active recently.
            if (now - last).total_seconds() >= 3600:
                return True
        except Exception:
            return True
        return False

    # Session start/resume checklist: show at the moment it matters.
    if _should_show_session_start_checklist(session):
        try:
            from pathlib import Path

            from edison.core.workflow.checklists.session_start import SessionStartChecklistEngine
            from edison.core.utils.paths import PathResolver

            checklist = SessionStartChecklistEngine(project_root=PathResolver.resolve_project_root()).compute(
                session_id=session_id,
                cwd=Path(os.getcwd()),
            )
            actions.append(
                {
                    "id": "session.start_checklist",
                    "entity": "session",
                    "recordId": session_id,
                    "cmd": ["edison", "session", "show", session_id],
                    "rationale": "Session start/resume checklist (worktree, delegation gate, prerequisites).",
                    "blocking": bool(checklist.get("hasBlockers", False)),
                    "checklist": checklist,
                }
            )
        except Exception:
            # Fail-open: session next must remain usable even if checklist fails.
            pass
    # Session JSON is NOT the source of truth for tasks/QAs. Tasks are derived from
    # task files (TaskRepository) via session_id linkage.
    from edison.core.task import TaskRepository

    task_repo = TaskRepository()
    session_tasks = task_repo.find_by_session(session_id)
    tasks_map: dict[str, Any] = {
        t.id: {
            "status": t.state,
            "parentId": t.parent_id,
            "childIds": list(t.child_ids or []),
        }
        for t in session_tasks
    }

    # Fail-open UX fallback: if task files are missing/unlinked, fall back to the
    # lightweight `session.tasks` index so `session next` can still guide users.
    if not tasks_map:
        tasks_index = session.get("tasks") if isinstance(session, dict) else None
        if isinstance(tasks_index, dict) and tasks_index:
            for task_id, entry in tasks_index.items():
                if not task_id or not isinstance(task_id, str):
                    continue
                e = entry if isinstance(entry, dict) else {}
                status = e.get("status") or e.get("state") or infer_task_status(task_id)
                tasks_map[task_id] = {
                    "status": status,
                    "parentId": e.get("parentId") if isinstance(e.get("parentId"), str) else None,
                    "childIds": list(e.get("childIds") or []) if isinstance(e.get("childIds"), list) else [],
                }

    # Required-fill reminders: for tasks that declare REQUIRED FILL markers, prompt
    # the orchestrator/LLM to complete them before starting implementation work.
    try:
        from edison.core.artifacts import find_missing_required_sections

        todo_state = STATES["task"]["todo"]
        wip_state = STATES["task"]["wip"]

        for task_id, entry in tasks_map.items():
            status = entry.get("status") if isinstance(entry, dict) else None
            if status not in (todo_state, wip_state):
                continue

            try:
                path = task_repo.get_path(task_id)
                content = path.read_text(encoding="utf-8", errors="strict")
            except Exception:
                continue

            missing = find_missing_required_sections(content)
            if not missing:
                continue

            actions.append(
                {
                    "id": "task.fill_required_sections",
                    "entity": "task",
                    "recordId": task_id,
                    "cmd": ["edison", "task", "show", task_id],
                    "rationale": f"Task is missing required sections: {', '.join(missing)}",
                    "blocking": True,
                    "missingRequiredSections": missing,
                }
            )
    except Exception:
        # Fail-open: session-next must not crash due to required-fill helpers/config.
        pass

    similarity_index = None

    def _similar(title: str) -> list[dict[str, object]]:
        nonlocal similarity_index
        try:
            if similarity_index is None:
                from edison.core.task.similarity import TaskSimilarityIndex
                from edison.core.utils.paths import PathResolver

                similarity_index = TaskSimilarityIndex.build(
                    project_root=PathResolver.resolve_project_root()
                )
            return [m.to_session_next_dict() for m in similarity_index.search(title)]
        except Exception:
            return []

    # Validation-first: QA in todo with task done → start validators (promote to wip)
    for task_id, _task_entry in tasks_map.items():
        t_status = infer_task_status(task_id)
        q_status = infer_qa_status(task_id)
        if q_status == STATES["qa"]["todo"] and t_status == STATES["task"]["done"] and scope in (None, "qa"):
            # Get recommendations from config for this transition
            qa_todo = STATES["qa"]["todo"]
            qa_wip = STATES["qa"]["wip"]
            recommendations = workflow_cfg.get_recommendations("qa", qa_todo, qa_wip)

            # Build validator roster using ValidatorRegistry (single source of truth)
            from edison.core.registries.validators import ValidatorRegistry
            validator_registry = ValidatorRegistry()
            roster = validator_registry.build_execution_roster(task_id, session_id=session_id)

            # Check if any validators can be executed directly using ValidationExecutor
            executor = ValidationExecutor()
            validators_in_roster = (
                roster.get("alwaysRequired", [])
                + roster.get("triggeredBlocking", [])
                + roster.get("triggeredOptional", [])
            )
            can_execute_directly = any(
                executor.can_execute_validator(v["id"])
                for v in validators_in_roster
            )

            if recommendations:
                # Use config-driven recommendations
                for rec in recommendations:
                    action = _build_action_from_recommendation(
                        rec, qa_todo, qa_wip, workflow_cfg, state_spec,
                        task_id=task_id, session_id=session_id
                    )
                    action["validatorRoster"] = roster
                    try:
                        from edison.core.workflow.checklists.qa_validate_preflight import (
                            QAValidatePreflightChecklistEngine,
                        )

                        action["checklist"] = QAValidatePreflightChecklistEngine(
                            project_root=PathResolver.resolve_project_root()
                        ).compute(
                            task_id=task_id,
                            session_id=session_id,
                            roster=roster,
                            round_num=None,
                            new_round=False,
                            will_execute=("--execute" in (action.get("cmd") or [])),
                            check_only=False,
                        )
                    except Exception:
                        pass
                    actions.append(action)
            else:
                # Fallback: generate default action if no recommendations in config
                # Rule IDs come from config (workflow.yaml), not hardcoded
                rule_ids = workflow_cfg.get_transition_rules("qa", qa_todo, qa_wip) or []

                # Recommend direct execution if CLI tools available
                if can_execute_directly:
                    cmd = ["edison", "qa", "validate", task_id, "--session", session_id, "--execute"]
                    rationale = "Direct CLI validation: execute validators and collect results"
                else:
                    cmd = ["edison", "qa", "validate", task_id, "--session", session_id]
                    rationale = "Build validator roster for orchestrator delegation"

                checklist = None
                try:
                    from edison.core.workflow.checklists.qa_validate_preflight import (
                        QAValidatePreflightChecklistEngine,
                    )

                    checklist = QAValidatePreflightChecklistEngine(
                        project_root=PathResolver.resolve_project_root()
                    ).compute(
                        task_id=task_id,
                        session_id=session_id,
                        roster=roster,
                        round_num=None,
                        new_round=False,
                        will_execute=can_execute_directly,
                        check_only=False,
                    )
                except Exception:
                    checklist = None

                action = {
                    "id": "qa.validate",
                    "entity": "qa",
                    "recordId": f"{task_id}-qa",
                    "cmd": cmd,
                    "rationale": rationale,
                    "ruleRef": {"id": rule_ids[0]} if rule_ids else None,
                    "ruleIds": rule_ids,
                    "blocking": True,
                    "validatorRoster": roster,
                    "canExecuteDirectly": can_execute_directly,
                }
                if checklist:
                    action["checklist"] = checklist
                actions.append(action)

    # Auto-unblock parents when all children are ready (done or validated)
    for task_id, task_entry in tasks_map.items():
        # Consider only tasks explicitly marked blocked
        if task_entry.get("status") != STATES["task"]["blocked"]:
            continue
        children = task_entry.get("childIds", []) or []
        if not children:
            continue
        # A parent is ready to unblock when every child is done or validated.
        # Check session graph first (for tasks claimed in this session),
        # then fall back to filesystem (for global tasks not yet claimed).
        ready_states = {STATES["task"]["done"], STATES["task"]["validated"]}
        def _child_ready(cid: str) -> bool:
            entry = tasks_map.get(cid, {}) or {}
            status = str(entry.get("status") or "").lower()
            if status in ready_states:
                return True
            return infer_task_status(cid) in ready_states

        all_children_ready = all(_child_ready(cid) for cid in children)
        if all_children_ready and scope in (None, "tasks", "session"):
            from_state = STATES["task"]["blocked"]
            to_state = STATES["task"]["wip"]
            recommendations = workflow_cfg.get_recommendations("task", from_state, to_state)
            if recommendations:
                for rec in recommendations:
                    action = _build_action_from_recommendation(
                        rec, from_state, to_state, workflow_cfg, state_spec,
                        task_id=task_id, session_id=session_id,
                    )
                    action["rationale"] = "All child tasks are done/validated; move parent from blocked → wip"
                    actions.append(action)
            else:
                unblock_rules = workflow_cfg.get_transition_rules("task", from_state, to_state) or []
                actions.append({
                    "id": "task.unblock.wip",
                    "entity": "task",
                    "recordId": task_id,
                    "cmd": ["edison", "task", "status", task_id, "--status", to_state],
                    "rationale": "All child tasks are done/validated; move parent from blocked → wip",
                    "ruleRef": {"id": unblock_rules[0]} if unblock_rules else None,
                    "ruleIds": unblock_rules,
                    "blocking": True,
                })

    # Suggest parent promotion to done when children are ready and evidence is present
    ready_states_set = {STATES["task"]["done"], STATES["task"]["validated"]}
    for task_id, task_entry in tasks_map.items():
        if task_entry.get("status") != STATES["task"]["wip"]:
            continue
        children = task_entry.get("childIds", []) or []
        if children and not all((tasks_map.get(cid, {}) or {}).get("status") in ready_states_set for cid in children):
            continue
        missing = missing_evidence_blockers(task_id)
        # Only propose if automation evidence exists (i.e., missing list empty)
        if not missing and scope in (None, "tasks", "session"):
            from_state = STATES["task"]["wip"]
            to_state = STATES["task"]["done"]
            recommendations = workflow_cfg.get_recommendations("task", from_state, to_state)
            if recommendations:
                for rec in recommendations:
                    action = _build_action_from_recommendation(
                        rec, from_state, to_state, workflow_cfg, state_spec,
                        task_id=task_id, session_id=session_id,
                    )
                    action["rationale"] = "Children ready and automation evidence present; promote parent wip → done"
                    actions.append(action)
            else:
                rule_ids = rules_for("task", from_state, to_state, state_spec) or []
                actions.append({
                    "id": "task.promote.done",
                    "entity": "task",
                    "recordId": task_id,
                    "cmd": ["edison", "task", "status", task_id, "--status", to_state],
                    "rationale": "Children ready and automation evidence present; promote parent wip → done",
                    "ruleRef": {"id": rule_ids[0]} if rule_ids else None,
                    "ruleIds": list(rule_ids),
                    "blocking": True,
                })

    # Fix invariants: create missing QA for owned wip tasks (suggestion)
    # Note: QA creation is not a state transition, so no transition rules apply
    for task_id, task_entry in tasks_map.items():
        if task_entry.get("status") == STATES["task"]["wip"] and infer_qa_status(task_id) == "missing" and scope in (None, "qa"):
            actions.append({
                "id": "qa.create",
                "entity": "qa",
                "recordId": f"{task_id}-qa",
                "cmd": ["edison", "qa", "new", task_id],
                "rationale": "Pair QA with active task",
                "ruleRef": None,  # Not a transition - no transition rules
                "ruleIds": [],
                "blocking": True,
            })

    # Automation/Context7 blockers (evidence files)
    for task_id, task_entry in tasks_map.items():
        if task_entry.get("status") == STATES["task"]["wip"]:
            blockers.extend(missing_evidence_blockers(task_id))

    # waiting->todo when task done
    for task_id, task_entry in tasks_map.items():
        if infer_task_status(task_id) == STATES["task"]["done"] and infer_qa_status(task_id) == STATES["qa"]["waiting"] and scope in (None, "qa"):
            from_state = STATES["qa"]["waiting"]
            to_state = STATES["qa"]["todo"]
            recommendations = workflow_cfg.get_recommendations("qa", from_state, to_state)
            if recommendations:
                for rec in recommendations:
                    action = _build_action_from_recommendation(
                        rec, from_state, to_state, workflow_cfg, state_spec,
                        task_id=task_id, session_id=session_id,
                    )
                    action["rationale"] = "Task done; get QA ready"
                    actions.append(action)
            else:
                rule_ids = list(rules_for("qa", from_state, to_state, state_spec) or [])
                actions.append({
                    "id": "qa.promote.todo",
                    "entity": "qa",
                    "recordId": f"{task_id}-qa",
                    "cmd": ["edison", "qa", "promote", task_id, "--status", to_state],
                    "rationale": "Task done; get QA ready",
                    "ruleRef": {"id": rule_ids[0]} if rule_ids else None,
                    "ruleIds": rule_ids,
                    "blocking": True,
                })

    # Delegation hints for wip tasks (non-mutating suggestions)
    # Guidance rule comes from config (workflow.yaml guidance section)
    # Get guidance rules for delegation context
    delegation_guidance_rules = get_rules_for_context("delegation")
    delegation_guidance_rule = delegation_guidance_rules[0].get("id") if delegation_guidance_rules else None
    for task_id, task_entry in tasks_map.items():
        if task_entry.get("status") == STATES["task"]["wip"] and scope in (None, "tasks"):
            basic_hint = simple_delegation_hint(
                task_id, rule_id=delegation_guidance_rule
            )
            if basic_hint:
                # Enhance hint with detailed reasoning
                enhanced_hint = enhance_delegation_hint(task_id, basic_hint)
                # Find related tasks for context
                related = find_related_in_session(session_id, task_id)

                # Compute task start checklist for this wip task (early surfacing).
                task_checklist = None
                try:
                    from edison.core.workflow.checklists.task_start import TaskStartChecklistEngine

                    engine = TaskStartChecklistEngine()
                    checklist_result = engine.compute(task_id=task_id, session_id=session_id)
                    task_checklist = checklist_result.to_dict()
                except Exception:
                    # Fail-open: session next must remain usable even if checklist fails.
                    pass

                action_data = {
                    **basic_hint,
                    "delegationDetails": enhanced_hint,
                    "relatedTasks": related,
                }
                if task_checklist:
                    action_data["checklist"] = task_checklist

                actions.append(action_data)

    # Follow-ups suggestions (claim vs create-only)
    wip_done_states = {STATES["task"]["wip"], STATES["task"]["done"]}
    for task_id, task_entry in tasks_map.items():
        t_status = infer_task_status(task_id)
        if t_status not in wip_done_states:
            continue
        impl_fus = load_impl_followups(task_id)
        val_fus = load_bundle_followups(task_id)
        if not impl_fus and not val_fus:
            continue
        # Build suggestions with commands
        fus_cmds: list[dict[str, Any]] = []
        wave, base = extract_wave_and_base_id(task_id)
        for fu in impl_fus:
            slug = slugify(fu.get("title") or "follow-up")
            next_id = allocate_child_id(base)
            if fu.get("blockingBeforeValidation"):
                cmd = ["edison", "task", "new", "--id", next_id, "--wave", wave, "--slug", slug, "--parent", task_id, "--session", session_id]
                fus_cmds.append({
                    "kind": "create-link-claim",
                    "title": fu.get("title"),
                    "cmd": cmd,
                    "note": "Blocking follow-up: link to parent and claim into session",
                    "similar": _similar(fu.get("title") or "follow-up"),
                })
            else:
                cmd = ["edison", "task", "new", "--id", next_id, "--wave", wave, "--slug", slug]
                fus_cmds.append({
                    "kind": "create-only",
                    "title": fu.get("title"),
                    "cmd": cmd,
                    "note": "Non-blocking (implementation): create in tasks/todo without linking",
                    "similar": _similar(fu.get("title") or "follow-up"),
                })
        for fu in val_fus:
            slug = slugify(fu.get("title") or "follow-up")
            next_id = allocate_child_id(base)
            cmd = ["edison", "task", "new", "--id", next_id, "--wave", wave, "--slug", slug]
            fus_cmds.append({
                "kind": "create-only",
                "title": fu.get("title"),
                "cmd": cmd,
                "note": "Non-blocking (validator): create in tasks/todo without linking",
                "similar": _similar(fu.get("title") or "follow-up"),
            })
        if fus_cmds:
            followups_plan.append({
                "taskId": task_id,
                "suggestions": fus_cmds,
            })

    # UX fallback: if no other task actions were produced, guide the user back to
    # implementation work for tasks in semantic "wip".
    if scope in (None, "tasks", "session"):
        for task_id, task_entry in tasks_map.items():
            if task_entry.get("status") != STATES["task"]["wip"]:
                continue
            already_has_task_action = any(
                a.get("entity") == "task" and a.get("recordId") == task_id for a in actions
            )
            if already_has_task_action:
                continue
            actions.append(
                {
                    "id": "task.work",
                    "entity": "task",
                    "recordId": task_id,
                    "cmd": ["edison", "task", "show", task_id],
                    "rationale": "Continue implementation work for this task",
                    "ruleRef": None,
                    "ruleIds": [],
                    "blocking": False,
                }
            )

    # Build bundles for roots if children ready
    bundle_ready_states = {STATES["task"]["done"], STATES["task"]["validated"]}
    for task_id, task_entry in tasks_map.items():
        if not task_entry.get("parentId"):
            children = task_entry.get("childIds", [])
            if children and all(infer_task_status(cid) in bundle_ready_states for cid in children) and scope in (None, "qa"):
                # Rule IDs come from config (workflow.yaml), not hardcoded
                bundle_rules = rules_for("qa", STATES["qa"]["todo"], STATES["qa"]["wip"], state_spec) or []
                actions.append({
                    "id": "bundle.build",
                    "entity": "qa",
                    "recordId": f"{task_id}-qa",
                    "cmd": ["edison", "qa", "bundle", task_id, "--session", session_id],
                    "rationale": "Bundle related tasks for validation",
                    "ruleRef": {"id": bundle_rules[0]} if bundle_rules else None,
                    "ruleIds": bundle_rules,
                    "blocking": True,
                })

    # Analyze validator reports to propose QA next steps
    qa_active_states = {STATES["qa"]["wip"], STATES["qa"]["todo"]}
    for task_id, task_entry in tasks_map.items():
        q_status = infer_qa_status(task_id)
        if q_status not in qa_active_states:
            continue
        v = read_validator_reports(task_id)
        reports = v.get("reports", [])
        if not reports:
            continue
        # Suggest follow-ups based on reports
        suggestions = []
        for r in reports:
            for s in r.get("suggestedFollowups", []) or []:
                suggestions.append(s)
        # Propose creation commands for suggestions
        # Note: Task creation is not a state transition, so no transition rules apply
        # Task claim IS a transition (todo→wip), so we look up rules from config
        claim_rules = workflow_cfg.get_transition_rules("task", STATES["task"]["todo"], STATES["task"]["wip"]) or []
        for s in suggestions:
            parent_id = s.get("parentId") or task_id
            wave, base = extract_wave_and_base_id(parent_id)
            new_id = allocate_child_id(base)
            slug = s.get("suggestedSlug") or slugify(s.get("title","follow-up"))
            # Build guarded Python tasks/new command
            cmd = ["edison", "task", "new", "--id", new_id, "--wave", wave, "--slug", slug, "--owner", session["meta"]["sessionId"], "--parent", parent_id, "--session", session_id]
            actions.append({
                "id": "task.create.followup",
                "entity": "task",
                "recordId": new_id,
                "cmd": cmd,
                "rationale": f"Follow-up from {r.get('validatorId','validator')}: {s.get('title')}",
                "ruleRef": None,  # Not a transition - no transition rules
                "ruleIds": [],
                "blocking": bool(s.get("blocking")),
            })
            if s.get("claimNow"):
                actions.append({
                    "id": "task.claim",
                    "entity": "task",
                    "recordId": new_id,
                    "cmd": ["edison", "task", "claim", new_id, "--session", session_id],
                    "rationale": "Suggestion marked claimNow by validator",
                    "ruleRef": {"id": claim_rules[0]} if claim_rules else None,
                    "ruleIds": claim_rules,
                    "blocking": False,
                })
            if s.get("blocking"):
                # Task blocked transition - look up rules from config
                block_rules = workflow_cfg.get_transition_rules("task", STATES["task"]["wip"], STATES["task"]["blocked"]) or []
                actions.append({
                    "id": "task.block",
                    "entity": "task",
                    "recordId": parent_id,
                    "cmd": ["edison", "task", "status", parent_id, "--status", STATES["task"]["blocked"]],
                    "rationale": "Follow-up marked blocking; set parent to blocked",
                    "ruleRef": {"id": block_rules[0]} if block_rules else None,
                    "ruleIds": block_rules,
                    "blocking": True,
                })
        blocking_failed = [r for r in reports if not r.get("approved")]
        if blocking_failed and scope in (None, "qa"):
            # QA rejection returns to waiting - look up rules from config for wip→todo (restart)
            reject_rules = workflow_cfg.get_transition_rules("qa", STATES["qa"]["wip"], STATES["qa"]["todo"]) or []
            actions.append({
                "id": "qa.round.reject",
                "entity": "qa",
                "recordId": f"{task_id}-qa",
                "cmd": ["edison", "qa", "round", task_id, "--status", "reject", "--note", f"validators: {', '.join(r.get('validatorId','?') for r in blocking_failed)}"],
                "rationale": "Blocking validators failed; record Round and return QA to waiting",
                "ruleRef": {"id": reject_rules[0]} if reject_rules else None,
                "ruleIds": reject_rules,
                "blocking": True,
            })
        elif not blocking_failed and q_status == STATES["qa"]["wip"] and scope in (None, "qa"):
            # QA promotion to done - look up rules from config
            from_state = STATES["qa"]["wip"]
            to_state = STATES["qa"]["done"]
            recommendations = workflow_cfg.get_recommendations("qa", from_state, to_state)
            if recommendations:
                for rec in recommendations:
                    action = _build_action_from_recommendation(
                        rec, from_state, to_state, workflow_cfg, state_spec,
                        task_id=task_id, session_id=session_id,
                    )
                    action["rationale"] = "All blocking validators approved; close QA"
                    actions.append(action)
            else:
                done_rules = workflow_cfg.get_transition_rules("qa", from_state, to_state) or []
                actions.append({
                    "id": "qa.promote.done",
                    "entity": "qa",
                    "recordId": f"{task_id}-qa",
                    "cmd": ["edison", "qa", "promote", task_id, "--status", to_state],
                    "rationale": "All blocking validators approved; close QA",
                    "ruleRef": {"id": done_rules[0]} if done_rules else None,
                    "ruleIds": done_rules,
                    "blocking": True,
                })

    if limit and len(actions) > limit:
        actions = actions[:limit]

    # Build reportsMissing list for visibility
    reports_missing = build_reports_missing(session)

    # Phase 1B: context-aware rules + guard previews via RulesEngine.
    rules_engine_summary: dict[str, Any] = {}
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
            from_state: str | None = None
            to_state: str | None = None

            if entity == "task" and aid == "task.promote.done":
                from_state, to_state = STATES["task"]["wip"], STATES["task"]["done"]
            elif entity == "task" and aid == "task.claim":
                from_state, to_state = STATES["task"]["todo"], STATES["task"]["wip"]

            if not from_state or not to_state or not record_id:
                continue

            task_ctx = {"id": record_id}
            sess_ctx: dict[str, Any] = {"id": session.get("id") or session_id}
            allowed, msg = engine.check_transition_guards(
                from_state, to_state, task_ctx, sess_ctx, validation_results=None
            )
            guard_status = "allowed" if allowed else "blocked"
            guard_obj: dict[str, Any] = {
                "from": from_state,
                "to": to_state,
                "status": guard_status,
            }
            if msg:
                guard_obj["message"] = msg
            a["guard"] = guard_obj

    # Session-close evidence (surface early; do not wait until close-time failure).
    session_close_evidence: dict[str, Any] = {"required": [], "missing": []}
    try:
        from edison.core.config.domains.qa import QAConfig
        from edison.core.qa.evidence.command_evidence import parse_command_evidence
        from edison.core.qa.evidence.service import EvidenceService

        qa_cfg = QAConfig()
        from edison.core.qa.policy.session_close import get_session_close_policy

        policy = get_session_close_policy(project_root=qa_cfg.repo_root)
        required_close = list(policy.required_evidence or [])
        required_close = [str(x).strip() for x in (required_close or []) if str(x).strip()]
        session_close_evidence["required"] = list(required_close)

        if required_close and session_tasks:
            missing_close: list[str] = []
            for filename in required_close:
                ok = False
                for t in session_tasks:
                    rd = EvidenceService(t.id).get_current_round_dir()
                    if not rd:
                        continue
                    p = rd / filename
                    if not p.exists():
                        continue
                    parsed = parse_command_evidence(p)
                    if parsed is None:
                        continue
                    try:
                        if int(parsed.get("exitCode", 1)) == 0:
                            ok = True
                            break
                    except Exception:
                        continue
                if not ok:
                    missing_close.append(filename)
            session_close_evidence["missing"] = missing_close
    except Exception:
        session_close_evidence = {"required": [], "missing": []}

    # Session close preflight checklist (surface only when approaching close).
    try:
        done_tasks = [t for t in session_tasks if getattr(t, "state", None) == STATES["task"]["done"]]
        wip_tasks = [t for t in session_tasks if getattr(t, "state", None) == STATES["task"]["wip"]]
        if done_tasks and not wip_tasks:
            from edison.core.workflow.checklists.session_close_preflight import SessionClosePreflightChecklistEngine
            from edison.core.utils.paths import PathResolver

            checklist = SessionClosePreflightChecklistEngine(project_root=PathResolver.resolve_project_root()).compute(
                session_id=session_id
            )
            actions.append(
                {
                    "id": "session.close_preflight",
                    "entity": "session",
                    "recordId": session_id,
                    "cmd": ["edison", "session", "verify", session_id, "--phase", "closing"],
                    "rationale": "Session close preflight checklist (deep bundle preset, evidence, and scope invariants).",
                    "blocking": bool(checklist.get("hasBlockers", False)),
                    "checklist": checklist,
                }
            )
    except Exception:
        pass

    recommendations_list = [
        "Run 'edison session verify <session-id>' before closing to detect metadata drift (manual edits)",
        "Context7 enforcement cross-checks task metadata + git diff for accuracy",
    ]
    if session_close_evidence.get("missing"):
        anchor = sorted([t.id for t in session_tasks if t and t.id])[:1]
        anchor_id = anchor[0] if anchor else "<task-id>"
        recommendations_list.append(
            "Before session close: satisfy required session-close evidence (config-driven) "
            f"by running `edison evidence capture {anchor_id} --session-close`, then review outputs via `edison evidence show`."
        )

    return {
        "context": _build_context_payload(session_id),
        "sessionId": session_id,
        "summary": "Next actions computed",
        "actions": actions,
        "blockers": blockers,
        "reportsMissing": reports_missing,
        "followUpsPlan": followups_plan,
        "rulesEngine": rules_engine_summary,  # Context-aware rules (git diff + config)
        "sessionCloseEvidence": session_close_evidence,
        "rules": [
            "Use bundle-first validation; keep one QA per task.",
            "All moves must go through guarded CLIs.",
        ],
        "recommendations": recommendations_list,
    }


def _build_context_payload(session_id: str) -> dict[str, Any]:
    """Build the hook-safe session context payload for session-next output."""
    try:
        from edison.core.session.context_payload import build_session_context_payload
        from edison.core.utils.paths import PathResolver

        project_root = PathResolver.resolve_project_root()
        return build_session_context_payload(project_root=project_root, session_id=session_id).to_dict()
    except Exception:
        # Fail-open: session-next must remain usable even if context building fails.
        return {"isEdisonProject": True, "sessionId": session_id}


def main() -> None:  # CLI facade for direct execution
    """CLI entry point for compute_next."""
    parser = argparse.ArgumentParser()
    parser.add_argument("session_id")
    parse_common_args(parser)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--scope", choices=["tasks", "qa", "session"])
    args = parser.parse_args()
    session_id = validate_session_id(args.session_id)

    # parse_common_args() exposes --repo-root as `project_root`
    if getattr(args, "project_root", None):
        os.environ["AGENTS_PROJECT_ROOT"] = str(args.project_root)

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
        # Enhanced human-readable output with rules, validators, delegation details
        print(format_human_readable(payload))


if __name__ == "__main__":
    sys.exit(main())
