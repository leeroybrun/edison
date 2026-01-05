"""Session start/resume checklist engine.

This checklist is designed to surface the highest-leverage "don't get lost"
requirements at the start of a session, without duplicating constitution text
or hook injection logic.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from edison.core.utils.paths import PathResolver
from edison.core.workflow.checklists.task_start import ChecklistItem


class SessionStartChecklistEngine:
    kind: str = "session_start"

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or PathResolver.resolve_project_root()

    def compute(self, *, session_id: str, cwd: Path | None = None) -> dict[str, Any]:
        items: list[ChecklistItem] = []

        items.append(self._build_worktree_item(session_id=session_id, cwd=cwd))
        items.append(self._build_constitution_item())
        items.append(self._build_delegation_gate_item())

        has_blockers = any(i.severity == "blocker" and i.status != "ok" for i in items)
        return {
            "kind": self.kind,
            "sessionId": session_id,
            "items": [i.to_dict() for i in items],
            "hasBlockers": has_blockers,
        }

    def _build_worktree_item(self, *, session_id: str, cwd: Path | None) -> ChecklistItem:
        expected = ""
        try:
            from edison.core.session.persistence.repository import SessionRepository

            sess = SessionRepository(project_root=self.project_root).get(session_id)
            if sess:
                data = sess.to_dict()
                expected = str(((data.get("git") or {}) if isinstance(data, dict) else {}).get("worktreePath") or "").strip()
        except Exception:
            expected = ""

        if not expected:
            return ChecklistItem(
                id="worktree",
                severity="warning",
                title="Worktree Confinement",
                rationale="Session has no recorded worktree; ensure you're in the intended repo/worktree before implementing.",
                status="unknown",
                evidence_paths=[],
                suggested_commands=[],
            )

        current = (cwd or Path.cwd()).resolve()
        expected_path = Path(expected).expanduser().resolve()
        ok = False
        try:
            ok = current.is_relative_to(expected_path)
        except Exception:
            ok = str(current).startswith(str(expected_path))

        if ok:
            return ChecklistItem(
                id="worktree",
                severity="blocker",
                title="Worktree Confinement",
                rationale="You're operating inside the session worktree.",
                status="ok",
                evidence_paths=[str(expected_path)],
                suggested_commands=[],
            )

        return ChecklistItem(
            id="worktree",
            severity="blocker",
            title="Wrong Directory (Not in Session Worktree)",
            rationale=f"Current cwd is {current}, but session worktree is {expected_path}.",
            status="invalid",
            evidence_paths=[str(expected_path)],
            suggested_commands=[f"cd {expected_path}"],
        )

    def _build_constitution_item(self) -> ChecklistItem:
        return ChecklistItem(
            id="constitution",
            severity="info",
            title="Re-read Constitution (if needed)",
            rationale="If context was compacted or you are resuming, re-read the role constitution before implementing.",
            status="ok",
            evidence_paths=[],
            suggested_commands=[
                "edison read ORCHESTRATOR --type constitutions",
                "edison read AGENTS --type constitutions",
                "edison read VALIDATORS --type constitutions",
            ],
        )

    def _build_delegation_gate_item(self) -> ChecklistItem:
        return ChecklistItem(
            id="delegation-gate",
            severity="warning",
            title="Delegation-First Loop Driver",
            rationale="Use `edison session next` as the loop driver before starting work to see task checklists and next actions.",
            status="ok",
            evidence_paths=[],
            suggested_commands=["edison session next"],
        )


__all__ = ["SessionStartChecklistEngine"]

