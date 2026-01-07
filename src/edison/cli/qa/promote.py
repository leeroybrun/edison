"""
Edison qa promote command.

SUMMARY: Promote QA brief between states with state-machine guard enforcement
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import (
    OutputFormatter,
    add_json_flag,
    add_repo_root_flag,
    get_repo_root,
    get_repository,
    resolve_existing_task_id,
)
from edison.core.qa import promoter, bundler
from edison.core.qa.evidence import EvidenceService, read_validator_reports
from edison.core.qa.workflow.next_steps import (
    build_promote_next_steps_payload,
    format_promote_next_steps_text,
)
from edison.core.state.transitions import validate_transition

SUMMARY = "Promote QA brief between states"

def _parse_transition_spec(spec: str) -> tuple[str, str] | None:
    s = str(spec or "").strip()
    if not s or "→" not in s:
        return None
    left, right = s.split("→", 1)
    left = left.strip()
    right = right.strip()
    if not left or not right:
        return None
    return (left, right)


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "task_id",
        help="Task identifier",
    )
    parser.add_argument(
        "--status",
        type=str,
        help="Target status to promote to",
    )
    parser.add_argument(
        "--session",
        type=str,
        help="Session ID for context",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview transition without making changes",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Promote QA brief with state-machine guard enforcement."""

    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)

        if not args.status:
            formatter.error("--status is required", error_code="missing_status")
            return 1

        # Validate status against config-driven QA states (runtime validation for fast CLI startup)
        from edison.core.config.domains.workflow import WorkflowConfig

        cfg = WorkflowConfig(repo_root=repo_root)
        valid = cfg.get_states("qa")
        if args.status not in valid:
            formatter.error(
                ValueError(f"Invalid status: {args.status}. Valid values: {', '.join(valid)}"),
                error_code="invalid_status",
            )
            return 1

        # Canonical ID semantics:
        # - CLI takes a task_id, but QA entity IDs are stored as "<task_id>-qa" (or "<task_id>.qa").
        raw_id = str(args.task_id)
        if raw_id.endswith("-qa") or raw_id.endswith(".qa"):
            task_id_token = raw_id[:-3]  # strip "-qa" or ".qa"
        else:
            task_id_token = raw_id

        task_id = resolve_existing_task_id(project_root=repo_root, raw_task_id=task_id_token)
        if task_id != task_id_token and not formatter.json_mode:
            print(f"Resolved task id '{task_id_token}' -> '{task_id}'", file=sys.stderr)

        if raw_id.endswith("-qa") or raw_id.endswith(".qa"):
            qa_id = f"{task_id}-qa"
        else:
            qa_id = f"{task_id}-qa"

        # Get QA entity to determine current state
        qa_repo = get_repository("qa", project_root=repo_root)
        qa_entity = qa_repo.get(qa_id)
        
        if not qa_entity:
            formatter.error(f"QA brief not found: {qa_id}", error_code="qa_not_found")
            return 1
        
        current_status = qa_entity.state
        
        # Get latest round using EvidenceService
        svc = EvidenceService(task_id, project_root=repo_root)
        round_num = svc.get_current_round()
        
        # Build context for guard evaluation
        context = {
            "task_id": task_id,
            "qa": {
                "id": qa_id,
                "task_id": task_id,
                "state": current_status,
            },
            "entity_type": "qa",
            "entity_id": qa_id,
        }
        if args.session:
            context["session_id"] = str(args.session)
            context["session"] = {"id": str(args.session)}
        
        # Add task context if available
        try:
            task_repo = get_repository("task", project_root=repo_root)
            task_entity = task_repo.get(task_id)
            if task_entity:
                context["task"] = {
                    "id": task_entity.id,
                    "status": task_entity.state,
                    "state": task_entity.state,
                    "session_id": task_entity.session_id,
                }
        except Exception:
            pass
        
        # Add validation results if available
        if round_num is not None:
            try:
                validator_data = read_validator_reports(task_id)
                context["validation_results"] = {
                    "round": round_num,
                    "reports": validator_data.get("reports", []),
                }
            except Exception:
                pass
        
        # Dry run - validate without execution
        if args.dry_run:
            is_valid, msg = validate_transition(
                "qa",
                current_status,
                args.status,
                context=context,
                repo_root=repo_root,
            )
            formatter.json_output({
                "dry_run": True,
                "task_id": task_id,
                "qa_id": qa_id,
                "current_status": current_status,
                "target_status": args.status,
                "valid": is_valid,
                "message": msg if not is_valid else "Transition allowed",
            }) if formatter.json_mode else formatter.text(
                f"Transition {current_status} -> {args.status}: {'ALLOWED' if is_valid else 'BLOCKED - ' + msg}"
            )
            return 0 if is_valid else 1
        
        # Additional check for validated state - bundle must be fresh
        validated_state = cfg.get_semantic_state("qa", "validated")
        if args.status == validated_state and round_num is not None:
            bundle_path = bundler.bundle_summary_path(task_id, round_num)
            reports = promoter.collect_validator_reports([task_id])
            task_files = promoter.collect_task_files([task_id], args.session)

            if promoter.should_revalidate_bundle(bundle_path, reports, task_files):
                payload = build_promote_next_steps_payload(
                    task_id=task_id,
                    target_status=str(args.status),
                    reason="revalidation_required",
                )
                formatter.error(
                    ValueError("Bundle is stale. Re-run validation before promoting to validated."),
                    error_code="revalidation_required",
                    data={"nextSteps": payload},
                )
                if not formatter.json_mode:
                    print(format_promote_next_steps_text(payload), file=sys.stderr)
                return 1

        # Execute the promotion with guard validation + action execution.
        old_state = qa_entity.state
        qa_entity = qa_repo.transition(
            qa_id,
            args.status,
            context=context,
            reason="cli-qa-promote",
        )

        # Lifecycle sync: when QA is approved (done → validated), also promote the
        # task (done → validated) according to workflow.validationLifecycle.onApprove.
        #
        # This keeps the filesystem state tree coherent with the configured lifecycle.
        task_sync = {"attempted": False, "promoted": False}
        task_sync_error: str | None = None
        try:
            on_approve = cfg.get_lifecycle_transition("onApprove") or {}
            qa_spec = _parse_transition_spec(str(on_approve.get("qaState") or ""))
            task_spec = _parse_transition_spec(str(on_approve.get("taskState") or ""))

            if qa_spec and task_spec and old_state == qa_spec[0] and str(args.status) == qa_spec[1]:
                task_sync["attempted"] = True

                task_repo = get_repository("task", project_root=repo_root)
                task_entity = task_repo.get(task_id)
                if not task_entity:
                    raise ValueError(f"Task not found: {task_id}")

                from_task, to_task = task_spec
                if task_entity.state == to_task:
                    task_sync["promoted"] = True
                elif task_entity.state != from_task:
                    raise ValueError(
                        "QA was promoted to validated, but task state is inconsistent.\n"
                        f"Task: {task_id}\n"
                        f"Expected task state: {from_task} (or already {to_task})\n"
                        f"Actual task state: {task_entity.state}"
                    )
                else:
                    task_context = dict(context)
                    task_context["entity_type"] = "task"
                    task_context["entity_id"] = task_id
                    task_repo.transition(
                        task_id,
                        to_task,
                        context=task_context,
                        reason="workflow.validationLifecycle.onApprove",
                    )
                    task_sync["promoted"] = True
        except Exception as e:
            task_sync_error = str(e)

        result = {
            "task_id": task_id,
            "qa_id": qa_id,
            "round": round_num,
            "old_status": old_state,
            "new_status": args.status,
            "promoted": True,
            "taskSync": task_sync,
        }

        # If QA promotion succeeded but task sync failed, return non-zero so
        # orchestrators/LLMs do not silently proceed with inconsistent state.
        if task_sync.get("attempted") and not task_sync.get("promoted"):
            raise RuntimeError(
                "QA was promoted, but task lifecycle sync failed.\n"
                f"Task: {task_id}\n"
                f"QA: {qa_id}\n"
                "Fix: run `edison task status <task-id> --status validated` (or the configured target state).\n"
                f"Details: {task_sync_error or 'unknown error'}"
            )

        formatter.json_output(result) if formatter.json_mode else formatter.text(
            f"Promoted {qa_id}: {old_state} -> {args.status}"
        )

        return 0

    except Exception as e:
        formatter.error(e, error_code="promote_error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
