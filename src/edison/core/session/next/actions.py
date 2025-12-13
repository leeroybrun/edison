"""Action generation and helper functions for session next computation.

Functions for building action recommendations and related task discovery.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from edison.core.qa.evidence import (
    EvidenceService,
    load_bundle_followups,  # noqa: F401 - re-exported for compute.py
    load_impl_followups,  # noqa: F401 - re-exported for compute.py
    missing_evidence_blockers,  # noqa: F401 - re-exported for compute.py
    read_validator_jsons,  # noqa: F401 - re-exported for compute.py
)
from edison.core.session.next.utils import project_cfg_dir
from edison.core.task import TaskRepository, safe_relative
from edison.core.utils.io import read_json as io_read_json
from edison.core.utils.patterns import matches_any_pattern

if TYPE_CHECKING:
    pass


def infer_task_status(task_id: str) -> str:
    """Infer task status from filesystem location."""
    try:
        task_repo = TaskRepository()
        p = task_repo.get_path(task_id)
        return p.parent.name or "unknown"
    except FileNotFoundError:
        return "missing"


def infer_qa_status(task_id: str) -> str:
    """Infer QA status from filesystem location."""
    # Lazy import to avoid circular dependency
    from edison.core.qa.workflow.repository import QARepository
    try:
        qa_repo = QARepository()
        p = qa_repo.get_path(task_id)
        return p.parent.name or "missing"
    except FileNotFoundError:
        return "missing"


def find_related_in_session(session_id: str, task_id: str) -> list[dict[str, Any]]:
    """Find related tasks/QAs in session: parent, children, linked tasks.

    Uses TaskRepository (task files) as the single source of truth for relationships.
    Session ID is used to filter tasks to the session context.
    """
    task_repo = TaskRepository()
    
    # Get the task to find its relationships
    task = task_repo.get(task_id)
    if not task:
        return []

    related = []

    # Parent task (from task.parent_id field in task file)
    if task.parent_id:
        parent_status = infer_task_status(task.parent_id)
        parent_qa = infer_qa_status(task.parent_id)
        related.append({
            "relationship": "parent",
            "taskId": task.parent_id,
            "taskStatus": parent_status,
            "qaStatus": parent_qa,
            "note": f"This task is a follow-up to {task.parent_id}",
        })

    # Child tasks (from task.child_ids field in task file)
    for child_id in task.child_ids:
        child_status = infer_task_status(child_id)
        child_qa = infer_qa_status(child_id)
        related.append({
            "relationship": "child",
            "taskId": child_id,
            "taskStatus": child_status,
            "qaStatus": child_qa,
            "note": f"Follow-up task spawned from {task_id}",
        })

    # Sibling tasks (other children of same parent)
    if task.parent_id:
        parent_task = task_repo.get(task.parent_id)
        if parent_task:
            for sibling_id in parent_task.child_ids:
                if sibling_id != task_id:
                    sib_status = infer_task_status(sibling_id)
                    sib_qa = infer_qa_status(sibling_id)
                    related.append({
                        "relationship": "sibling",
                        "taskId": sibling_id,
                        "taskStatus": sib_status,
                        "qaStatus": sib_qa,
                        "note": f"Sibling task (same parent {task.parent_id})",
                    })

    return related


def build_reports_missing(session: dict[str, Any]) -> list[dict[str, Any]]:
    """Build reportsMissing list for visibility.

    Uses TaskRepository to find tasks in the session (by session_id).
    Task files are the single source of truth for task data.

    Args:
        session: Session dictionary (used to get session_id)

    Returns:
        List of missing report entries
    """
    from edison.core.config.domains.workflow import WorkflowConfig
    workflow_cfg = WorkflowConfig()

    # Get QA states from config
    qa_wip = workflow_cfg.get_semantic_state("qa", "wip")
    qa_todo = workflow_cfg.get_semantic_state("qa", "todo")
    qa_active_states = {qa_wip, qa_todo}

    reports_missing: list[dict[str, Any]] = []

    # Get tasks from TaskRepository instead of session JSON
    task_repo = TaskRepository()
    session_id = session.get("id") or session.get("meta", {}).get("sessionId")
    
    # Find tasks belonging to this session
    if session_id:
        session_tasks = task_repo.find_by_session(session_id)
    else:
        # Fallback: get all tasks (shouldn't happen in normal usage)
        session_tasks = task_repo.get_all()
    
    for task in session_tasks:
        task_id = task.id
        # Validators JSON expected when QA is wip/todo
        qstat = infer_qa_status(task_id)
        if qstat in qa_active_states:
            v = read_validator_jsons(task_id)
            have = {r.get("validatorId") for r in v.get("reports", [])}
            # Derive expected blocking IDs from validators config using QAConfig
            try:
                from edison.core.config.domains.qa import QAConfig
                qa_cfg = QAConfig()
                validators = qa_cfg.get_validators()
                need = [
                    vid for vid, cfg in validators.items()
                    if cfg.get("always_run") or cfg.get("blocking", True)
                ]
                for vid in need:
                    if vid not in have:
                        reports_missing.append({
                            "taskId": task_id,
                            "type": "validator",
                            "validatorId": vid,
                            "suggested": ["(re)run validator wave and write JSON per schema", f"edison qa promote --task {task_id} --to wip"],
                        })
            except Exception:
                pass

        # Implementation Report JSON required for ALL tasks
        try:
            ev_svc = EvidenceService(task_id)
            latest_round = ev_svc.get_current_round()
            if latest_round is not None:
                impl_data = ev_svc.read_implementation_report(latest_round)
                if not impl_data:  # Empty dict means report doesn't exist
                    # Use configured filename from EvidenceService
                    impl_filename = ev_svc.implementation_filename
                    impl_path = ev_svc.get_evidence_root() / f"round-{latest_round}" / impl_filename
                    rel_path = safe_relative(impl_path)
                    reports_missing.append({
                        "taskId": task_id,
                        "type": "implementation",
                        "path": rel_path,
                        "suggested": [
                            "Write Implementation Report JSON per schema",
                            f"edison implementation validate {rel_path}",
                        ],
                    })
        except Exception:
            pass

        # Context7 markers expected for post-training packages used by this task
        try:
            # Load triggers from context7 config domain (not hardcoded)
            from edison.core.config.domains.context7 import Context7Config

            def _load_cfg():
                try:
                    return io_read_json(project_cfg_dir()/"validators"/"config.json")
                except Exception:
                    return {}

            def _files_for_task(tid: str) -> list[str]:
                try:
                    task_repo = TaskRepository()
                    p = task_repo.get_path(tid)
                    txt = p.read_text(errors="ignore")
                except FileNotFoundError:
                    return []
                files: list[str] = []
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

            def _matches(file_path: str, pkg: str, triggers: dict[str, list[str]]) -> bool:
                """Match file path against package triggers from config."""
                return matches_any_pattern(file_path, triggers.get(pkg, []))

            # Load triggers from config instead of hardcoding
            ctx7_config = Context7Config()
            triggers = ctx7_config.triggers  # From context7.yaml

            cfg = _load_cfg()
            pkgs = list((cfg.get("postTrainingPackages") or {}).keys())
            files = _files_for_task(task_id)
            used = {pkg for pkg in pkgs for f in files if _matches(f, pkg, triggers)}
            if used:
                ev_svc_ctx7 = EvidenceService(task_id)
                ev_root = ev_svc_ctx7.get_evidence_root()
                latest_round_ctx7 = ev_svc_ctx7.get_current_round()
                latest = ev_root / f"round-{latest_round_ctx7}" if latest_round_ctx7 is not None else None
                missing_pkgs: list[str] = []
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

    return reports_missing
