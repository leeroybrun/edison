"""Action generation and helper functions for session next computation.

Functions for building action recommendations and related task discovery.
"""
from __future__ import annotations

from typing import Any, Dict, List

from edison.core.session import manager as session_manager
from edison.core.qa.evidence import (
    missing_evidence_blockers,
    read_validator_jsons,
    load_impl_followups,
    load_bundle_followups,
    get_evidence_dir,
    get_latest_round,
    get_implementation_report_path,
)
from edison.core.session.next.utils import project_cfg_dir
from edison.core.file_io.utils import read_json_safe as io_read_json_safe
from edison.core import task


def infer_task_status(task_id: str) -> str:
    """Infer task status from filesystem location."""
    try:
        p = task.find_record(task_id, "task")
        return task.infer_status_from_path(p, "task") or "unknown"
    except FileNotFoundError:
        return "missing"


def infer_qa_status(task_id: str) -> str:
    """Infer QA status from filesystem location."""
    try:
        p = task.find_record(task_id, "qa")
        return task.infer_status_from_path(p, "qa") or "missing"
    except FileNotFoundError:
        return "missing"


def find_related_in_session(session_id: str, task_id: str) -> List[Dict[str, Any]]:
    """Find related tasks/QAs in session: parent, children, linked tasks.

    Helps orchestrator understand dependencies and context.
    """
    try:
        session = session_manager.get_session(session_id)
    except Exception:
        return []

    related = []
    task_data = session.get("tasks", {}).get(task_id, {})

    # Parent task
    parent_id = task_data.get("parentId")
    if parent_id:
        parent_status = infer_task_status(parent_id)
        parent_qa = infer_qa_status(parent_id)
        related.append({
            "relationship": "parent",
            "taskId": parent_id,
            "taskStatus": parent_status,
            "qaStatus": parent_qa,
            "note": f"This task is a follow-up to {parent_id}",
        })

    # Child tasks
    for child_id in task_data.get("childIds", []):
        child_status = infer_task_status(child_id)
        child_qa = infer_qa_status(child_id)
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
                sib_status = infer_task_status(tid)
                sib_qa = infer_qa_status(tid)
                related.append({
                    "relationship": "sibling",
                    "taskId": tid,
                    "taskStatus": sib_status,
                    "qaStatus": sib_qa,
                    "note": f"Sibling task (same parent {parent_id})",
                })

    return related


def build_reports_missing(session: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build reportsMissing list for visibility.

    Args:
        session: Session dictionary with tasks

    Returns:
        List of missing report entries
    """
    reports_missing: List[Dict[str, Any]] = []

    for task_id, task_entry in session.get("tasks", {}).items():
        # Validators JSON expected when QA is wip/todo
        qstat = infer_qa_status(task_id)
        if qstat in {"wip", "todo"}:
            v = read_validator_jsons(task_id)
            have = {r.get("validatorId") for r in v.get("reports", [])}
            # Derive expected blocking IDs from validators config
            try:
                cfg = io_read_json_safe(project_cfg_dir()/"validators"/"config.json")
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
            ev_root = get_evidence_dir(task_id)
            latest_round = get_latest_round(task_id)
            if latest_round is not None:
                impl_report = get_implementation_report_path(task_id, latest_round)
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
                    return io_read_json_safe(project_cfg_dir()/"validators"/"config.json")
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
                ev_root = get_evidence_dir(task_id)
                latest_round = get_latest_round(task_id)
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

    return reports_missing
