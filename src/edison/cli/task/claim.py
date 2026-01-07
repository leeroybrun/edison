"""
Edison task claim command.

SUMMARY: Claim task or QA into a session with guarded status updates
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from edison.cli import (
    OutputFormatter,
    add_json_flag,
    add_repo_root_flag,
    detect_record_type,
    format_display_path,
    get_repo_root,
    resolve_existing_task_id,
    resolve_session_id,
)

SUMMARY = "Claim task or QA into a session with guarded status updates"

def _is_truthy_env(name: str) -> bool:
    return str(os.environ.get(name, "")).strip().lower() in {"1", "true", "yes", "on"}


def _detect_strict_guard_wrappers(project_root: Path) -> bool:
    scripts_dir = project_root / "scripts"
    return (
        (scripts_dir / "implementation" / "validate").exists()
        and (scripts_dir / "tasks" / "ensure-followups").exists()
    )


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "record_id",
        help="Task or QA identifier (e.g., 150-wave1-auth-gate)",
    )
    parser.add_argument(
        "--session",
        help="Session to claim into (auto-detects if not provided)",
    )
    parser.add_argument(
        "--type",
        choices=["task", "qa"],
        help="Record type (auto-detects if not provided)",
    )
    parser.add_argument(
        "--owner",
        help="Owner name to stamp (defaults to git user or system user)",
    )
    parser.add_argument(
        "--status",
        type=str,
        default=None,
        help="Target status after claim (default: semantic wip). Validated against config at runtime.",
    )
    parser.add_argument(
        "--takeover",
        action="store_true",
        help="(Deprecated) Alias for --reclaim (tasks only).",
    )
    parser.add_argument(
        "--reclaim",
        action="store_true",
        help="Allow reclaiming a task already claimed by another session (tasks only).",
    )
    parser.add_argument(
        "--reason",
        type=str,
        default=None,
        help="Optional reason for reclaim/takeover (recorded in session history).",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Claim task - delegates to core library using entity-based API."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    project_root: Path | None = None
    session_id: str | None = None
    record_type: str | None = None
    record_id: str | None = None

    try:
        # Resolve project root
        project_root = get_repo_root(args)
        strict_wrappers = _detect_strict_guard_wrappers(project_root)
        debug_wrappers = _is_truthy_env("project_DEBUG_WRAPPERS")

        # Lazy imports to keep CLI startup fast.
        from edison.core.config.domains.project import ProjectConfig
        from edison.core.config.domains.workflow import WorkflowConfig
        from edison.core.qa.workflow.repository import QARepository
        from edison.core.task import TaskQAWorkflow, normalize_record_id

        # Determine record type (from arg or auto-detect)
        record_type = args.type or detect_record_type(args.record_id)

        # Normalize/resolve record id.
        #
        # Tasks frequently use shorthand like "12007" and expect it to resolve to
        # "12007-wave8-...". QA ids are already derived from full task ids and are
        # not eligible for shorthand resolution here.
        if record_type == "task":
            record_id = resolve_existing_task_id(project_root=project_root, raw_task_id=str(args.record_id))
        else:
            record_id = normalize_record_id(record_type, args.record_id)

        # Get or auto-detect session
        session_id = resolve_session_id(
            project_root=project_root,
            explicit=args.session,
            required=True,
        )
        assert session_id is not None

        # Get owner (for stamping when missing)
        owner = args.owner or ProjectConfig(repo_root=project_root).get_owner_or_user()

        # Use TaskQAWorkflow for claiming (handles state transition and persistence)
        workflow = TaskQAWorkflow(project_root=project_root)

        workflow_cfg = WorkflowConfig(repo_root=project_root)
        domain = "qa" if record_type == "qa" else "task"
        default_state = workflow_cfg.get_semantic_state(domain, "wip")
        target_state = str(args.status).strip() if args.status else default_state

        valid_states = workflow_cfg.get_states(domain)
        if target_state not in valid_states:
            raise ValueError(
                f"Invalid status for {domain}: {target_state}. Valid values: {', '.join(valid_states)}"
            )

        if record_type == "task":
            reclaim = bool(getattr(args, "reclaim", False) or getattr(args, "takeover", False))
            reclaim_reason = str(getattr(args, "reason", "") or "").strip() or None

            qa_repo = QARepository(project_root=project_root)
            qa_id = f"{record_id}-qa"
            qa_existed_before = qa_repo.get(qa_id) is not None

            # Pre-flight: if reclaiming from a non-expired session, surface a warning.
            if reclaim:
                try:
                    existing = workflow.task_repo.get(record_id)
                    other_sid = str(getattr(existing, "session_id", "") or "").strip() if existing else ""
                    if other_sid and other_sid != session_id:
                        from edison.core.config.domains.session import SessionConfig
                        from edison.core.session.lifecycle.recovery import is_session_expired
                        from edison.core.session.persistence.repository import SessionRepository
                        from edison.core.utils.time import parse_iso8601, utc_now

                        if not is_session_expired(other_sid, project_root=project_root):
                            sess_repo = SessionRepository(project_root=project_root)
                            other = sess_repo.get(other_sid)
                            meta = (other.to_dict().get("meta") if other else {}) or {}
                            now = utc_now(repo_root=project_root)
                            ref = None
                            for key in ("lastActive", "claimedAt", "createdAt"):
                                raw = str(meta.get(key) or "").strip()
                                if not raw:
                                    continue
                                try:
                                    ref = parse_iso8601(raw, repo_root=project_root)
                                    break
                                except Exception:
                                    continue
                            age_hours = None
                            if ref is not None:
                                age_hours = max(0.0, (now - ref).total_seconds() / 3600.0)
                            timeout_hours = int(SessionConfig(repo_root=project_root).get_recovery_config().get("timeoutHours") or 0)
                            if age_hours is not None and not formatter.json_mode:
                                print(
                                    f"Warning: reclaiming task {record_id} from session '{other_sid}' even though session is only "
                                    f"{age_hours:.2f} hours old (timeout {timeout_hours}h).",
                                    file=sys.stderr,
                                )
                except Exception:
                    pass

            # Claim task using entity-based workflow
            task_entity = workflow.claim_task(
                record_id,
                session_id,
                owner=owner,
                takeover=reclaim,
                takeover_reason=reclaim_reason,
            )

            # Optional post-claim transition to requested state
            if target_state != task_entity.state:
                task_entity = workflow.task_repo.transition(
                    task_entity.id,
                    target_state,
                    context={
                        "task": task_entity.to_dict(),
                        "session": {"id": session_id},
                        "session_id": session_id,
                        "entity_type": "task",
                        "entity_id": task_entity.id,
                    },
                    reason="cli-claim-command",
                )

            effective_owner = (task_entity.metadata.created_by or owner or "").strip() or "_unassigned_"

            from edison.core.qa.evidence import EvidenceService
            from edison.core.qa.workflow.next_steps import (
                build_qa_next_steps_payload,
                format_qa_next_steps_text,
            )

            task_path = workflow.task_repo.get_path(task_entity.id)
            task_path_display = format_display_path(project_root=project_root, path=task_path)

            evidence_root = EvidenceService(task_entity.id, project_root=project_root).get_evidence_root()
            evidence_root_display = format_display_path(project_root=project_root, path=evidence_root)

            qa = qa_repo.get(qa_id)
            qa_path_display = ""
            qa_state = "unknown"
            if qa:
                qa_state = str(qa.state)
                qa_path = qa_repo.get_path(qa_id)
                qa_path_display = format_display_path(project_root=project_root, path=qa_path)

            qa_payload = build_qa_next_steps_payload(
                qa_id=qa_id,
                qa_state=qa_state,
                qa_path=qa_path_display,
                created=not qa_existed_before,
            )

            if formatter.json_mode:
                out = {
                    "status": "claimed",
                    "record_id": record_id,
                    "record_type": record_type,
                    "session_id": session_id,
                    "owner": effective_owner,
                    "state": task_entity.state,
                    "strict_wrappers": strict_wrappers,
                    "path": task_path_display,
                    "evidenceRoot": evidence_root_display,
                }
                out.update(qa_payload)
                formatter.json_output(out)
            else:
                formatter.text(
                    f"Claimed task {record_id}\n"
                    f"Session: {session_id}\n"
                    f"Owner: {effective_owner}\n"
                    f"Status: {task_entity.state}\n"
                    f"Path: {task_path_display}\n"
                    f"Evidence: {evidence_root_display}"
                    + (f"\nStrict Wrappers → {'yes' if strict_wrappers else 'no'}" if debug_wrappers else "")
                )
                formatter.text("")
                formatter.text(format_qa_next_steps_text(qa_payload))
        else:
            qa_repo = QARepository(project_root=project_root)
            qa = qa_repo.get(record_id)
            if not qa:
                raise ValueError(f"QA record not found: {record_id}")

            # Transition QA into semantic wip on claim.
            wip_state = workflow_cfg.get_semantic_state("qa", "wip")

            def _mutate_claimed(q: Any) -> None:
                q.session_id = session_id
                if owner and not (getattr(q, "validator_owner", "") or "").strip():
                    q.validator_owner = owner
                if owner and not (getattr(getattr(q, "metadata", None), "created_by", "") or "").strip():
                    q.metadata.created_by = owner

            qa = qa_repo.transition(
                record_id,
                wip_state,
                context={
                    "qa": qa.to_dict(),
                    "session": {"id": session_id},
                    "session_id": session_id,
                    "entity_type": "qa",
                    "entity_id": record_id,
                },
                reason="cli-claim-command",
                mutate=_mutate_claimed,
            )

            # Optional post-claim transition to requested state
            if target_state != qa.state:
                qa = qa_repo.transition(
                    record_id,
                    target_state,
                    context={
                        "qa": qa.to_dict(),
                        "session": {"id": session_id},
                        "session_id": session_id,
                        "entity_type": "qa",
                        "entity_id": record_id,
                    },
                    reason="cli-claim-command",
                    mutate=_mutate_claimed,
                )

            effective_owner = (getattr(qa, "validator_owner", None) or getattr(getattr(qa, "metadata", None), "created_by", None) or owner or "").strip() or "_unassigned_"

            from edison.core.qa.evidence import EvidenceService

            qa_path = qa_repo.get_path(record_id)
            qa_path_display = format_display_path(project_root=project_root, path=qa_path)

            evidence_root_display = ""
            task_id = str(getattr(qa, "task_id", "") or "").strip()
            if task_id:
                evidence_root = EvidenceService(task_id, project_root=project_root).get_evidence_root()
                evidence_root_display = format_display_path(project_root=project_root, path=evidence_root)

            formatter.json_output({
                "status": "claimed",
                "record_id": record_id,
                "record_type": record_type,
                "session_id": session_id,
                "owner": effective_owner,
                "state": qa.state,
                "strict_wrappers": strict_wrappers,
                "path": qa_path_display,
                "evidenceRoot": evidence_root_display,
            }) if formatter.json_mode else formatter.text(
                f"Claimed QA {record_id}\n"
                f"Session: {session_id}\n"
                f"Owner: {effective_owner}\n"
                f"Status: {qa.state}\n"
                f"Path: {qa_path_display}"
                + (f"\nEvidence: {evidence_root_display}" if evidence_root_display else "")
                + (f"\nStrict Wrappers → {'yes' if strict_wrappers else 'no'}" if debug_wrappers else "")
            )

        return 0

    except Exception as e:
        extra: dict[str, Any] = {}

        # When a task claim fails due to dependency blocking, surface blockers inline
        # so the operator/agent doesn't have to run a second command to understand why.
        try:
            if record_type == "task" and project_root is not None and record_id:
                from edison.core.task.readiness import TaskReadinessEvaluator

                evaluator = TaskReadinessEvaluator(project_root=project_root)
                readiness = evaluator.evaluate_task(record_id, session_id=session_id)
                if readiness.blocked_by:
                    extra.update(readiness.to_blocked_list_dict())
        except Exception:
            pass

        if not formatter.json_mode and extra.get("blockedBy"):
            try:
                formatter.text("")
                formatter.text("Blocked by unmet dependencies:")
                for b in extra.get("blockedBy", []):
                    dep = str(b.get("dependencyId") or "").strip()
                    reason = str(b.get("reason") or "").strip()
                    sid = str(b.get("dependencySessionId") or "").strip()
                    suffix = f" (session {sid})" if sid else ""
                    formatter.text(f"  - {dep}: {reason}{suffix}")
            except Exception:
                pass

        formatter.error(e, error_code="claim_error", data=extra or None)
        return 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
