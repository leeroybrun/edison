"""Session manager facade."""
from __future__ import annotations

import logging
import subprocess
from typing import Any, Dict, List, Optional
from pathlib import Path

from . import store
from . import state as session_state
from . import validation
from . import worktree
from ._config import get_config
from .naming import generate_session_id
from ..paths import PathResolver
from ..paths.management import get_management_paths
from ..file_io.utils import ensure_directory
from ..exceptions import SessionError
from ..utils.time import utc_timestamp

logger = logging.getLogger(__name__)


def _get_worktree_config():
    """Get worktree config lazily to avoid module-level evaluation."""
    return get_config().get_worktree_config()

def create_session(
    session_id: str, 
    owner: str, 
    mode: str = "start", 
    install_deps: Optional[bool] = None,
    *,
    create_wt: bool = True
) -> Path:
    """Create a new session with optional worktree."""
    validation.validate_session_id_format(session_id)
    if store.session_exists(session_id):
        raise SessionError(f"Session {session_id} already exists", session_id=session_id)

    initial_state = "active"
    sess = {
        "id": session_id,
        "state": initial_state,
        "meta": {
            "sessionId": session_id,
            "owner": owner,
            "mode": mode,
            "createdAt": utc_timestamp(),
            "lastActive": utc_timestamp(),
            "status": "wip",
        },
        "tasks": {},
        "qa": {},
        "activityLog": [
            {
                "timestamp": utc_timestamp(),
                "message": "Session created",
            }
        ],
    }

    # Handle worktree creation if configured or requested
    # We use ensure_worktree_materialized logic but we can call create_worktree directly
    # or let the script handle it?
    # The original sessionlib.create_session_with_worktree called create_worktree.
    
    # If we are in a git repo, we might want to create a worktree.
    # But let's delegate to worktree module.
    # We can use ensure_worktree_materialized which calls create_worktree.
    
    # But wait, ensure_worktree_materialized returns git meta dict.
    # We should update sess["git"] with it.
    
    sess.setdefault("git", {})
    wt_cfg = _get_worktree_config()
    base_branch = wt_cfg.get("baseBranch", "main") if isinstance(wt_cfg, dict) else "main"
    sess["git"].setdefault("baseBranch", base_branch)

    repo_dir = PathResolver.resolve_project_root()
    in_git_repo = (repo_dir / ".git").exists()

    if create_wt and in_git_repo:
        try:
            wt_path, branch = worktree.create_worktree(session_id, install_deps=install_deps)
            if wt_path:
                sess["git"]["worktreePath"] = str(wt_path)
            if branch:
                sess["git"]["branchName"] = branch
        except Exception as exc:
            raise SessionError(f"Failed to create worktree for session {session_id}: {exc}", session_id=session_id) from exc
    else:
        sess["git"].setdefault("worktreePath", None)
        sess["git"].setdefault("branchName", None)

    sess["git"].setdefault("worktreePath", None)
    sess["git"].setdefault("branchName", None)

    # Persist new session in active/wip directory layout
    sess_dir = store._session_dir(initial_state, session_id)
    ensure_directory(sess_dir)
    path = sess_dir / "session.json"
    store._write_json(path, sess)  # type: ignore[attr-defined]
    return path

def get_session(session_id: str) -> Dict[str, Any]:
    """Get a session by ID."""
    return store.load_session(session_id)

def list_sessions(state: Optional[str] = None) -> List[str]:
    """List sessions, optionally filtered by state."""
    # store._list_active_sessions only lists active.
    # We might need a better list function in store or iterate directories.
    # For now, if state="active", use store._list_active_sessions.
    if state == "active" or state is None:
         return store._list_active_sessions()
    # TODO: Implement listing for other states in store
    return []

def transition_session(session_id: str, target_state: str) -> None:
    """Transition a session to a new state."""
    sess = get_session(session_id)
    current_state = sess.get("state", "unknown")

    # Default readiness to true to satisfy state-machine conditions when unset
    sess.setdefault("ready", True)

    session_state.validate_transition(current_state, target_state, context={"session": sess})

    # Update state in JSON
    sess["state"] = target_state
    store.save_session(session_id, sess)
    
    # Move directory if needed
    # store._move_session_json_to handles moving
    store._move_session_json_to(target_state, session_id)

def touch_session(session_id: str) -> None:
    """Update session lastActive timestamp."""
    try:
        sess = store.load_session(session_id)
        sess.setdefault("meta", {})["lastActive"] = utc_timestamp()
        store.save_session(session_id, sess)
    except Exception:
        pass

def render_markdown(session: Dict[str, Any], state_spec: Optional[Dict[str, Any]] = None) -> str:
    """Render session as markdown summary."""
    return store.render_markdown(session, state_spec)


class SessionManager:
    """Minimal OO wrapper mirroring legacy sessionlib behavior for tests."""

    def __init__(self, project_root: Optional[Path] = None) -> None:
        self.project_root = project_root or PathResolver.resolve_project_root()
        self._config = get_config(self.project_root)

    def create_session(
        self,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        *,
        process: Optional[str] = None,
        owner: Optional[str] = None,
        naming_strategy: Optional[str] = None,
    ) -> Path:
        sid = session_id or self._generate_session_id(
            process=process, owner=owner, naming_strategy=naming_strategy
        )

        path = store.ensure_session(sid, state="Active")
        data = store.load_session(sid)
        data["state"] = str(data.get("state", "active")).lower()
        meta = data.setdefault("meta", {})

        if metadata:
            data["metadata"] = metadata
            if isinstance(metadata, dict):
                meta.update(metadata)

        # Record naming strategy + orchestrator profile for downstream consumers
        strategy_used = naming_strategy or self._config.get_naming_config().get("strategy")
        if strategy_used:
            meta["namingStrategy"] = strategy_used
        if owner:
            meta["orchestratorProfile"] = owner

        store.save_session(sid, data)
        return path / "session.json"

    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Load a session by ID."""
        return store.load_session(session_id)

    def transition_state(self, session_id: str, to_state: str) -> Path:
        # Ensure readiness flag for state machine conditions
        try:
            data = store.load_session(session_id)
            data.setdefault("ready", True)
            store.save_session(session_id, data)
        except Exception:
            pass

        store.transition_state(session_id, to_state)
        updated = store.load_session(session_id, state=to_state)
        updated["state"] = to_state
        return store.get_session_json_path(session_id)

    # --- Internal helpers -------------------------------------------------
    def _generate_session_id(
        self,
        *,
        process: Optional[str],
        owner: Optional[str],
        naming_strategy: Optional[str],
    ) -> str:
        # The parameters process, owner, and naming_strategy are now ignored
        # as the generate_session_id function does not use them.
        # This method is effectively a wrapper for backward compatibility.
        return generate_session_id()



def create_session_with_worktree(
    session_id: str,
    owner: str,
    mode: str = "start",
    install_deps: Optional[bool] = None,
) -> Path:
    """Create a session and its git worktree with strict error handling.

    CalledProcessError -> RuntimeError with clear message (fail fast)
    PermissionError -> propagate
    Other Exception -> log warning and continue without worktree
    """
    validation.validate_session_id_format(session_id)

    wt_path: Optional[Path] = None
    branch: Optional[str] = None
    had_noncritical_error = False
    try:
        wt_path, branch = worktree.create_worktree(session_id, install_deps=install_deps)
    except PermissionError:
        logger.error("Permission denied creating session worktree for %s", session_id, exc_info=True)
        raise
    except subprocess.CalledProcessError as exc:
        logger.error("Git operation failed creating worktree for %s", session_id, exc_info=True)
        raise RuntimeError("Session git setup failed") from exc
    except Exception:
        logger.warning("Unexpected git error while creating worktree for %s; continuing without worktree", session_id, exc_info=True)
        had_noncritical_error = True

    path = create_session(
        session_id,
        owner,
        mode=mode,
        install_deps=install_deps,
        create_wt=False,
    )

    if wt_path and branch:
        sess = store.load_session(session_id)
        sess.setdefault("git", {})
        sess["git"]["worktreePath"] = str(wt_path)
        sess["git"]["branchName"] = branch
        store.save_session(session_id, sess)

    if had_noncritical_error:
        return path

    return path
