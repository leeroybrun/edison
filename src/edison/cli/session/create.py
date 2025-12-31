"""
Edison session create command.

SUMMARY: Create a new Edison session
"""

from __future__ import annotations

import argparse
import os
import sys

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root
from edison.core.exceptions import SessionError
from edison.core.session import lifecycle as session_manager
from edison.core.session.core.id import validate_session_id
from edison.core.session.core.naming import generate_session_id

SUMMARY = "Create a new Edison session"


def _strip_seq_suffix(session_id: str) -> str:
    # Session ids are typically: {name}-pid-{pid}[-seq-{n}]
    # When auto-selecting a unique id, treat the base as the prefix without any seq suffix.
    import re

    m = re.match(r"^(?P<base>.+)-seq-\d+$", session_id)
    return m.group("base") if m else session_id


def _pick_next_available_session_id(*, repo_root: str, preferred: str) -> str:
    """Pick the next available session id by adding -seq-N when needed.

    This is only used when the session id was inferred (not explicitly provided).
    """
    from pathlib import Path

    from edison.core.session.persistence.repository import SessionRepository

    repo = SessionRepository(project_root=Path(repo_root))
    base = _strip_seq_suffix(preferred)

    # Treat the base as seq=0, then try seq=1.. until free.
    if not repo.exists(base):
        return base

    n = 1
    while True:
        candidate = f"{base}-seq-{n}"
        if not repo.exists(candidate):
            return candidate
        n += 1


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--session-id",
        "--id",
        dest="session_id",
        required=False,
        help="Session identifier (optional; if omitted, auto-inferred from topmost process + PID)",
    )
    parser.add_argument(
        "--owner",
        default="system",
        help="Session owner (default: system)",
    )
    parser.add_argument(
        "--mode",
        default="start",
        help="Session mode (default: start)",
    )
    parser.add_argument(
        "--no-worktree",
        action="store_true",
        help="Skip worktree creation",
    )
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install dependencies in worktree (if creating worktree)",
    )
    parser.add_argument(
        "--base-branch",
        "--branch",
        dest="base_branch",
        required=False,
        help="Base ref to branch from for the session worktree (overrides config)",
    )
    parser.add_argument(
        "--prompt",
        dest="start_prompt",
        required=False,
        help="Optional start prompt ID to print after creation (e.g. AUTO_NEXT). See `edison list --type start --format detail`.",
    )
    parser.add_argument(
        "--include-prompt-text",
        action="store_true",
        help="Include full start prompt text in --json output (can be large).",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def _emit_worktree_instructions(
    formatter: OutputFormatter,
    *,
    session_id: str,
    worktree_path: str | None,
) -> None:
    if not worktree_path:
        return
    formatter.text("")
    formatter.text("WORKTREE CONFINEMENT (CRITICAL)")
    formatter.text(f"  cd {worktree_path}")
    formatter.text(f"  export AGENTS_SESSION={session_id}")
    formatter.text(f"  export AGENTS_PROJECT_ROOT={worktree_path}")
    formatter.text("  Never run `git checkout` / `git switch` in the primary checkout.")
    formatter.text(
        "  Never run `git reset` / `git restore` / `git clean` unless explicitly requested."
    )
    formatter.text("  Do all code changes inside the session worktree directory only.")


def main(args: argparse.Namespace) -> int:
    """Create a new session - delegates to core library."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        # Honor --repo-root by making project root resolution deterministic for this process.
        # Core session lifecycle uses PathResolver internally (env/cwd based), so we set the
        # canonical env var used by PathResolver.
        repo_root = get_repo_root(args)
        os.environ["AGENTS_PROJECT_ROOT"] = str(repo_root)

        inferred = not bool(getattr(args, "session_id", None))
        raw = args.session_id or generate_session_id()
        session_id = validate_session_id(raw)

        # If the session id was inferred and already exists, auto-select a unique -seq-N.
        # Keep explicit --session-id collisions fail-closed.
        if inferred:
            try:
                session_id = _pick_next_available_session_id(
                    repo_root=str(repo_root),
                    preferred=session_id,
                )
            except Exception:
                # Best-effort: uniqueness selection should not prevent explicitly provided ids.
                pass

        # Determine worktree creation
        create_wt = not args.no_worktree
        install_deps = args.install_deps if args.install_deps else None

        # Create the session
        sess_path = session_manager.create_session(
            session_id=session_id,
            owner=args.owner,
            mode=args.mode,
            install_deps=install_deps,
            base_branch=getattr(args, "base_branch", None),
            create_wt=create_wt,
        )

        # Load session data for output
        session = session_manager.get_session(session_id)
        worktree_path = session.get("git", {}).get("worktreePath")

        # Get worktree pinning status (task 047)
        from pathlib import Path

        from edison.core.session.worktree.manager import (
            ensure_worktree_session_id_file,
            get_worktree_pinning_status,
        )

        # Even in --no-worktree mode, pin the current checkout so session context
        # can be auto-resolved without manual file edits.
        pinning_root = Path(worktree_path) if worktree_path else Path(repo_root)
        if not worktree_path:
            ensure_worktree_session_id_file(worktree_path=pinning_root, session_id=session_id)

        pinning_status = get_worktree_pinning_status(pinning_root, session_id)

        # NOTE: Orchestrator launch is handled by `edison orchestrator start`.
        # `edison session create` is intentionally limited to creating the session record (+ optional worktree).

        if formatter.json_mode:
            start_prompt_id = getattr(args, "start_prompt", None)
            prompt_text = None
            prompt_path = None
            if start_prompt_id:
                from edison.core.session.start_prompts import (
                    find_start_prompt_path,
                    read_start_prompt,
                )

                prompt_path = str(find_start_prompt_path(repo_root, start_prompt_id))
                if bool(getattr(args, "include_prompt_text", False)):
                    prompt_text = read_start_prompt(repo_root, start_prompt_id)
            output = {
                "status": "created",
                "session_id": session_id,
                "path": str(sess_path),
                "session": session,
                "startPromptId": start_prompt_id,
                "startPromptPath": prompt_path,
                "startPrompt": prompt_text,
                # Worktree pinning status (task 047)
                "sessionIdFilePath": pinning_status["sessionIdFilePath"],
                "worktreePinned": pinning_status["worktreePinned"],
            }
            formatter.json_output(output)
        else:
            formatter.text(f"✓ Created session: {session_id}")
            formatter.text(f"  Path: {sess_path}")
            formatter.text(f"  Owner: {args.owner}")
            formatter.text(f"  Mode: {args.mode}")
            if worktree_path:
                formatter.text(f"  Worktree: {worktree_path}")
            if session.get("git", {}).get("branchName"):
                formatter.text(f"  Branch: {session['git']['branchName']}")
            if session.get("git", {}).get("baseBranch"):
                formatter.text(f"  Base: {session['git']['baseBranch']}")

            # Show worktree pinning status (task 047)
            if pinning_status["worktreePinned"]:
                formatter.text(f"  Pinned: .session-id written to {pinning_status['sessionIdFilePath']}")
            elif worktree_path:
                formatter.text("  Pinned: No (worktree .session-id file not created)")

            _emit_worktree_instructions(
                formatter, session_id=session_id, worktree_path=worktree_path
            )

            if getattr(args, "start_prompt", None):
                from edison.core.session.start_prompts import read_start_prompt

                prompt_id = str(args.start_prompt)
                prompt_text = read_start_prompt(repo_root, prompt_id)
                formatter.text("")
                formatter.text(f"START PROMPT ({prompt_id})")
                formatter.text(prompt_text.rstrip())

        return 0

    except SessionError as e:
        formatter.error(e, error_code="session_error")
        return 1

    except Exception as e:
        formatter.error(e, error_code="error")
        return 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
