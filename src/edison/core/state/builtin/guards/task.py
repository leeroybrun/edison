"""Task-specific guard functions for state machine transitions.

All guards follow the FAIL-CLOSED principle:
- Return False if any required data is missing
- Return False if validation cannot be performed
- Only return True when all conditions are explicitly met
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def can_start_task(ctx: Mapping[str, Any]) -> bool:
    """Task can start only if claimed by current session.

    FAIL-CLOSED: Returns False if any required data is missing.

    Prerequisites:
    - Task must exist in context
    - Session must exist in context
    - Task must be claimed by the session (matching session_id)

    Args:
        ctx: Context with 'task' and 'session' dicts

    Returns:
        True if task is claimed by current session
    """
    task = ctx.get("task")
    session = ctx.get("session")

    if not isinstance(task, Mapping) or not isinstance(session, Mapping):
        return False  # FAIL-CLOSED: missing context

    task_session = task.get("session_id") or task.get("sessionId")
    session_id = session.get("id")

    if not task_session or not session_id:
        return False  # FAIL-CLOSED: missing IDs

    return str(task_session) == str(session_id)


def can_finish_task(ctx: Mapping[str, Any]) -> bool:
    """Task can finish only when Context7 + evidence requirements are satisfied.

    FAIL-CLOSED: Returns False if evidence is missing.

    Prerequisites:
    - Task ID must be in context (via 'task.id' or 'entity_id')
    - Context7 markers must exist for any detected packages (react, zod, etc.)
    - Implementation report must exist for the latest round
    - If evidence enforcement is enabled, required evidence files must exist

    Args:
        ctx: Context with task ID (via 'task' dict or 'entity_id') and optionally 'project_root'

    Returns:
        True if requirements are satisfied
    """
    # Try to get task_id from various context patterns
    task_id = None

    # Pattern 1: task dict with id
    task = ctx.get("task")
    if isinstance(task, Mapping):
        task_id = task.get("id")

    # Pattern 2: entity_id (from transition_entity)
    if not task_id:
        task_id = ctx.get("entity_id")

    if not task_id:
        return False  # FAIL-CLOSED: no task ID found

    # Get project_root from context if available (for isolated test environments)
    project_root = ctx.get("project_root")
    project_root_path: Path | None = None
    if isinstance(project_root, (str, Path)):
        try:
            project_root_path = Path(project_root).resolve()
        except Exception:
            project_root_path = None

    # Context7 enforcement (must surface a useful error message).
    try:
        session = ctx.get("session")
        session_dict = session if isinstance(session, Mapping) else None

        from edison.core.qa.context import detect_packages, missing_packages
        from edison.core.task.repository import TaskRepository

        task_repo = TaskRepository(project_root=project_root_path)
        task_path = task_repo._find_entity_path(str(task_id))  # type: ignore[attr-defined]
        if task_path:
            packages = detect_packages(Path(task_path), session_dict)  # type: ignore[arg-type]
            missing = missing_packages(str(task_id), packages)
            if missing:
                detected = ", ".join(sorted(packages)) if packages else "(none)"
                missing_s = ", ".join(missing)
                raise ValueError(
                    "Context7 evidence required "
                    f"(missing: {missing_s}; detected: {detected})"
                )
    except ValueError:
        raise
    except Exception as e:
        # FAIL-CLOSED: if Context7 validation can't run reliably, block completion,
        # but do so with a clear, actionable error.
        raise ValueError(f"Context7 validation failed: {e}") from e

    # Check implementation report exists
    try:
        from edison.core.qa.evidence import EvidenceService

        ev_svc = EvidenceService(str(task_id), project_root=project_root_path)
        latest = ev_svc.get_current_round()
        if latest is None:
            expected = ev_svc.get_round_dir(1) / ev_svc.implementation_filename
            raise ValueError(
                "Implementation report Markdown is required per round (no round-* evidence directory found).\n"
                f"Expected: {expected}\n"
                "Fix: run `edison session track start --task <task> --type implementation` to create the round + report."
            )
        report = ev_svc.read_implementation_report(latest)
        if not report:
            expected = ev_svc.get_round_dir(latest) / ev_svc.implementation_filename
            raise ValueError(
                "Implementation report Markdown is required per round.\n"
                f"Missing: {expected}\n"
                "Fix: run `edison session track start --task <task> --type implementation --round <N>`."
            )

        enforce = bool(ctx.get("enforce_evidence")) or bool(
            os.environ.get("ENFORCE_TASK_STATUS_EVIDENCE")
        )
        required: list[str] = []
        if enforce:
            from edison.core.qa.evidence.analysis import list_evidence_files
            from edison.core.qa.policy.resolver import ValidationPolicyResolver

            sid = str((session_dict or {}).get("id") or (session_dict or {}).get("sessionId") or "").strip() or None
            policy = ValidationPolicyResolver(project_root=project_root_path).resolve_for_task(
                str(task_id),
                session_id=sid,
            )
            required = list(policy.required_evidence or [])
            round_dir = ev_svc.get_round_dir(latest)
            files = {str(p.relative_to(round_dir)) for p in list_evidence_files(round_dir)}

            missing_files: list[str] = []
            for pattern in required:
                if not any(Path(name).match(pattern) for name in files):
                    missing_files.append(str(pattern))
            if missing_files:
                raise ValueError(
                    f"Missing evidence files in round-{latest}: {', '.join(missing_files)}"
                )

        # Optional TDD readiness gates (used by `edison task ready`).
        enforce_tdd = bool(ctx.get("enforce_tdd")) and not bool(
            str(os.environ.get("DISABLE_TDD_ENFORCEMENT", "")).strip()
        )
        if enforce_tdd:
            from edison.core.config.domains.tdd import TDDConfig
            from edison.core.qa.evidence.command_evidence import verify_command_evidence_hmac
            from edison.core.tdd.ready_gate import (
                run_verification_script,
                scan_for_blocked_test_tokens,
                validate_command_evidence_exit_codes,
                validate_tdd_evidence,
            )

            tdd_cfg = TDDConfig(repo_root=project_root_path)
            required_files = list(required or [])
            tdd_round_dir = ev_svc.get_round_dir(latest)

            # Exit code verification for command evidence (best-effort).
            if enforce and bool(tdd_cfg.require_evidence):
                validate_command_evidence_exit_codes(tdd_round_dir, required_files=required_files)

            # HMAC verification is enabled when a key is present.
            hmac_key = str(os.environ.get(tdd_cfg.hmac_key_env_var, "")).strip()
            if hmac_key:
                for name in required_files:
                    ok, msg = verify_command_evidence_hmac(tdd_round_dir / str(name), hmac_key=hmac_key)
                    if not ok:
                        raise ValueError(msg)

            # `.only` / focus token detection.
            roots: list[Path] = []
            if project_root_path is not None:
                roots.append(project_root_path)
            wt_raw = (session_dict or {}).get("git", {}).get("worktreePath") if session_dict else None
            try:
                wt = Path(str(wt_raw)).resolve() if wt_raw else None
            except Exception:
                wt = None
            if wt and wt.exists():
                roots.append(wt)

            hits = scan_for_blocked_test_tokens(
                roots=roots,
                file_globs=tdd_cfg.test_file_globs,
                blocked_tokens=tdd_cfg.blocked_test_tokens,
            )
            if hits:
                path, token = hits[0]
                raise ValueError(f"Blocked test token {token!r} detected in {path}")

            # Optional project verification script (e.g., coverage thresholds).
            script_rel = tdd_cfg.verification_script
            if script_rel and project_root_path is not None:
                script_path = Path(script_rel)
                if not script_path.is_absolute():
                    script_path = (project_root_path / script_path).resolve()
                if script_path.exists() and os.access(script_path, os.X_OK):
                    cp = run_verification_script(script_path, cwd=project_root_path)
                    if cp.returncode != 0:
                        out = ((cp.stdout or "") + "\n" + (cp.stderr or "")).strip()
                        raise ValueError(
                            "TDD verification script failed (coverage gate).\n"
                            f"Script: {script_path}\n"
                            f"{out}".strip()
                        )

            # Validate session-scoped TDD evidence when present.
            sid = str(ctx.get("session_id") or (session_dict or {}).get("id") or "").strip()
            if sid and project_root_path is not None:
                validate_tdd_evidence(
                    project_root=project_root_path,
                    session_id=sid,
                    task_id=str(task_id),
                    enforce_red_green_refactor=bool(tdd_cfg.enforce_red_green_refactor),
                    worktree_path=wt,
                )

        return True
    except Exception:
        raise

    return False  # pragma: no cover


def has_implementation_report(ctx: Mapping[str, Any]) -> bool:
    """Check if implementation report exists for the task.

    Alias for can_finish_task with clearer semantic meaning.

    Args:
        ctx: Context with 'task' dict containing 'id'

    Returns:
        True if implementation report exists
    """
    return can_finish_task(ctx)


def requires_rollback_reason(ctx: Mapping[str, Any]) -> bool:
    """Check if task has rollback reason for done->wip transition.

    FAIL-CLOSED: Returns False if rollback reason is missing.

    Args:
        ctx: Context with 'task' dict

    Returns:
        True if rollback reason is present
    """
    task = ctx.get("task")
    if not isinstance(task, Mapping):
        return False  # FAIL-CLOSED

    reason = task.get("rollbackReason") or task.get("rollback_reason") or ""
    return bool(str(reason).strip())
