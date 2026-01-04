"""Session close preflight checklist engine.

This checklist is designed to answer "Can I close this session?" deterministically,
with actionable remediation commands. It is reused by:
- `edison session next` (when approaching close),
- `edison session verify --phase closing` (human output).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from edison.core.utils.paths import PathResolver
from edison.core.workflow.checklists.task_start import ChecklistItem


class SessionClosePreflightChecklistEngine:
    kind: str = "session_close_preflight"

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or PathResolver.resolve_project_root()

    def compute(self, *, session_id: str) -> dict[str, Any]:
        items: list[ChecklistItem] = []

        preset_name, preset_item = self._build_session_close_preset_item()
        items.append(preset_item)

        # Closing set is deterministic: all session tasks in semantic task.done.
        from edison.core.config.domains.workflow import WorkflowConfig
        from edison.core.qa.workflow.repository import QARepository
        from edison.core.task.repository import TaskRepository

        wf = WorkflowConfig(repo_root=self.project_root)
        task_done = wf.get_semantic_state("task", "done")
        qa_done = wf.get_semantic_state("qa", "done")
        qa_validated = wf.get_semantic_state("qa", "validated")
        qa_ready = {qa_done, qa_validated}

        task_repo = TaskRepository(project_root=self.project_root)
        qa_repo = QARepository(project_root=self.project_root)
        session_tasks = task_repo.find_by_session(session_id)

        done_tasks = [t for t in session_tasks if t and t.state == task_done]

        if not done_tasks:
            items.append(
                ChecklistItem(
                    id="closing-set",
                    severity="info",
                    title="Closing Set (Done Tasks)",
                    rationale="No tasks in task.done for this session; nothing is gated on session close checks yet.",
                    status="ok",
                    evidence_paths=[],
                    suggested_commands=[],
                )
            )
            has_blockers = any(i.severity == "blocker" and i.status != "ok" for i in items)
            return {
                "kind": self.kind,
                "sessionId": session_id,
                "closePreset": preset_name,
                "items": [i.to_dict() for i in items],
                "hasBlockers": has_blockers,
            }

        items.append(
            ChecklistItem(
                id="closing-set",
                severity="info",
                title="Closing Set (Done Tasks)",
                rationale=f"{len(done_tasks)} task(s) are in task.done and must be covered by session-close requirements.",
                status="ok",
                evidence_paths=[],
                suggested_commands=[],
            )
        )

        # ------------------------------------------------------------------
        # QA readiness for done tasks
        # ------------------------------------------------------------------
        missing_qa: list[str] = []
        for t in done_tasks:
            qa_id = f"{t.id}-qa"
            try:
                p = qa_repo.get_path(qa_id)
                if p.parent.name not in qa_ready:
                    missing_qa.append(t.id)
            except FileNotFoundError:
                missing_qa.append(t.id)

        if missing_qa:
            items.append(
                ChecklistItem(
                    id="qa-ready",
                    severity="blocker",
                    title="QA Ready for Done Tasks",
                    rationale=f"QA must be qa.done/qa.validated for tasks in task.done. Missing or not ready: {', '.join(sorted(missing_qa)[:5])}"
                    + (" (+more)" if len(missing_qa) > 5 else ""),
                    status="missing",
                    evidence_paths=[],
                    suggested_commands=[f"edison qa promote {tid} --status done" for tid in sorted(missing_qa)[:3]],
                )
            )
        else:
            items.append(
                ChecklistItem(
                    id="qa-ready",
                    severity="info",
                    title="QA Ready for Done Tasks",
                    rationale="All done tasks have QA in qa.done/qa.validated.",
                    status="ok",
                    evidence_paths=[],
                    suggested_commands=[],
                )
            )

        # ------------------------------------------------------------------
        # Bundle summary approval + preset match
        # ------------------------------------------------------------------
        from edison.core.qa.evidence.service import EvidenceService
        from edison.core.qa.bundler.cluster import select_cluster

        missing_bundle: list[str] = []
        not_approved: list[str] = []
        wrong_preset: list[str] = []
        roots_to_fix: dict[str, set[str]] = {}

        for t in done_tasks:
            ev = EvidenceService(t.id, project_root=self.project_root)
            bundle = ev.read_bundle() or {}
            if not bundle:
                missing_bundle.append(t.id)
            elif not bool(bundle.get("approved")):
                not_approved.append(t.id)
            elif preset_name:
                found = str(bundle.get("preset") or "").strip()
                if found != preset_name:
                    wrong_preset.append(t.id)

            if preset_name and (t.id in set(missing_bundle + not_approved + wrong_preset)):
                cluster = select_cluster(str(t.id), scope="bundle", project_root=self.project_root)
                roots_to_fix.setdefault(cluster.root_task_id, set()).add(t.id)

        if missing_bundle or not_approved or wrong_preset:
            problems: list[str] = []
            if missing_bundle:
                problems.append(f"missing bundle summary: {len(missing_bundle)}")
            if not_approved:
                problems.append(f"not approved: {len(not_approved)}")
            if wrong_preset:
                problems.append(f"wrong preset: {len(wrong_preset)}")

            suggested: list[str] = []
            if preset_name and roots_to_fix:
                for root in sorted(roots_to_fix.keys())[:3]:
                    suggested.append(f"edison qa validate {root} --scope bundle --preset {preset_name} --execute")
            elif roots_to_fix:
                for root in sorted(roots_to_fix.keys())[:3]:
                    suggested.append(f"edison qa validate {root} --scope bundle --execute")

            items.append(
                ChecklistItem(
                    id="bundle-summary",
                    severity="blocker",
                    title="Session-close Bundle Coverage",
                    rationale="; ".join(problems)
                    + (f". Session-close preset: {preset_name}." if preset_name else "."),
                    status="missing",
                    evidence_paths=[],
                    suggested_commands=suggested,
                )
            )
        else:
            items.append(
                ChecklistItem(
                    id="bundle-summary",
                    severity="info",
                    title="Session-close Bundle Coverage",
                    rationale="All done tasks have an approved bundle summary matching the session-close preset.",
                    status="ok",
                    evidence_paths=[],
                    suggested_commands=[],
                )
            )

        # ------------------------------------------------------------------
        # Session-close evidence commands (preset-driven)
        # ------------------------------------------------------------------
        items.append(self._build_session_close_evidence_item(session_id=session_id))

        has_blockers = any(i.severity == "blocker" and i.status != "ok" for i in items)
        return {
            "kind": self.kind,
            "sessionId": session_id,
            "closePreset": preset_name,
            "items": [i.to_dict() for i in items],
            "hasBlockers": has_blockers,
        }

    def _build_session_close_preset_item(self) -> tuple[str | None, ChecklistItem]:
        try:
            from edison.core.qa.policy.session_close import get_session_close_policy

            preset = str(get_session_close_policy(project_root=self.project_root).preset.name or "").strip()
            if not preset:
                raise ValueError("validation.sessionClose.preset resolved to empty")
            return (
                preset,
                ChecklistItem(
                    id="session-close-preset",
                    severity="info",
                    title="Session-close Preset",
                    rationale=f"Session close requires preset '{preset}' (config: validation.sessionClose.preset).",
                    status="ok",
                    evidence_paths=[],
                    suggested_commands=[],
                ),
            )
        except Exception as exc:
            return (
                None,
                ChecklistItem(
                    id="session-close-preset",
                    severity="blocker",
                    title="Session-close Preset",
                    rationale=f"Session close policy is not configured or invalid: {exc}",
                    status="invalid",
                    evidence_paths=[],
                    suggested_commands=[
                        "edison config show validation --format yaml",
                        "Define validation.sessionClose.preset and presets.<name> in config YAML.",
                    ],
                ),
            )

    def _build_session_close_evidence_item(self, *, session_id: str) -> ChecklistItem:
        try:
            from edison.core.qa.evidence.command_evidence import parse_command_evidence
            from edison.core.qa.evidence.service import EvidenceService
            from edison.core.qa.policy.session_close import get_session_close_policy
            from edison.core.task.repository import TaskRepository

            policy = get_session_close_policy(project_root=self.project_root)
            required = [str(x).strip() for x in (policy.required_evidence or []) if str(x).strip()]
            if not required:
                return ChecklistItem(
                    id="session-close-evidence",
                    severity="info",
                    title="Session-close Evidence",
                    rationale="No session-close command evidence is required by policy.",
                    status="ok",
                    evidence_paths=[],
                    suggested_commands=[],
                )

            tasks = TaskRepository(project_root=self.project_root).find_by_session(session_id)
            missing: list[str] = []
            for filename in required:
                ok = False
                for t in tasks:
                    rd = EvidenceService(t.id, project_root=self.project_root).get_current_round_dir()
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
                    missing.append(filename)

            if not missing:
                return ChecklistItem(
                    id="session-close-evidence",
                    severity="info",
                    title="Session-close Evidence",
                    rationale="All session-close required command evidence is present (exitCode=0).",
                    status="ok",
                    evidence_paths=[],
                    suggested_commands=[],
                )

            anchor = sorted([t.id for t in tasks if t and t.id])[:1]
            anchor_id = anchor[0] if anchor else "<task-id>"
            return ChecklistItem(
                id="session-close-evidence",
                severity="blocker",
                title="Session-close Evidence",
                rationale=f"Missing session-close evidence: {', '.join(missing)}",
                status="missing",
                evidence_paths=[],
                suggested_commands=[
                    f"edison evidence capture {anchor_id} --session-close",
                    f"edison evidence status {anchor_id}",
                ],
            )
        except Exception:
            # Fail-open: checklist should not crash the workflow.
            return ChecklistItem(
                id="session-close-evidence",
                severity="warning",
                title="Session-close Evidence",
                rationale="Unable to compute session-close evidence status (config or evidence error).",
                status="unknown",
                evidence_paths=[],
                suggested_commands=["edison config show validation --format yaml"],
            )


__all__ = ["SessionClosePreflightChecklistEngine"]

