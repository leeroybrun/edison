"""
Edison session list command.

SUMMARY: List sessions across states
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root

SUMMARY = "List sessions across states"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--status",
        help="Filter by session status/state (accepts semantic state or directory alias)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Include terminal/final states (e.g., validated/archived)",
    )
    parser.add_argument(
        "--owner",
        help="Filter by session owner",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    try:
        project_root = get_repo_root(args)

        from edison.core.config.domains.session import SessionConfig
        from edison.core.config.domains.workflow import WorkflowConfig
        from edison.core.session.persistence.repository import SessionRepository
        from edison.cli import resolve_session_id

        repo = SessionRepository(project_root=project_root)

        include_all = bool(getattr(args, "all", False))

        if getattr(args, "status", None):
            cfg = SessionConfig(repo_root=project_root)
            states_map = cfg.get_session_states()
            valid = sorted(set(states_map.keys()) | set(states_map.values()))
            if args.status not in valid:
                raise ValueError(f"Invalid session status: {args.status}. Valid values: {', '.join(valid)}")
            sessions = repo.list_by_state(str(args.status))
        else:
            sessions = repo.get_all()

        if not getattr(args, "status", None) and not include_all:
            cfg = WorkflowConfig(repo_root=project_root)
            final_states = set(cfg.get_final_states("session"))
            sessions = [s for s in sessions if s.state not in final_states]

        if getattr(args, "owner", None):
            owner = str(args.owner)
            sessions = [s for s in sessions if str(getattr(s, "owner", "") or "") == owner]

        current_session_id = resolve_session_id(project_root=project_root, explicit=None, required=False)
        if current_session_id:
            # Prefer showing the current session first when listing in-session,
            # even if ordering would otherwise be arbitrary.
            for idx, s in enumerate(list(sessions)):
                if s.id == current_session_id:
                    sessions.insert(0, sessions.pop(idx))
                    break

        if formatter.json_mode:
            records = []
            for s in sessions:
                try:
                    p = repo.get_path(s.id)
                    path_str = str(p.relative_to(project_root)) if p.is_relative_to(project_root) else str(p)
                except Exception:
                    path_str = ""

                worktree_path = None
                try:
                    worktree_path = getattr(getattr(s, "git", None), "worktree_path", None)
                except Exception:
                    worktree_path = None

                records.append(
                    {
                        "id": s.id,
                        "state": s.state,
                        "owner": getattr(s, "owner", None),
                        "worktreePath": worktree_path,
                        "path": path_str,
                    }
                )
            formatter.json_output(records)
            return 0

        if not sessions:
            text = "No sessions found"
            if not getattr(args, "status", None) and not include_all:
                cfg = WorkflowConfig(repo_root=project_root)
                text += (
                    f"\n  (excluding terminal states: {', '.join(cfg.get_final_states('session'))})"
                    "\n  Tip: pass --all to include terminal sessions."
                )
            formatter.text(text)
            return 0

        lines = []
        for s in sessions:
            suffix_parts = []
            if getattr(s, "owner", None):
                suffix_parts.append(f"owner={s.owner}")
            wt = None
            try:
                wt = getattr(getattr(s, "git", None), "worktree_path", None)
            except Exception:
                wt = None
            if wt:
                suffix_parts.append(f"worktree={wt}")

            suffix = f" ({', '.join(suffix_parts)})" if suffix_parts else ""
            lines.append(f"  {s.id} [{s.state}]{suffix}")

        text = f"Found {len(sessions)} session(s):\n" + "\n".join(lines)
        if not getattr(args, "status", None) and not include_all:
            cfg = WorkflowConfig(repo_root=project_root)
            text += (
                f"\nNote: excluding terminal states ({', '.join(cfg.get_final_states('session'))}). "
                "Pass --all to include them."
            )
        formatter.text(text)
        return 0
    except Exception as exc:
        formatter.error(exc, error_code="session_list_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
