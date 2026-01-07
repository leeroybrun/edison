"""
Edison session continuation show command.

SUMMARY: Show effective per-session continuation settings (defaults + override)
"""

from __future__ import annotations

import argparse
import sys

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root
from edison.core.config import ConfigManager
from edison.core.session.core.id import validate_session_id
from edison.core.session.persistence.repository import SessionRepository

from ._core import compute_continuation_view

SUMMARY = "Show effective per-session continuation settings (defaults + override)"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("session_id", help="Session identifier")
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    try:
        project_root = get_repo_root(args)
        session_id = validate_session_id(str(args.session_id))

        repo = SessionRepository(project_root=project_root)
        session = repo.get(session_id)
        if not session:
            raise FileNotFoundError(f"Session {session_id} not found")

        cfg = ConfigManager(project_root).load_config(validate=False)
        cont_cfg = cfg.get("continuation") or {}

        meta_cont = None
        if isinstance(session.meta_extra, dict):
            raw = session.meta_extra.get("continuation")
            meta_cont = raw if isinstance(raw, dict) else None

        view = compute_continuation_view(continuation_cfg=cont_cfg if isinstance(cont_cfg, dict) else {}, meta_continuation=meta_cont)

        if formatter.json_mode:
            formatter.json_output(
                {
                    "sessionId": session_id,
                    "defaults": view.defaults,
                    "override": view.override,
                    "effective": view.effective,
                }
            )
        else:
            formatter.text(f"Session: {session_id}")
            formatter.text(f"Effective mode: {view.effective.get('mode')}")
            formatter.text(f"Effective enabled: {view.effective.get('enabled')}")
            budgets = (view.effective.get('budgets') or {})
            formatter.text(
                f"Budgets: maxIterations={budgets.get('maxIterations')} cooldownSeconds={budgets.get('cooldownSeconds')} stopOnBlocked={budgets.get('stopOnBlocked')}"
            )
        return 0
    except Exception as e:
        formatter.error(e, error_code="session_continuation_show_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    sys.exit(main(parser.parse_args()))

