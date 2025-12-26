"""Structured session insights extraction (memory pipeline input).

This module produces a small, deterministic structured record that can be
persisted to providers like Graphiti and/or the file-store fallback.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def extract_session_insights_v1(*, project_root: Path, session_id: str) -> dict[str, Any]:
    """Extract a structured insights record for a session (v1)."""
    project_root = Path(project_root).expanduser().resolve()

    tasks_completed: list[str] = []
    qas_completed: list[str] = []
    evidence_summaries: list[dict[str, Any]] = []
    what_worked: list[str] = []
    what_failed: list[str] = []
    recommendations: list[str] = []
    files_understood: dict[str, str] = {}

    try:
        from edison.core.config.domains.workflow import WorkflowConfig
        from edison.core.task.repository import TaskRepository

        wf = WorkflowConfig(repo_root=project_root)
        task_done = str(wf.get_semantic_state("task", "done"))
        task_validated = str(wf.get_semantic_state("task", "validated"))
        task_completed_states = {task_done, task_validated}

        task_repo = TaskRepository(project_root=project_root)
        session_tasks = task_repo.find_by_session(str(session_id))
        tasks_completed = sorted({t.id for t in session_tasks if str(t.state) in task_completed_states})
        for tid in tasks_completed:
            what_worked.append(f"Completed task: {tid}")
    except Exception:
        tasks_completed = []

    try:
        from edison.core.config.domains.workflow import WorkflowConfig
        from edison.core.qa.workflow.repository import QARepository

        wf = WorkflowConfig(repo_root=project_root)
        qa_done = str(wf.get_semantic_state("qa", "done"))
        qa_validated = str(wf.get_semantic_state("qa", "validated"))
        qa_completed_states = {qa_done, qa_validated}

        qa_repo = QARepository(project_root=project_root)
        session_qas = qa_repo.find_by_session(str(session_id))
        qas_completed = sorted({q.id for q in session_qas if str(q.state) in qa_completed_states})
    except Exception:
        qas_completed = []

    # Evidence summaries (implementation + validator reports) for completed tasks.
    for task_id in list(tasks_completed):
        try:
            from edison.core.qa.evidence.report_io import read_structured_report
            from edison.core.qa.evidence.service import EvidenceService

            ev = EvidenceService(task_id, project_root=project_root)
            round_num = ev.get_current_round()
            impl = ev.read_implementation_report(round_num)
            validators: list[dict[str, Any]] = []

            if round_num is not None:
                for p in ev.list_validator_reports(round_num=round_num):
                    data = read_structured_report(p)
                    if not data:
                        continue
                    vid = str(data.get("validatorId") or data.get("validator_id") or "")
                    strengths = data.get("strengths", []) if isinstance(data.get("strengths", []), list) else []
                    findings = data.get("findings", []) if isinstance(data.get("findings", []), list) else []
                    summary = str(data.get("summary") or "").strip()

                    for s in strengths:
                        if isinstance(s, str) and s.strip():
                            what_worked.append(s.strip())

                    for f in findings:
                        if not isinstance(f, dict):
                            continue
                        desc = f.get("description")
                        if isinstance(desc, str) and desc.strip():
                            what_failed.append(desc.strip())
                        loc = f.get("location")
                        if isinstance(loc, str) and loc.strip():
                            file_hint = loc.split(":")[0].strip()
                            if file_hint:
                                files_understood.setdefault(file_hint, "Referenced in validator findings")

                    if str(data.get("verdict") or "").strip() in {"reject", "blocked"}:
                        what_failed.append(f"Validator {vid} verdict: {data.get('verdict')}")

                    validators.append(
                        {
                            "validatorId": vid,
                            "verdict": data.get("verdict"),
                            "strengths": strengths,
                            "findings": findings,
                            "summary": summary,
                            "followUpTasks": data.get("followUpTasks", []),
                        }
                    )

            followups: list[str] = []
            impl_summary: dict[str, Any] | None = None
            if isinstance(impl, dict) and impl:
                for it in impl.get("followUpTasks", []) or []:
                    title = it.get("title") if isinstance(it, dict) else None
                    if isinstance(title, str) and title.strip():
                        followups.append(title.strip())
                    if isinstance(it, dict):
                        for k in ("files", "relatedFiles"):
                            raw_files = it.get(k)
                            if isinstance(raw_files, list):
                                for fp in raw_files:
                                    if isinstance(fp, str) and fp.strip():
                                        files_understood.setdefault(fp.strip(), "Referenced in follow-up context")

                for b in impl.get("blockers", []) or []:
                    if isinstance(b, dict) and isinstance(b.get("description"), str) and b["description"].strip():
                        what_failed.append(b["description"].strip())

                impl_summary = {
                    "completionStatus": impl.get("completionStatus"),
                    "blockers": [
                        b.get("description")
                        for b in (impl.get("blockers") or [])
                        if isinstance(b, dict) and b.get("description")
                    ],
                    "followUpTasks": [
                        t.get("title")
                        for t in (impl.get("followUpTasks") or [])
                        if isinstance(t, dict) and t.get("title")
                    ],
                    "notesForValidator": impl.get("notesForValidator"),
                    "primaryModel": impl.get("primaryModel"),
                    "round": impl.get("round"),
                }

            for v in validators:
                for it in v.get("followUpTasks", []) or []:
                    if isinstance(it, dict) and isinstance(it.get("title"), str) and it["title"].strip():
                        followups.append(it["title"].strip())

            for title in followups:
                recommendations.append(title)

            evidence_summaries.append(
                {
                    "taskId": task_id,
                    "round": round_num,
                    "implementation": impl_summary,
                    "validators": validators,
                }
            )
        except Exception:
            continue

    # Session planner recommendations (best-effort).
    try:
        from edison.core.session.next.compute import compute_next

        nxt = compute_next(str(session_id), scope=None, limit=0)
        for rec in nxt.get("recommendations", []) if isinstance(nxt, dict) else []:
            if isinstance(rec, str) and rec.strip():
                recommendations.append(rec.strip())
    except Exception:
        pass

    def _dedupe(items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for it in items:
            s = str(it).strip()
            if not s or s in seen:
                continue
            seen.add(s)
            out.append(s)
        return out

    what_worked = _dedupe(what_worked)
    what_failed = _dedupe(what_failed)
    recommendations = _dedupe(recommendations)

    return {
        "schema": "session-insights-v1",
        "sessionId": str(session_id),
        "tasksCompleted": tasks_completed,
        "qasCompleted": qas_completed,
        "evidenceSummaries": evidence_summaries,
        "whatWorked": what_worked,
        "whatFailed": what_failed,
        "recommendationsForNextSession": recommendations,
        "discoveries": {
            "files_understood": dict(sorted(files_understood.items())),
            "patterns_found": [],
            "gotchas_encountered": [],
        },
    }


__all__ = ["extract_session_insights_v1"]
