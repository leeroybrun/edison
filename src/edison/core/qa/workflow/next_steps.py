"""Shared next-steps helpers for QA workflow CLIs.

This module centralizes stable, user-facing guidance so multiple commands
(`task claim`, `task new`, `qa new`) don't drift in output shape or wording.
"""
from __future__ import annotations

from typing import Any, Dict, List, TypedDict


class NextStep(TypedDict, total=False):
    id: str
    title: str
    message: str
    commands: List[str]
    taskIds: List[str]


class QANextStepsPayload(TypedDict):
    qaId: str
    qaState: str
    qaPath: str
    qaCreated: bool
    nextSteps: List[str]


class BundleReportsPayload(TypedDict):
    bundleImplementationReportRequired: bool
    taskImplementationReportRequired: bool
    notes: List[str]


class BundleNextStepsPayload(TypedDict):
    rootTask: str
    scope: str
    nextSteps: List[NextStep]
    bundleReports: BundleReportsPayload


class PromoteNextStepsPayload(TypedDict):
    taskId: str
    targetStatus: str
    reason: str
    nextSteps: List[NextStep]


_QA_OPEN_INSTRUCTION = (
    "Open the QA brief and update it (commands/expected results/evidence links) "
    "before/while implementing."
)


def build_qa_next_steps_payload(
    *,
    qa_id: str,
    qa_state: str,
    qa_path: str,
    created: bool,
) -> QANextStepsPayload:
    return {
        "qaId": str(qa_id),
        "qaState": str(qa_state),
        "qaPath": str(qa_path),
        "qaCreated": bool(created),
        "nextSteps": [_QA_OPEN_INSTRUCTION],
    }


def format_qa_next_steps_text(payload: QANextStepsPayload) -> str:
    created_hint = "created" if payload["qaCreated"] else "exists"
    return (
        f"QA: {payload['qaId']} ({payload['qaState']}; {created_hint})\n"
        f"QA Path: @{payload['qaPath']}\n"
        f"Next: {payload['nextSteps'][0]}"
    )

def format_steps_text(steps: List[NextStep]) -> str:
    if not steps:
        return "Next steps: (none)"
    lines: List[str] = ["Next steps:"]
    for step in steps:
        title = str(step.get("title") or step.get("id") or "").strip()
        if title:
            lines.append(f"- {title}")
        message = str(step.get("message") or "").strip()
        if message:
            lines.append(f"  {message}")
        for cmd in (step.get("commands") or [])[:6]:
            lines.append(f"  - {cmd}")
    return "\n".join(lines)


def build_round_next_steps(
    *,
    root_task_id: str,
    scope: str,
    round_num: int,
) -> List[NextStep]:
    root = str(root_task_id).strip()
    scope_used = str(scope or "hierarchy").strip() or "hierarchy"
    return [
        {
            "id": "update_reports",
            "title": "Update round reports",
            "message": "Fill the implementation report delta section before validating.",
            "commands": [],
        },
        {
            "id": "capture_evidence",
            "title": "Capture required command evidence",
            "message": "Avoid `--only` unless rerunning specific commands; ensure required evidence is complete.",
            "commands": [
                f"edison evidence capture {root}",
                f"edison evidence status {root}",
            ],
        },
        {
            "id": "run_validation",
            "title": "Run validation for this round",
            "commands": [
                f"edison qa validate {root} --scope {scope_used} --round {int(round_num)} --execute"
            ],
        },
    ]


def build_validate_next_steps_from_checklist(
    *,
    root_task_id: str,
    scope: str,
    checklist: Dict[str, Any] | None,
) -> List[NextStep]:
    root = str(root_task_id).strip()
    scope_used = str(scope or "hierarchy").strip() or "hierarchy"
    items = (checklist or {}).get("items") if isinstance(checklist, dict) else None
    cmds: List[str] = []
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            for cmd in item.get("suggestedCommands") or []:
                s = str(cmd).strip()
                if s:
                    cmds.append(s)
    seen: set[str] = set()
    deduped: List[str] = []
    for c in cmds:
        if c in seen:
            continue
        seen.add(c)
        deduped.append(c)

    if deduped:
        return [
            {
                "id": "resolve_blockers",
                "title": "Resolve preflight blockers",
                "message": "Fix the checklist blockers before executing validators.",
                "commands": deduped[:8],
            }
        ]

    return [
        {
            "id": "execute_validation",
            "title": "Execute validators",
            "commands": [f"edison qa validate {root} --scope {scope_used} --execute"],
        }
    ]


def build_bundle_next_steps_payload(
    *,
    manifest: Dict[str, Any],
    project_root: Any,
) -> BundleNextStepsPayload:
    """Build dynamic next-steps guidance for validation bundles.

    This payload is intended to be used by multiple CLI commands (`qa bundle`,
    `task bundle add/show`) so guidance doesn't drift.

    Notes:
    - Bundles do NOT have a separate "bundle implementation report".
    - Implementation reports are per-task (and round-scoped for validation).
    """
    from edison.core.config.domains.workflow import WorkflowConfig

    wf = WorkflowConfig(repo_root=project_root)
    qa_done = str(wf.get_semantic_state("qa", "done"))
    qa_validated = str(wf.get_semantic_state("qa", "validated"))
    task_done = str(wf.get_semantic_state("task", "done"))
    task_validated = str(wf.get_semantic_state("task", "validated"))
    ready_task_states = {task_done, task_validated}

    root_task = str(manifest.get("rootTask") or "").strip()
    scope = str(manifest.get("scope") or "hierarchy").strip() or "hierarchy"

    tasks = [t for t in (manifest.get("tasks") or []) if isinstance(t, dict)]
    pending = [
        str(t.get("taskId") or "").strip()
        for t in tasks
        if str(t.get("taskId") or "").strip()
        and str(t.get("taskStatus") or "").strip() not in ready_task_states
    ]

    root_qa_status = "missing"
    for t in tasks:
        if str(t.get("taskId") or "").strip() == root_task:
            root_qa_status = str(t.get("qaStatus") or "missing")
            break

    steps: List[NextStep] = []

    if pending:
        steps.append(
            {
                "id": "finish_tasks",
                "title": "Finish bundle tasks before validating",
                "message": "Bundle validation is only meaningful once all tasks are implemented (done/validated).",
                "taskIds": sorted({t for t in pending if t}),
                "commands": [f"edison task done {tid}" for tid in sorted({t for t in pending if t})[:5]],
            }
        )

    if root_task and root_qa_status == "missing":
        steps.append(
            {
                "id": "create_root_qa",
                "title": "Create QA for the bundle root",
                "message": "Rounds are tracked in the bundle root QA history; create it before preparing a new round.",
                "commands": [f"edison qa new {root_task}"],
            }
        )

    # Always point to the canonical per-round entrypoint (it also seeds reports).
    if root_task:
        steps.append(
            {
                "id": "prepare_round",
                "title": "Prepare a new validation round",
                "message": "Creates round-N and initializes per-round reports (implementation + validation summary).",
                "commands": [f"edison qa round prepare {root_task} --scope {scope}"],
            }
        )
        steps.append(
            {
                "id": "run_validation",
                "title": "Run bundle validation",
                "message": "Runs validators against the resolved cluster (root + members).",
                "commands": [f"edison qa validate {root_task} --scope {scope} --execute"],
            }
        )
        steps.append(
            {
                "id": "promote_on_approve",
                "title": "Promote when approved",
                "message": "After validation is approved and the validation summary is written, promote QA through the final states.",
                "commands": [
                    f"edison qa promote {root_task} --status {qa_done}",
                    f"edison qa promote {root_task} --status {qa_validated}",
                ],
            }
        )

    bundle_reports: BundleReportsPayload = {
        "bundleImplementationReportRequired": False,
        "taskImplementationReportRequired": True,
        "notes": [
            "Do not create a separate implementation report for the bundle itself.",
            "Each task has its own implementation report (per round).",
        ],
    }

    return {
        "rootTask": root_task,
        "scope": scope,
        "nextSteps": steps,
        "bundleReports": bundle_reports,
    }


def format_bundle_next_steps_text(payload: BundleNextStepsPayload) -> str:
    steps = payload.get("nextSteps") or []
    if not steps:
        return "Next steps: (none)"
    lines: List[str] = ["Next steps:"]
    for step in steps:
        title = str(step.get("title") or step.get("id") or "").strip()
        if title:
            lines.append(f"- {title}")
        message = str(step.get("message") or "").strip()
        if message:
            lines.append(f"  {message}")
        commands = step.get("commands") or []
        for cmd in commands[:5]:
            lines.append(f"  - {cmd}")
        task_ids = step.get("taskIds") or []
        if task_ids:
            shown = ", ".join(task_ids[:8])
            suffix = f", … +{len(task_ids) - 8}" if len(task_ids) > 8 else ""
            lines.append(f"  Tasks: {shown}{suffix}")
    return "\n".join(lines)


def build_promote_next_steps_payload(
    *,
    task_id: str,
    target_status: str,
    reason: str,
    scope: str = "auto",
) -> PromoteNextStepsPayload:
    tid = str(task_id).strip()
    target = str(target_status).strip()
    why = str(reason).strip() or "blocked"
    scope_used = str(scope or "auto").strip() or "auto"

    steps: List[NextStep] = []

    if why == "revalidation_required":
        steps.append(
            {
                "id": "rerun_validation",
                "title": "Re-run validation to refresh the bundle approval summary",
                "message": "The existing validation summary is stale relative to reports/tasks; re-run validation and summarize verdict before promoting.",
                "commands": [
                    f"edison qa validate {tid} --scope {scope_used} --execute",
                    f"edison qa round summarize-verdict {tid} --scope {scope_used}",
                ],
            }
        )
        steps.append(
            {
                "id": "retry_promote",
                "title": "Retry promotion",
                "commands": [f"edison qa promote {tid} --status {target}"],
            }
        )
    else:
        steps.append(
            {
                "id": "retry_promote",
                "title": "Retry promotion",
                "commands": [f"edison qa promote {tid} --status {target}"],
            }
        )

    return {
        "taskId": tid,
        "targetStatus": target,
        "reason": why,
        "nextSteps": steps,
    }


def format_promote_next_steps_text(payload: PromoteNextStepsPayload) -> str:
    reason = str(payload.get("reason") or "").strip() or "blocked"
    header = f"Promotion blocked ({reason})."
    steps = payload.get("nextSteps") or []
    return "\n".join([header, format_steps_text(steps)]).strip()


__all__ = [
    "QANextStepsPayload",
    "BundleNextStepsPayload",
    "BundleReportsPayload",
    "PromoteNextStepsPayload",
    "NextStep",
    "build_qa_next_steps_payload",
    "format_qa_next_steps_text",
    "format_steps_text",
    "build_round_next_steps",
    "build_validate_next_steps_from_checklist",
    "build_bundle_next_steps_payload",
    "format_bundle_next_steps_text",
    "build_promote_next_steps_payload",
    "format_promote_next_steps_text",
]
