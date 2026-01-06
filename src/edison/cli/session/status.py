"""
Edison session status command.

SUMMARY: Display current session status
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
    resolve_session_id,
)

SUMMARY = "Display current session status"


def _list_session_scoped_records(root: Path) -> dict[str, dict[str, str]]:
    """Return a lightweight record listing keyed by record id.

    This is derived from the directory layout (SSoT) and is intentionally
    independent from any session.json indexing.
    """
    out: dict[str, dict[str, str]] = {}
    if not root.exists():
        return out

    for state_dir in sorted([p for p in root.iterdir() if p.is_dir()], key=lambda p: p.name):
        state = state_dir.name
        for md in sorted(state_dir.glob("*.md")):
            rid = md.stem
            if not rid:
                continue
            out[rid] = {"state": state, "path": str(md)}

    return out


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "session_id",
        nargs="?",
        help="Session ID (optional, uses current session if not specified)",
    )
    parser.add_argument(
        "--status",
        help="Transition session to this state (if omitted, shows current status)",
    )
    parser.add_argument(
        "--reason",
        help="Reason for transition (recorded in session history)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview transition without making changes",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Display or transition session status."""

    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        from edison.core.session.persistence.repository import SessionRepository

        project_root = get_repo_root(args)
        session_id = resolve_session_id(
            project_root=project_root,
            explicit=args.session_id,
            required=True,
        )

        repo = SessionRepository(project_root=project_root)
        entity = repo.get(session_id)
        if not entity:
            raise ValueError(f"Session not found: {session_id}")

        current_state = str(entity.state or "")

        if getattr(args, "status", None):
            # Validate status against config-driven states (runtime validation for fast CLI startup)
            from edison.core.config.domains.workflow import WorkflowConfig

            cfg = WorkflowConfig(repo_root=project_root)
            valid = cfg.get_states("session")
            if args.status not in valid:
                raise ValueError(
                    f"Invalid status for session: {args.status}. Valid values: {', '.join(valid)}"
                )

            if args.dry_run:
                from edison.core.state.transitions import validate_transition

                session_payload = entity.to_dict()
                if args.status == "blocked" and getattr(args, "reason", None):
                    session_payload = {**session_payload, "blocker_reason": args.reason}

                context = {
                    "session_id": session_id,
                    "session": session_payload,
                    "entity_type": "session",
                    "entity_id": session_id,
                }
                is_valid, msg = validate_transition(
                    "session",
                    current_state,
                    args.status,
                    context=context,
                    repo_root=project_root,
                )
                formatter.json_output({
                    "dry_run": True,
                    "session_id": session_id,
                    "current_status": current_state,
                    "target_status": args.status,
                    "valid": is_valid,
                    "message": msg,
                }) if formatter.json_mode else formatter.text(
                    f"Transition {current_state} -> {args.status}: "
                    + ("ALLOWED" if is_valid else f"BLOCKED - {msg}")
                )
                return 0 if is_valid else 1

            session_payload = entity.to_dict()
            if args.status == "blocked" and getattr(args, "reason", None):
                session_payload = {**session_payload, "blocker_reason": args.reason}

            context = {
                "session_id": session_id,
                "session": session_payload,
                "entity_type": "session",
                "entity_id": session_id,
            }
            repo.transition(
                session_id,
                args.status,
                context=context,
                reason=getattr(args, "reason", None) or "cli-session-status",
            )

            payload = {"status": "transitioned", "session_id": session_id, "from": current_state, "to": args.status}
            formatter.json_output(payload) if formatter.json_mode else formatter.text(
                f"Transitioned session {session_id}: {current_state} -> {args.status}"
            )
            return 0

        session = entity.to_dict()
        try:
            session_dir = repo.get_path(session_id).parent
            session["tasks"] = _list_session_scoped_records(session_dir / "tasks")
            session["qa"] = _list_session_scoped_records(session_dir / "qa")
        except Exception:
            # Fail-open: status output should never fail due to directory scanning.
            pass

        if formatter.json_mode:
            formatter.json_output(session)
        else:
            formatter.text(f"Session: {session_id}")
            state = session.get("state") or session.get("meta", {}).get("status", "unknown")
            formatter.text(f"Status: {state}")
            task = session.get("task") or session.get("meta", {}).get("task")
            if task:
                formatter.text(f"Task: {task}")
            owner = session.get("owner") or session.get("meta", {}).get("owner")
            if owner:
                formatter.text(f"Owner: {owner}")

            # Archived worktrees section (deterministic newest-first ordering).
            try:
                from edison.core.config.domains.session import SessionConfig
                from edison.core.config.domains.project import ProjectConfig

                wt_cfg = SessionConfig(repo_root=project_root).get_worktree_config()
                raw = wt_cfg.get("archiveDirectory")
                substituted = ProjectConfig(repo_root=project_root).substitute_project_tokens(str(raw or ""))
                archive_dir = Path(substituted)
                if not archive_dir.is_absolute():
                    archive_dir = (project_root / archive_dir).resolve()

                formatter.text("\n## Archived Worktrees")
                if archive_dir.exists():
                    dirs = [p for p in archive_dir.iterdir() if p.is_dir()]
                    dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                    for p in dirs:
                        formatter.text(f"- {p}")
            except Exception:
                # Status output must never fail due to archival listing.
                pass

        return 0

    except Exception as e:
        formatter.error(e, error_code="status_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
