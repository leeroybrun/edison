"""QA validate preflight checklist engine.

This checklist is designed to surface the highest-leverage prerequisites
BEFORE running `edison qa validate`, without turning normal development into
a constant blocker.

It focuses on:
- evidence round selection / availability
- preset-driven required evidence patterns (policy resolver)
- Context7 marker status for the roster being validated
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from edison.core.utils.paths import PathResolver
from edison.core.workflow.checklists.task_start import ChecklistItem


class QAValidatePreflightChecklistEngine:
    kind: str = "qa_validate_preflight"

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or PathResolver.resolve_project_root()

    def _display_path(self, path: Path) -> str:
        """Render a stable, repo-root-relative path when possible."""
        try:
            return str(path.relative_to(self.project_root))
        except Exception:
            return str(path)

    def compute(
        self,
        *,
        task_id: str,
        session_id: str | None,
        roster: dict[str, Any],
        round_num: int | None,
        will_execute: bool,
        root_task_id: str | None = None,
        scope_used: str | None = None,
        cluster_task_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        items: list[ChecklistItem] = []

        requested_task_id = str(task_id)
        root = str(root_task_id or task_id)

        scope: str | None = str(scope_used) if scope_used is not None else None
        cluster_size: int | None = len(cluster_task_ids) if cluster_task_ids is not None else None
        if scope is None or cluster_size is None:
            try:
                from edison.core.qa.bundler import build_validation_manifest

                manifest = build_validation_manifest(
                    requested_task_id,
                    project_root=self.project_root,
                    session_id=session_id,
                )
                scope = str(manifest.get("scope") or "") or scope
                root = str(manifest.get("rootTask") or root)
                tasks = manifest.get("tasks") if isinstance(manifest, dict) else None
                if cluster_size is None and isinstance(tasks, list):
                    cluster_size = len(tasks)
            except Exception:
                pass

        scope = scope or "hierarchy"
        cluster_size = int(cluster_size or 1)

        items.append(
            self._build_scope_preset_item(
                requested_task_id=requested_task_id,
                root_task_id=root,
                scope_used=scope,
                cluster_size=cluster_size,
                roster=roster,
            )
        )
        items.append(self._build_engine_availability_item(roster=roster))
        items.append(
            self._build_evidence_round_item(
                task_id=root,
                round_num=round_num,
                will_execute=will_execute,
            )
        )
        items.append(
            self._build_required_evidence_item(
                task_id=root,
                round_num=round_num,
                will_execute=will_execute,
            )
        )
        items.append(
            self._build_context7_item(
                task_id=root,
                session_id=session_id,
                roster=roster,
                round_num=round_num,
                will_execute=will_execute,
            )
        )

        has_blockers = any(i.severity == "blocker" and i.status != "ok" for i in items)
        return {
            "kind": self.kind,
            "taskId": requested_task_id,
            "rootTask": root,
            "scope": scope,
            "clusterSize": cluster_size,
            "items": [i.to_dict() for i in items],
            "hasBlockers": has_blockers,
        }

    def _resolve_target_round(
        self,
        *,
        task_id: str,
        round_num: int | None,
    ) -> tuple[int | None, Path | None, int | None]:
        """Resolve (target_round, target_round_dir, current_round)."""
        from edison.core.qa.evidence import EvidenceService

        ev = EvidenceService(task_id, project_root=self.project_root)
        current = ev.get_current_round()

        if round_num is not None:
            target = int(round_num)
            return target, ev.get_round_dir(target), current

        if current is None:
            return None, None, None

        return int(current), ev.get_round_dir(int(current)), current

    def _build_evidence_round_item(
        self,
        *,
        task_id: str,
        round_num: int | None,
        will_execute: bool,
    ) -> ChecklistItem:
        target, target_dir, _current = self._resolve_target_round(task_id=task_id, round_num=round_num)

        if target is None:
            sev = "blocker" if will_execute else "info"
            rationale = "No evidence round exists yet."
            if will_execute:
                rationale += " `qa validate --execute` does not create rounds; prepare a round first."
            return ChecklistItem(
                id="evidence-round",
                severity=sev,
                title="Evidence Round Not Initialized",
                rationale=rationale,
                status="missing",
                evidence_paths=[],
                suggested_commands=[f"edison qa round prepare {task_id}"],
            )

        assert target_dir is not None
        if target_dir.exists():
            return ChecklistItem(
                id="evidence-round",
                severity="info",
                title="Evidence Round Selected",
                rationale=f"Using evidence round {target} at {self._display_path(target_dir)}.",
                status="ok",
                evidence_paths=[self._display_path(target_dir)],
                suggested_commands=[],
            )

        # Target doesn't exist yet (typically an explicit round override).
        sev = "blocker" if will_execute else "warning"
        rationale = f"Evidence round {target} does not exist yet at {self._display_path(target_dir)}."
        return ChecklistItem(
            id="evidence-round",
            severity=sev,
            title="Evidence Round Will Be Created",
            rationale=rationale,
            status="missing",
            evidence_paths=[self._display_path(target_dir)],
            suggested_commands=[f"edison qa round prepare {task_id}"],
        )

    def _build_required_evidence_item(
        self,
        *,
        task_id: str,
        round_num: int | None,
        will_execute: bool,
    ) -> ChecklistItem:
        from edison.core.qa.policy.resolver import ValidationPolicyResolver

        target, target_dir, _current = self._resolve_target_round(task_id=task_id, round_num=round_num)
        policy = ValidationPolicyResolver(project_root=self.project_root).resolve_for_task(task_id)
        required = [str(x).strip() for x in (policy.required_evidence or []) if str(x).strip()]

        if not required:
            return ChecklistItem(
                id="required-evidence",
                severity="info",
                title="Required Evidence (Preset)",
                rationale="No required evidence patterns configured for this task/preset.",
                status="ok",
                evidence_paths=[],
                suggested_commands=[],
            )

        if target is None or target_dir is None:
            # No rounds yet.
            sev = "warning" if will_execute else "info"
            rationale = "Required evidence patterns exist, but no round directory exists yet."
            return ChecklistItem(
                id="required-evidence",
                severity=sev,
                title="Required Evidence (Preset)",
                rationale=rationale,
                status="unknown",
                evidence_paths=[],
                suggested_commands=[
                    f"edison qa round prepare {task_id}",
                    f"edison evidence capture {task_id}",
                ],
            )

        if not target_dir.exists():
            sev = "warning" if will_execute else "warning"
            return ChecklistItem(
                id="required-evidence",
                severity=sev,
                title="Required Evidence (Preset)",
                rationale=f"Evidence round {target} does not exist yet, so required evidence cannot be present.",
                status="missing",
                evidence_paths=[self._display_path(target_dir)],
                suggested_commands=[f"edison qa round prepare {task_id}"],
            )

        from edison.core.qa.evidence.analysis import list_evidence_files

        try:
            files = {str(p.relative_to(target_dir)) for p in list_evidence_files(target_dir)}
        except Exception:
            files = {p.name for p in target_dir.iterdir() if p.is_file()}

        missing: list[str] = []
        for pattern in required:
            if not any(Path(name).match(str(pattern)) for name in files):
                missing.append(str(pattern))

        if not missing:
            return ChecklistItem(
                id="required-evidence",
                severity="info",
                title="Required Evidence (Preset)",
                rationale=f"All required evidence patterns are present in round-{target}.",
                status="ok",
                evidence_paths=[self._display_path(target_dir)],
                suggested_commands=[],
            )

        sev = "warning"
        suggested = [f"edison evidence capture {task_id}"]
        if will_execute:
            suggested.append(f"edison qa validate {task_id} --execute")
        return ChecklistItem(
            id="required-evidence",
            severity=sev,
            title="Required Evidence (Preset) Missing",
            rationale=f"Missing evidence patterns in round-{target}: {', '.join(missing)}",
            status="missing",
            evidence_paths=[self._display_path(target_dir)],
            suggested_commands=suggested,
        )

    def _build_context7_item(
        self,
        *,
        task_id: str,
        session_id: str | None,
        roster: dict[str, Any],
        round_num: int | None,
        will_execute: bool,
    ) -> ChecklistItem:
        _ = session_id  # reserved for future (task-scoped detection work)

        validators_in_roster = (
            (roster.get("alwaysRequired") or [])
            + (roster.get("triggeredBlocking") or [])
            + (roster.get("triggeredOptional") or [])
        )
        required_pkgs: set[str] = set()
        for v in validators_in_roster:
            if not isinstance(v, dict):
                continue
            if v.get("context7Required") and isinstance(v.get("context7Packages"), list):
                required_pkgs |= {
                    str(p).strip()
                    for p in v.get("context7Packages")
                    if p and str(p).strip() and str(p).strip() != "+"
                }

        if not required_pkgs:
            return ChecklistItem(
                id="context7",
                severity="info",
                title="Context7",
                rationale="No Context7 markers required for this validator roster.",
                status="ok",
                evidence_paths=[],
                suggested_commands=[],
            )

        target, target_dir, _current = self._resolve_target_round(task_id=task_id, round_num=round_num)
        if target is None:
            return ChecklistItem(
                id="context7",
                severity="warning",
                title="Context7 Markers Missing (No Round Directory Yet)",
                rationale=(
                    f"Context7 markers are required for: {', '.join(sorted(required_pkgs))}. "
                    "No evidence round exists yet."
                ),
                status="missing",
                evidence_paths=[],
                suggested_commands=[
                    f"edison qa round prepare {task_id}",
                    "edison evidence context7 template <package>",
                ],
            )

        assert target_dir is not None

        if not target_dir.exists():
            rationale = (
                f"Context7 markers are required for: {', '.join(sorted(required_pkgs))}. "
                f"Evidence round {target} does not exist yet."
            )
            if will_execute:
                rationale += " This run will create the round, but markers will still be missing until saved."
            return ChecklistItem(
                id="context7",
                severity="warning",
                title="Context7 Markers Missing (No Round Directory Yet)",
                rationale=rationale,
                status="missing",
                evidence_paths=[self._display_path(target_dir)],
                suggested_commands=[
                    f"edison evidence init {task_id}",
                    "edison evidence context7 template <package>",
                ],
            )

        from edison.core.qa.context.context7 import classify_packages

        classification = classify_packages(target_dir, sorted(required_pkgs))
        missing = classification.get("missing", []) or []
        invalid = classification.get("invalid", []) or []
        valid = classification.get("valid", []) or []

        suggested: list[str] = []
        problematic = set(missing)
        for inv in invalid:
            if isinstance(inv, dict) and inv.get("package"):
                problematic.add(str(inv["package"]))
        for pkg in sorted(problematic):
            suggested.append(f"edison evidence context7 template {pkg}")
            suggested.append(
                f"edison evidence context7 save {task_id} {pkg} --library-id /<org>/{pkg} --topics <topics>"
            )

        if missing or invalid:
            rationale_parts: list[str] = []
            if missing:
                rationale_parts.append(f"Missing: {', '.join([str(x) for x in missing])}")
            if invalid:
                invalid_desc = [
                    f"{inv.get('package')} (missing: {', '.join(inv.get('missing_fields', []) or [])})"
                    for inv in invalid
                    if isinstance(inv, dict)
                ]
                if invalid_desc:
                    rationale_parts.append(f"Invalid: {', '.join(invalid_desc)}")
            return ChecklistItem(
                id="context7",
                severity="warning",
                title="Context7 Markers Required",
                rationale="; ".join(rationale_parts),
                status="missing" if missing else "invalid",
                evidence_paths=[self._display_path(target_dir)],
                suggested_commands=suggested,
            )

        return ChecklistItem(
            id="context7",
            severity="info",
            title="Context7 Markers Present",
            rationale=f"Valid: {', '.join([str(x) for x in valid])}",
            status="ok",
            evidence_paths=[self._display_path(target_dir)],
            suggested_commands=[],
        )

    def _build_scope_preset_item(
        self,
        *,
        requested_task_id: str,
        root_task_id: str,
        scope_used: str,
        cluster_size: int,
        roster: dict[str, Any],
    ) -> ChecklistItem:
        preset = str(roster.get("preset") or "").strip() or "standard"

        root_suffix = ""
        if str(root_task_id).strip() != str(requested_task_id).strip():
            root_suffix = f"; requested: {requested_task_id}"
        rationale = (
            f"Scope: {scope_used} (tasks={cluster_size}); preset: {preset}; root: {root_task_id}{root_suffix}."
        )
        return ChecklistItem(
            id="scope-preset",
            severity="info",
            title="Scope + Preset",
            rationale=rationale,
            status="ok",
            evidence_paths=[],
            suggested_commands=[],
        )

    def _build_engine_availability_item(self, *, roster: dict[str, Any]) -> ChecklistItem:
        validators_in_roster = (
            (roster.get("alwaysRequired") or [])
            + (roster.get("triggeredBlocking") or [])
            + (roster.get("triggeredOptional") or [])
        )

        blocking_ids: list[str] = []
        for v in validators_in_roster:
            if not isinstance(v, dict):
                continue
            if not v.get("blocking"):
                continue
            vid = str(v.get("id") or "").strip()
            if vid:
                blocking_ids.append(vid)

        if not blocking_ids:
            return ChecklistItem(
                id="engine-availability",
                severity="info",
                title="Engine Availability",
                rationale="No blocking validators selected; engine availability is informational only.",
                status="ok",
                evidence_paths=[],
                suggested_commands=[],
            )

        try:
            from edison.core.qa.engines import ValidationExecutor

            executor = ValidationExecutor(project_root=self.project_root)
        except Exception as exc:
            return ChecklistItem(
                id="engine-availability",
                severity="warning",
                title="Engine Availability",
                rationale=f"Could not initialize validation executor to check CLI availability: {exc}",
                status="unknown",
                evidence_paths=[],
                suggested_commands=[],
            )

        problems: list[str] = []
        disabled_by_config = False
        binary_missing = False
        for vid in blocking_ids:
            details = executor.can_execute_validator_details(vid)
            can = bool(details.get("canExecute", False))
            if can:
                continue

            reason = str(details.get("reason") or "unknown")
            engine = str(details.get("engine") or "unknown")
            if reason == "disabled_by_config":
                disabled_by_config = True
            if reason == "binary_missing":
                binary_missing = True
            problems.append(f"{vid} (engine={engine}, reason={reason})")

        if not problems:
            return ChecklistItem(
                id="engine-availability",
                severity="info",
                title="Engine Availability",
                rationale=f"All blocking validators can execute via CLI (count={len(blocking_ids)}).",
                status="ok",
                evidence_paths=[],
                suggested_commands=[],
            )

        suggested: list[str] = []
        if disabled_by_config:
            suggested.append("edison config show orchestration --format yaml")
        if binary_missing:
            suggested.append("Verify required validator CLIs are installed and on PATH")

        return ChecklistItem(
            id="engine-availability",
            severity="warning",
            title="Engine Availability",
            rationale="Delegation-only blocking validators (CLI unavailable): "
            + ", ".join(problems[:5])
            + (f" (+{len(problems) - 5} more)" if len(problems) > 5 else ""),
            status="missing",
            evidence_paths=[],
            suggested_commands=suggested,
        )


__all__ = ["QAValidatePreflightChecklistEngine"]
