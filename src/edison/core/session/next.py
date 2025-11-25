#!/usr/bin/env python3
"""Compute deterministic next actions for a session (library module).

This logic now lives in ``lib.session.next`` with thin CLI wrappers under
``scripts/session/next``. Keeping it in lib makes it reusable from both the
CLI and other orchestrators without importing scripts directly.

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

import difflib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from edison.core.paths.project import get_project_config_dir 
from edison.core.utils import cli 
from edison.core.utils.git import get_repo_root 
from edison.core.paths.management import get_management_paths

from edison.core.session import manager as session_manager
from edison.core.session import store as session_store
from edison.core.session import graph as session_graph
from edison.core.session import config as session_config
from edison.core import task  # type: ignore
from edison.core.qa import validator as qa_validator 
from edison.core.io_utils import read_json_safe as io_read_json_safe 
from edison.core.evidence import ( 
    missing_evidence_blockers as _ev_missing_evidence_blockers,
    read_validator_jsons as _ev_read_validator_jsons,
    load_impl_followups as _ev_load_impl_followups,
    load_bundle_followups as _ev_load_bundle_followups,
)
from edison.core.qa import evidence as qa_evidence 
load_session = session_manager.get_session
build_validation_bundle = session_graph.build_validation_bundle
normalize_session_id = session_store.normalize_session_id


RULE_IDS = {
    "validation_first": "RULE.VALIDATION.FIRST",
    "bundle_first": "RULE.VALIDATION.BUNDLE_FIRST",
    "bundle_approved": "RULE.VALIDATION.BUNDLE_APPROVED_MARKER",
    "fail_closed": "RULE.GUARDS.FAIL_CLOSED",
    "link_scope": "RULE.LINK.SESSION_SCOPE_ONLY",
    "context7": "RULE.CONTEXT7.POSTTRAINING_REQUIRED",
    "evidence": "RULE.EVIDENCE.ROUND_COMMANDS_REQUIRED",
    "delegation": "RULE.DELEGATION.PRIORITY_CHAIN",
}


def _project_cfg_dir() -> Path:
    return get_project_config_dir(get_repo_root())


def _infer_task_status(task_id: str) -> str:
    try:
        p = task.find_record(task_id, "task")
        return task.infer_status_from_path(p, "task") or "unknown"
    except FileNotFoundError:
        return "missing"


def _infer_qa_status(task_id: str) -> str:
    try:
        p = task.find_record(task_id, "qa")
        return task.infer_status_from_path(p, "qa") or "missing"
    except FileNotFoundError:
        return "missing"


def _missing_evidence_blockers(task_id: str) -> List[Dict[str, Any]]:
    return _ev_missing_evidence_blockers(task_id)


def _read_validator_jsons(task_id: str) -> Dict[str, Any]:
    return _ev_read_validator_jsons(task_id)

def _load_impl_followups(task_id: str) -> List[Dict[str, Any]]:
    return _ev_load_impl_followups(task_id)

def _load_bundle_followups(task_id: str) -> List[Dict[str, Any]]:
    return _ev_load_bundle_followups(task_id)

def _all_task_files() -> List[Path]:
    mgmt_paths = get_management_paths(task.ROOT)
    root = mgmt_paths.get_tasks_root()
    files: List[Path] = []
    for st in ["todo", "wip", "blocked", "done", "validated"]:
        d = root / st
        if d.exists():
            files.extend(sorted(d.glob("*.md")))
    return files

def _stem_to_slug(stem: str) -> str:
    # stem example: 201-wave2-my-feature or 201.1-wave2-fix
    parts = stem.split("-", 2)
    if len(parts) >= 3:
        return parts[2]
    return stem

def _similar_tasks(title: str, *, top: int = 3, threshold: float = 0.6) -> List[Dict[str, Any]]:
    """Return up to 'top' similar existing tasks by slug similarity with scores."""
    want = _slugify(title)
    candidates: List[Tuple[str, float]] = []
    for f in _all_task_files():
        cand_id = f.stem
        cand_slug = _stem_to_slug(cand_id)
        score = difflib.SequenceMatcher(None, want, cand_slug).ratio()
        if score >= threshold:
            candidates.append((cand_id, score))
    candidates.sort(key=lambda x: x[1], reverse=True)
    out: List[Dict[str, Any]] = []
    for cid, sc in candidates[:top]:
        out.append({"taskId": cid, "score": round(sc, 2)})
    return out


def _slugify(s: str) -> str:
    import re
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "follow-up"


def _extract_wave_and_base_id(task_id: str) -> tuple[str, str]:
    """Return (wave, baseId) from a task filename, defaulting sensibly."""
    try:
        p = task.find_record(task_id, "task")
        name = p.name  # e.g., 150-wave1-foo.md or 201.2-wave2-bar.md
        base = name.split("-", 1)[0]  # e.g., 150 or 201.2
        wave = name.split("-", 2)[1]  # e.g., wave1
        return wave, base
    except Exception:
        return "wave1", task_id


def _allocate_child_id(base_id: str) -> str:
    """Find the next available base_id.N by scanning .project/tasks across states."""
    mgmt_paths = get_management_paths(task.ROOT)
    root = mgmt_paths.get_tasks_root()
    states = ["todo","wip","blocked","done","validated"]
    existing = set()
    for st in states:
        d = root / st
        if d.exists():
            for f in d.glob("*.md"):
                tid = f.name.split("-",1)[0]
                if tid.startswith(base_id + "."):
                    existing.add(tid)
    # next N starting at 1
    n = 1
    while True:
        cand = f"{base_id}.{n}"
        if cand not in existing:
            return cand
        n += 1



def _rules_for(domain: str, current: str, to: str, state_spec: Dict[str, Any]) -> List[str]:
    try:
        domain_spec = state_spec.get(domain, {})
        for tr in domain_spec.get("transitions", {}).get(current, []):
            if tr.get("to") == to:
                return tr.get("rules", []) or []
    except Exception:
        pass
    return []


def _expand_rules(rule_ids: List[str]) -> List[Dict[str, Any]]:
    if not rule_ids:
        return []
    reg_path = _project_cfg_dir() / "rules" / "registry.json"
    try:
        registry = io_read_json_safe(reg_path)
    except Exception:
        return []
    out: List[Dict[str, Any]] = []
    for rid in rule_ids:
        entry = next((r for r in registry.get("rules", []) if r.get("id") == rid), None)
        if not entry:
            continue
        src = REPO_ROOT / entry["sourcePath"]
        start = entry.get("start") or f"<!-- RULE: {rid} START -->"
        end = entry.get("end") or f"<!-- RULE: {rid} END -->"
        try:
            lines = src.read_text().splitlines()
            s = next(i for i,l in enumerate(lines) if start in l) + 1
            e = next(i for i in range(s, len(lines)) if end in lines[i])
            content = "\n".join(lines[s:e]).rstrip()
        except Exception:
            content = ""
        out.append({
            "id": rid,
            "title": entry.get("title", rid),
            "sourcePath": entry.get("sourcePath"),
            "content": content,
        })
    return out


def _find_related_in_session(session_id: str, task_id: str) -> List[Dict[str, Any]]:
    """Find related tasks/QAs in session: parent, children, linked tasks.

    Helps orchestrator understand dependencies and context.
    """
    try:
        session = load_session(session_id)
    except Exception:
        return []

    related = []
    task_data = session.get("tasks", {}).get(task_id, {})

    # Parent task
    parent_id = task_data.get("parentId")
    if parent_id:
        parent_status = _infer_task_status(parent_id)
        parent_qa = _infer_qa_status(parent_id)
        related.append({
            "relationship": "parent",
            "taskId": parent_id,
            "taskStatus": parent_status,
            "qaStatus": parent_qa,
            "note": f"This task is a follow-up to {parent_id}",
        })

    # Child tasks
    for child_id in task_data.get("childIds", []):
        child_status = _infer_task_status(child_id)
        child_qa = _infer_qa_status(child_id)
        related.append({
            "relationship": "child",
            "taskId": child_id,
            "taskStatus": child_status,
            "qaStatus": child_qa,
            "note": f"Follow-up task spawned from {task_id}",
        })

    # Linked tasks (same root family)
    if parent_id:
        # Find siblings (other children of same parent)
        for tid, tdata in session.get("tasks", {}).items():
            if tid != task_id and tdata.get("parentId") == parent_id:
                sib_status = _infer_task_status(tid)
                sib_qa = _infer_qa_status(tid)
                related.append({
                    "relationship": "sibling",
                    "taskId": tid,
                    "taskStatus": sib_status,
                    "qaStatus": sib_qa,
                    "note": f"Sibling task (same parent {parent_id})",
                })

    return related


def compute_next(session_id: str, scope: Optional[str], limit: int) -> Dict[str, Any]:
    session = load_session(session_id)
    cfg = session_config.SessionConfig()
    # state_spec structure expected by _rules_for: {"domain": {"transitions": ...}}
    state_spec = cfg._state_config # Accessing internal for now to minimize refactor of _rules_for
    actions: List[Dict[str, Any]] = []
    blockers: List[Dict[str, Any]] = []
    followups_plan: List[Dict[str, Any]] = []
    tasks_map: Dict[str, Any] = session.get("tasks", {}) or {}

    # Validation-first: QA in todo with task done → start validators (promote to wip)
    for task_id, task in tasks_map.items():
        t_status = _infer_task_status(task_id)
        q_status = _infer_qa_status(task_id)
        if q_status == "todo" and t_status == "done" and scope in (None, "qa"):
            rule_ids = _rules_for("qa", "todo", "wip", state_spec) or [RULE_IDS["validation_first"]]
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
    for task_id, task in tasks_map.items():
        # Consider only tasks explicitly marked blocked
        if task.get("status") != "blocked":
            continue
        children = task.get("childIds", []) or []
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
            return _infer_task_status(cid) in {"done", "validated"}

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
    for task_id, task in session.get("tasks", {}).items():
        if task.get("status") != "wip":
            continue
        children = task.get("childIds", []) or []
        if children and not all((tasks_map.get(cid, {}) or {}).get("status") in {"done", "validated"} for cid in children):
            continue
        missing = _missing_evidence_blockers(task_id)
        # Only propose if automation evidence exists (i.e., missing list empty)
        if not missing and scope in (None, "tasks", "session"):
            rule_ids = _rules_for("task", "wip", "done", state_spec) or [RULE_IDS["fail_closed"]]
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
    for task_id, task in tasks_map.items():
        if task.get("status") == "wip" and _infer_qa_status(task_id) == "missing" and scope in (None, "qa"):
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
    for task_id, task in tasks_map.items():
        if task.get("status") == "wip":
            blockers.extend(_missing_evidence_blockers(task_id))

    # waiting->todo when task done
    for task_id, task in tasks_map.items():
        if _infer_task_status(task_id) == "done" and _infer_qa_status(task_id) == "waiting" and scope in (None, "qa"):
            rule_ids = _rules_for("qa", "waiting", "todo", state_spec) or [RULE_IDS["validation_first"]]
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
    for task_id, task in session.get("tasks", {}).items():
        if task.get("status") == "wip" and scope in (None, "tasks"):
            basic_hint = qa_validator.simple_delegation_hint(
                task_id, rule_id=RULE_IDS["delegation"]
            )
            if basic_hint:
                # Enhance hint with detailed reasoning
                enhanced_hint = qa_validator.enhance_delegation_hint(task_id, basic_hint)
                # Find related tasks for context
                related = _find_related_in_session(session_id, task_id)

                actions.append({
                    **basic_hint,
                    "delegationDetails": enhanced_hint,  # NEW: Detailed reasoning
                    "relatedTasks": related,  # NEW: Parent/child/sibling context
                })

    # Follow-ups suggestions (claim vs create-only)
    for task_id, task in session.get("tasks", {}).items():
        t_status = _infer_task_status(task_id)
        if t_status not in {"wip", "done"}:
            continue
        impl_fus = _load_impl_followups(task_id)
        val_fus = _load_bundle_followups(task_id)
        if not impl_fus and not val_fus:
            continue
        # Build suggestions with commands
        fus_cmds: List[Dict[str, Any]] = []
        wave, base = _extract_wave_and_base_id(task_id)
        for fu in impl_fus:
            slug = _slugify(fu.get("title") or "follow-up")
            next_id = _allocate_child_id(base)
            if fu.get("blockingBeforeValidation"):
                cmd = ["scripts/tasks/new", "--id", next_id, "--wave", wave, "--slug", slug, "--parent", task_id, "--session", session_id]
                fus_cmds.append({
                    "kind": "create-link-claim",
                    "title": fu.get("title"),
                    "cmd": cmd,
                    "note": "Blocking follow-up: link to parent and claim into session",
                    "similar": _similar_tasks(fu.get("title") or "follow-up"),
                })
            else:
                cmd = ["scripts/tasks/new", "--id", next_id, "--wave", wave, "--slug", slug]
                fus_cmds.append({
                    "kind": "create-only",
                    "title": fu.get("title"),
                    "cmd": cmd,
                    "note": "Non-blocking (implementation): create in tasks/todo without linking",
                    "similar": _similar_tasks(fu.get("title") or "follow-up"),
                })
        for fu in val_fus:
            slug = _slugify(fu.get("title") or "follow-up")
            next_id = _allocate_child_id(base)
            cmd = ["scripts/tasks/new", "--id", next_id, "--wave", wave, "--slug", slug]
            fus_cmds.append({
                "kind": "create-only",
                "title": fu.get("title"),
                "cmd": cmd,
                "note": "Non-blocking (validator): create in tasks/todo without linking",
                "similar": _similar_tasks(fu.get("title") or "follow-up"),
            })
        if fus_cmds:
            followups_plan.append({
                "taskId": task_id,
                "suggestions": fus_cmds,
            })

    # Build bundles for roots if children ready
    for task_id, task in session.get("tasks", {}).items():
        if not task.get("parentId"):
            children = task.get("childIds", [])
            if children and all(_infer_task_status(cid) in {"done", "validated"} for cid in children) and scope in (None, "qa"):
                rule_id = ( _rules_for("qa", "todo", "wip", state_spec) or [RULE_IDS["bundle_first"]] )[0]
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
    for task_id, task in session.get("tasks", {}).items():
        q_status = _infer_qa_status(task_id)
        if q_status not in {"wip", "todo"}:
            continue
        v = _read_validator_jsons(task_id)
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
            wave, base = _extract_wave_and_base_id(parent_id)
            new_id = _allocate_child_id(base)
            slug = s.get("suggestedSlug") or _slugify(s.get("title","follow-up"))
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
    reports_missing: List[Dict[str, Any]] = []
    for task_id, task in session.get("tasks", {}).items():
        # Validators JSON expected when QA is wip/todo
        qstat = _infer_qa_status(task_id)
        if qstat in {"wip", "todo"}:
            v = _read_validator_jsons(task_id)
            have = {r.get("validatorId") for r in v.get("reports", [])}
            # Derive expected blocking IDs from validators config
            try:
                cfg = io_read_json_safe(_project_cfg_dir()/"validators"/"config.json")
                need = []
                for vcat in ("global","critical","specialized"):
                    for vv in cfg.get("validators",{}).get(vcat,[]):
                        if vv.get("alwaysRun") or vv.get("blocksOnFail") or vcat in ("global","critical"):
                            need.append(vv.get("id"))
                for vid in need:
                    if vid not in have:
                        reports_missing.append({
                            "taskId": task_id,
                            "type": "validator",
                            "validatorId": vid,
                            "suggested": ["(re)run validator wave and write JSON per schema", f"scripts/qa/promote --task {task_id} --to wip"],
                        })
            except Exception:
                pass
        # Implementation Report JSON required for ALL tasks
        try:
            ev_root = qa_evidence.get_evidence_dir(task_id)
            latest_round = qa_evidence.get_latest_round(task_id)
            if latest_round is not None:
                impl_report = qa_evidence.get_implementation_report_path(task_id, latest_round)
                if not impl_report.exists():
                    rel_path = task.safe_relative(impl_report)
                    reports_missing.append({
                        "taskId": task_id,
                        "type": "implementation",
                        "path": rel_path,
                        "suggested": [
                            "Write Implementation Report JSON per schema",
                            f"scripts/implementation/validate {rel_path}",
                        ],
                    })
        except Exception:
            pass
        # Context7 markers expected for post-training packages used by this task
        try:
            # local helpers (mirrors tasks/ready heuristics)
            def _load_cfg():
                try:
                    return io_read_json_safe(_project_cfg_dir()/"validators"/"config.json")
                except Exception:
                    return {}
            def _files_for_task(tid: str) -> List[str]:
                try:
                    p = task.find_record(tid, "task")
                    txt = p.read_text(errors="ignore")
                except FileNotFoundError:
                    return []
                files: List[str] = []
                capture = False
                for line in txt.splitlines():
                    if "Primary Files / Areas" in line:
                        capture = True
                        parts = line.split(":", 1)
                        if len(parts) > 1 and parts[1].strip():
                            files.extend([f.strip() for f in parts[1].split(",") if f.strip()])
                        continue
                    if capture:
                        if line.startswith("## "):
                            break
                        if line.strip().startswith("-"):
                            files.append(line.split("-", 1)[1].strip())
                return files
            def _matches(file_path: str, pkg: str) -> bool:
                import fnmatch
                patterns = {
                    "next": ["app/**/*", "**/route.ts", "**/layout.tsx", "**/page.tsx"],
                    "react": ["*.tsx", "*.jsx", "**/components/**/*"],
                    "uistylescss": ["*.css", "uistyles.config.*"],
                    "zod": ["**/*.schema.ts", "**/*.validation.ts", "**/route.ts"],
                    "framer-motion": ["*.tsx", "*.jsx"],
                    "typescript": ["*.ts", "*.tsx"],
                }
                for pat in patterns.get(pkg, []):
                    if fnmatch.fnmatch(file_path, pat):
                        return True
                return False
            cfg = _load_cfg()
            pkgs = list((cfg.get("postTrainingPackages") or {}).keys())
            files = _files_for_task(task_id)
            used = {pkg for pkg in pkgs for f in files if _matches(f, pkg)}
            if used:
                ev_root = qa_evidence.get_evidence_dir(task_id)
                latest_round = qa_evidence.get_latest_round(task_id)
                latest = ev_root / f"round-{latest_round}" if latest_round is not None else None
                missing_pkgs: List[str] = []
                for pkg in used:
                    if not latest or (
                        not (latest / f"context7-{pkg}.txt").exists()
                        and not (latest / f"context7-{pkg}.md").exists()
                    ):
                        missing_pkgs.append(pkg)
                if missing_pkgs:
                    reports_missing.append({
                        "taskId": task_id,
                        "type": "context7",
                        "packages": sorted(missing_pkgs),
                        "suggested": [
                            "Write context7-<package>.txt in latest round with topics and doc references",
                            "Add a note in the task file documenting Context7 usage"
                        ],
                    })
        except Exception:
            pass

    # Collect all unique rule IDs from actions
    all_rule_ids: List[str] = []
    for a in actions:
        for rid in a.get("ruleIds", []):
            if rid not in all_rule_ids:
                all_rule_ids.append(rid)

    # Always expand rules (no flag needed - default behavior)
    expanded_rules = _expand_rules(all_rule_ids)

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
    import argparse
    from edison.core.session.context import SessionContext
    parser = argparse.ArgumentParser()
    parser.add_argument("session_id")
    cli.parse_common_args(parser)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--scope", choices=["tasks", "qa", "session"])
    args = parser.parse_args()
    session_id = normalize_session_id(args.session_id)

    if args.repo_root:
        os.environ["AGENTS_PROJECT_ROOT"] = str(args.repo_root)

    if args.limit == 0:
        try:
            manifest = io_read_json_safe(_project_cfg_dir() / "manifest.json")
            limit = int(manifest.get("orchestration", {}).get("maxConcurrentAgents", 5))
        except Exception:
            limit = 5
    else:
        limit = args.limit

    with SessionContext.in_session_worktree(session_id):
        payload = compute_next(session_id, args.scope, limit)

    if args.json:
        print(cli.output_json(payload))
    else:
        # Enhanced human-readable output with rules, validators, delegation details
        print(f"═══ Session {payload['sessionId']} – Next Steps ═══\n")

        # Show applicable rules FIRST (proactive, not just at enforcement)
        if payload.get("rulesEngine") or payload.get("rulesExpanded"):
            print("📋 APPLICABLE RULES (read FIRST):")

            # Context-aware rules from RulesEngine
            re_summary = payload.get("rulesEngine") or {}
            for ctx_type, rules in re_summary.items():
                label = str(ctx_type).upper()
                print(f"\n  Context: {label}")
                for r in rules:
                    blocking = " (blocking)" if r.get("blocking") else ""
                    print(f"    - {r['id']}{blocking}: {r.get('description','')}")

            # Legacy expanded rules from registry (kept for backwards compatibility)
            if payload.get("rulesExpanded"):
                if re_summary:
                    print("\n  Registry Rules:")
                for rule in payload["rulesExpanded"]:
                    print(f"\n  {rule['id']} - {rule.get('title', 'N/A')}")
                    print(f"  Source: {rule.get('sourcePath', 'N/A')}")
                    if rule.get("content"):
                        # Show first 2 lines of rule content
                        lines = rule["content"].split("\n")[:2]
                        for line in lines:
                            print(f"    {line}")
            print()

        # Show actions with enhanced details
        print(f"🎯 RECOMMENDED ACTIONS ({len(payload.get('actions', []))} total):\n")
        for i, a in enumerate(payload.get("actions", []), 1):
            cmd = " ".join(a["cmd"]) if a.get("cmd") else a.get("id")
            rid = a.get("recordId", "")
            blocking = "🔴 BLOCKING" if a.get("blocking") else "🟢 OPTIONAL"

            print(f"{i}. [{blocking}] {a['id']} for `{rid}`")
            print(f"   Command: {cmd}")
            if a.get("rationale"):
                print(f"   Why: {a['rationale']}")

            # Show guard preview when available
            guard = a.get("guard") or {}
            if guard:
                status = str(guard.get("status") or "unknown")
                icon = "✅" if status == "allowed" else ("🔒" if status == "blocked" else "⚪")
                g_from = guard.get("from") or "?"
                g_to = guard.get("to") or "?"
                if status == "blocked" and guard.get("message"):
                    print(f"   Guard: {icon} {g_from} → {g_to} ({guard['message']})")
                else:
                    print(f"   Guard: {icon} {g_from} → {g_to}")

            # Show validator roster if present
            if a.get("validatorRoster"):
                roster = a["validatorRoster"]
                detection = roster.get("detectionMethod", "unknown")
                detection_label = "🎯 GIT DIFF" if detection == "git-diff" else "📄 TASK FILES"
                print(f"\n   📊 VALIDATOR ROSTER ({detection_label}):")
                print(f"      Total blocking: {roster.get('totalBlocking', 0)} | Max concurrent: {roster.get('maxConcurrent', 5)}")

                if roster.get("alwaysRequired"):
                    print(f"\n      ✅ Always Required ({len(roster['alwaysRequired'])} validators):")
                    for v in roster["alwaysRequired"]:
                        print(f"         - {v['id']} (model: {v['model']}, role: {v['zenRole']})")

                if roster.get("triggeredBlocking"):
                    print(f"\n      ⚠️  Triggered Blocking ({len(roster['triggeredBlocking'])} validators):")
                    for v in roster["triggeredBlocking"]:
                        method_icon = "🎯" if v.get("detectionMethod") == "git-diff" else "📄"
                        print(f"         {method_icon} {v['id']} (model: {v['model']}, role: {v['zenRole']})")
                        print(f"           Reason: {v['reason']}")

                if roster.get("triggeredOptional"):
                    print(f"\n      💡 Triggered Optional ({len(roster['triggeredOptional'])} validators):")
                    for v in roster["triggeredOptional"]:
                        method_icon = "🎯" if v.get("detectionMethod") == "git-diff" else "📄"
                        print(f"         {method_icon} {v['id']} (model: {v['model']}, role: {v['zenRole']})")

                if roster.get("decisionPoints"):
                    print(f"\n      🤔 Decision Points:")
                    for dp in roster["decisionPoints"]:
                        print(f"         - {dp}")

            # Show delegation details if present
            if a.get("delegationDetails"):
                details = a["delegationDetails"]
                if details.get("suggested"):
                    print(f"\n   🔧 DELEGATION SUGGESTION:")
                    print(f"      Model: {details.get('model')} | Role: {details.get('zenRole')}")
                    print(f"      Interface: {details.get('interface')}")
                    if details.get("reasoning"):
                        print(f"      Reasoning:")
                        for r in details["reasoning"]:
                            print(f"         - {r}")

            # Show related tasks if present
            if a.get("relatedTasks"):
                related = a["relatedTasks"]
                if related:
                    print(f"\n   🔗 RELATED TASKS IN SESSION:")
                    for rel in related[:3]:  # Show max 3
                        print(f"      - {rel['relationship'].upper()}: {rel['taskId']} (task: {rel['taskStatus']}, qa: {rel['qaStatus']})")
                        print(f"        {rel['note']}")

            print()  # Blank line between actions

        # Show blockers
        if payload.get("blockers"):
            print("🚫 BLOCKERS:")
            for b in payload["blockers"]:
                print(f"   - {b['recordId']}: {b['message']}")
                if b.get("fixCmd"):
                    print(f"     Fix: {' '.join(b['fixCmd'])}")
            print()

        # Show missing reports
        if payload.get("reportsMissing"):
            print("⚠️  MISSING REPORTS:")
            for r in payload["reportsMissing"]:
                print(f"   - Task {r['taskId']}: Missing {r['type']} report")
                if r.get("validatorId"):
                    print(f"     Validator: {r['validatorId']}")
                if r.get("packages"):
                    print(f"     Packages: {', '.join(r['packages'])}")
                if r.get("suggested"):
                    print(f"     Suggested fix:")
                    for s in r["suggested"]:
                        print(f"       - {s}")
            print()

        # Show recommendations
        if payload.get("recommendations"):
            print("💡 RECOMMENDATIONS:")
            for rec in payload["recommendations"]:
                print(f"   - {rec}")
            print()

        # Show follow-ups plan
        if payload.get("followUpsPlan"):
            print("🧩 FOLLOW-UPS (Claim vs Create-only):\n")
            for plan in payload["followUpsPlan"]:
                print(f"- Parent: `{plan['taskId']}`")
                for s in plan.get("suggestions", []):
                    cmd = " ".join(s.get("cmd", []))
                    kind = s.get("kind")
                    title = s.get("title") or "(untitled)"
                    icon = "🔗" if kind == "create-link-claim" else "➕"
                    print(f"  {icon} {title}")
                    print(f"     {s.get('note')}")
                    print(f"     Command: {cmd}")
                    if s.get("similar"):
                        print("     Similar existing:")
                        for m in s["similar"]:
                            print(f"       - {m['taskId']} (score {m['score']})")
            print()

        print("═══ End of Next Steps ═══")


if __name__ == "__main__":
    sys.exit(main())
