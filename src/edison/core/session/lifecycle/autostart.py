"""Session auto-start orchestration with rollback semantics."""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .manager import SessionManager, get_session
from ..core.naming import generate_session_id
from ..persistence.graph import save_session
from .. import worktree
from ..core.context import SessionContext
from .._config import get_config
from edison.core.utils.io import ensure_directory
from edison.core.utils.paths import PathResolver
from ...config.domains import OrchestratorConfig
from edison.core.orchestrator import (
    OrchestratorLauncher,
    OrchestratorError,
)
from edison.core.utils.paths import get_management_paths
from edison.core.utils.paths import get_project_config_dir
from edison.data import get_data_path


class SessionAutoStartError(Exception):
    """Raised when auto-start fails."""


class SessionAutoStart:
    """Orchestrates session creation, worktree setup, and orchestrator launch."""

    def __init__(
        self,
        session_manager: Optional[SessionManager] = None,
        orchestrator_config: Optional[OrchestratorConfig] = None,
        *,
        project_root: Optional[Path | str] = None,
        env: Optional[Dict[str, Any]] = None,
    ) -> None:
        # Allow callers to inject env for isolated test runs (E2E uses this)
        if env:
            os.environ.update({k: str(v) for k, v in env.items()})

        resolved_root = Path(project_root).expanduser().resolve() if project_root else None

        self.session_manager = session_manager or SessionManager(resolved_root)

        self.orchestrator_config = orchestrator_config
        if self.orchestrator_config is None:
            try:
                self.orchestrator_config = OrchestratorConfig(resolved_root)
            except ValueError as exc:
                if "Missing orchestrators configuration" not in str(exc):
                    raise
                target_root = resolved_root or self.session_manager.project_root
                self._ensure_orchestrator_config(target_root)
                self.orchestrator_config = OrchestratorConfig(target_root, validate=False)

        self.project_root = self.session_manager.project_root
        # Bind a fresh session config for naming/worktree checks
        self._session_config = self.session_manager._config  # intentionally reuse manager config

    # ------------------------------------------------------------------
    def start(
        self,
        process: Optional[str] = None,
        orchestrator_profile: Optional[str] = None,
        initial_prompt_path: Optional[Path] = None,
        prompt_path: Optional[Path | str] = None,
        detach: bool = False,
        no_worktree: bool = False,
        dry_run: bool = False,
        launch_orchestrator: bool = True,
        persist_dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Start a new session with optional worktree + orchestrator launch.

        Raises:
            SessionAutoStartError: on any failure after validating inputs.
        """
        # Validate inputs and prepare configuration
        prompt_text, profile, session_id, do_worktree, should_launch = self._prepare_start_inputs(
            initial_prompt_path=initial_prompt_path,
            prompt_path=prompt_path,
            orchestrator_profile=orchestrator_profile,
            no_worktree=no_worktree,
            dry_run=dry_run,
            launch_orchestrator=launch_orchestrator,
        )

        # Handle dry run early exit
        if dry_run and not persist_dry_run:
            return self._handle_dry_run(session_id, do_worktree)

        # Track created resources for rollback
        session_created = False
        worktree_path: Optional[Path] = None
        branch_name: Optional[str] = None

        try:
            # Create session record
            session_created = self._create_session(
                session_id=session_id,
                profile=profile,
                process=process,
                initial_prompt_path=initial_prompt_path,
                detach=detach,
                dry_run=dry_run,
            )

            # Setup worktree if enabled
            worktree_path, branch_name = self._setup_worktree(
                session_id=session_id,
                do_worktree=do_worktree,
                dry_run=dry_run,
            )

            # Launch orchestrator
            process_obj = self._launch_orchestrator(
                session_id=session_id,
                profile=profile,
                worktree_path=worktree_path,
                should_launch=should_launch,
                prompt_text=prompt_text,
            )

            # Build and return result
            return self._build_result(
                session_id=session_id,
                worktree_path=worktree_path,
                process_obj=process_obj,
                detach=detach,
                dry_run=dry_run,
            )

        except OrchestratorError as exc:
            self._handle_rollback(session_created, session_id, worktree_path, branch_name)
            raise SessionAutoStartError(str(exc)) from exc
        except Exception as exc:
            self._handle_rollback(session_created, session_id, worktree_path, branch_name)
            raise SessionAutoStartError(str(exc)) from exc

    # ------------------------------------------------------------------
    # Helper methods for start() - each handles a single responsibility
    # ------------------------------------------------------------------

    def _prepare_start_inputs(
        self,
        initial_prompt_path: Optional[Path],
        prompt_path: Optional[Path | str],
        orchestrator_profile: Optional[str],
        no_worktree: bool,
        dry_run: bool,
        launch_orchestrator: bool,
    ) -> Tuple[Optional[str], str, str, bool, bool]:
        """Validate inputs and prepare configuration for session start.

        Returns:
            Tuple of (prompt_text, profile, session_id, do_worktree, should_launch)
        """
        # Validate prompt early (Scenario 3)
        prompt_text: Optional[str] = None
        prompt_source = initial_prompt_path or (Path(prompt_path) if prompt_path else None)
        if prompt_source is not None:
            prompt_text = self._read_prompt_file(Path(prompt_source))

        # Resolve orchestrator profile
        profile = orchestrator_profile or self.orchestrator_config.get_default_profile_name()

        # Generate session ID using PID-based inference
        session_id = generate_session_id()

        # Determine worktree and launch behavior
        wt_cfg = self._session_config.get_worktree_config()
        do_worktree = bool(wt_cfg.get("enabled", False)) and not no_worktree
        should_launch = launch_orchestrator and not dry_run

        return prompt_text, profile, session_id, do_worktree, should_launch

    def _handle_dry_run(self, session_id: str, do_worktree: bool) -> Dict[str, Any]:
        """Handle dry run mode without persisting session.

        Returns:
            Dry run result dictionary with computed paths but no side effects.
        """
        wt_path, _ = (
            worktree.create_worktree(session_id, dry_run=True)
            if do_worktree
            else (None, None)
        )
        return {
            "status": "dry_run",
            "session_id": session_id,
            "worktree_path": str(wt_path) if wt_path else None,
            "orchestrator_pid": None,
            "process": None,
            "orchestrator_process": None,
        }

    def _create_session(
        self,
        session_id: str,
        profile: str,
        process: Optional[str],
        initial_prompt_path: Optional[Path],
        detach: bool,
        dry_run: bool,
    ) -> bool:
        """Create and persist session record.

        Returns:
            True when session is successfully created (for rollback tracking).

        Raises:
            SessionAutoStartError: if session creation fails.
        """
        metadata = {
            "autoStarted": True,
            "orchestratorProfile": profile,
            "process": process,
            "initialPromptPath": str(initial_prompt_path) if initial_prompt_path else None,
            "detach": detach,
            "dryRun": dry_run,
        }

        self.session_manager.create_session(
            session_id=session_id,
            metadata=metadata,
            owner=profile,
        )
        return True

    def _setup_worktree(
        self,
        session_id: str,
        do_worktree: bool,
        dry_run: bool,
    ) -> Tuple[Optional[Path], Optional[str]]:
        """Set up git worktree for session.

        Returns:
            Tuple of (worktree_path, branch_name).

        Raises:
            SessionAutoStartError: if worktree creation fails (triggers rollback).
        """
        if not do_worktree:
            return None, None

        try:
            wt_cfg = self._session_config.get_worktree_config()
            worktree_path, branch_name = worktree.create_worktree(
                session_id,
                base_branch=wt_cfg.get("baseBranch", "main"),
                dry_run=dry_run,
            )
        except Exception as exc:
            # Rollback session before propagating error
            self._rollback_session(session_id)
            raise SessionAutoStartError(f"Worktree creation failed: {exc}") from exc

        if worktree_path:
            if dry_run:
                ensure_directory(worktree_path)
                ensure_directory(worktree_path / ".git")

            # Use centralized helper to construct git metadata
            session = get_session(session_id)
            git_meta = worktree.prepare_session_git_metadata(
                session_id, worktree_path, branch_name
            )
            if isinstance(session, dict):
                session.setdefault("git", {}).update(git_meta)
                save_session(session_id, session)

        return worktree_path, branch_name

    def _launch_orchestrator(
        self,
        session_id: str,
        profile: str,
        worktree_path: Optional[Path],
        should_launch: bool,
        prompt_text: Optional[str],
    ) -> Any:
        """Launch orchestrator process.

        Returns:
            Process object if launched, None otherwise.

        Raises:
            OrchestratorError: if orchestrator launch fails (triggers rollback).
        """
        # Prepare session context for launcher
        session = get_session(session_id)
        ctx = SessionContext()
        ctx.session_id = session_id
        ctx.session = session
        ctx.session_worktree = str(worktree_path) if worktree_path else None
        ctx.worktree_path = ctx.session_worktree
        ctx.project_root = self.session_manager.project_root

        launcher = OrchestratorLauncher(self.orchestrator_config, ctx)
        log_path = self._session_log_path(session_id)

        process_obj = None
        if should_launch:
            # Launch orchestrator inside worktree when available
            if worktree_path:
                with SessionContext.in_session_worktree(session_id):
                    process_obj = launcher.launch(
                        profile, initial_prompt=prompt_text, log_path=log_path
                    )
            else:
                process_obj = launcher.launch(
                    profile, initial_prompt=prompt_text, log_path=log_path
                )
        else:
            # Record prompt even when not launching to aid audits
            if prompt_text is not None:
                log_path.write_text(f"{prompt_text}\n", encoding="utf-8")

        return process_obj

    def _build_result(
        self,
        session_id: str,
        worktree_path: Optional[Path],
        process_obj: Any,
        detach: bool,
        dry_run: bool,
    ) -> Dict[str, Any]:
        """Build final result object.

        Returns:
            Result dictionary with session metadata and process info.
        """
        pid: Optional[int] = None if (detach or not process_obj) else process_obj.pid

        return {
            "status": "dry_run" if dry_run else "success",
            "session_id": session_id,
            "worktree_path": str(worktree_path) if worktree_path else None,
            "orchestrator_pid": pid,
            "process": process_obj,
            "orchestrator_process": process_obj,
        }

    def _handle_rollback(
        self,
        session_created: bool,
        session_id: str,
        worktree_path: Optional[Path],
        branch_name: Optional[str],
    ) -> None:
        """Handle rollback of created resources on failure.

        Cleans up worktree and session in reverse order of creation.
        """
        if worktree_path:
            self._rollback_worktree(worktree_path, branch_name)
        if session_created:
            self._rollback_session(session_id)

    # ------------------------------------------------------------------
    def _rollback_session(self, session_id: str) -> None:
        """Remove session metadata across known state directories."""
        try:
            cfg = get_config()
            root_rel = cfg.get_session_root_path()
            roots = (PathResolver.resolve_project_root() / root_rel).resolve()
            for path in roots.glob(f"**/{session_id}/session.json"):
                shutil.rmtree(path.parent, ignore_errors=True)
            for flat in roots.glob(f"**/{session_id}.json"):
                try:
                    flat.unlink()
                except Exception:
                    pass
        except Exception:
            pass

    def _rollback_worktree(self, worktree_path: Path, branch_name: Optional[str]) -> None:
        """Rollback worktree creation by delegating to worktree.remove_worktree.

        The remove_worktree function already handles all cleanup logic including
        fallback removal if git commands fail.
        """
        try:
            worktree.remove_worktree(worktree_path, branch_name)
        except Exception:
            # remove_worktree already tries multiple cleanup strategies
            # If it still fails, we've done our best - suppress error
            pass

    def _read_prompt_file(self, path: Path) -> str:
        if not path.exists():
            raise SessionAutoStartError(f"Prompt file not found: {path}")
        if not path.is_file():
            raise SessionAutoStartError(f"Prompt path is not a file: {path}")
        return path.read_text(encoding="utf-8")

    def _session_log_path(self, session_id: str) -> Path:
        """Return path for per-session orchestrator log."""
        mgmt_paths = get_management_paths(self.session_manager.project_root)
        base = mgmt_paths.get_session_state_dir("wip") / session_id
        ensure_directory(base)
        return base / "orchestrator.log"

    def _ensure_orchestrator_config(self, repo_root: Path) -> None:
        """Ensure orchestrator config exists; bootstrap from bundled defaults when missing."""
        from edison.core.utils.io import dump_yaml_string

        cfg_dir = get_project_config_dir(repo_root) / "config"
        ensure_directory(cfg_dir)
        cfg_path = cfg_dir / "orchestrator.yaml"
        if cfg_path.exists():
            return

        # Prefer copying from bundled edison.data package
        try:
            bundled_cfg = get_data_path("config", "orchestrator.yaml")
            if bundled_cfg.exists():
                shutil.copy(bundled_cfg, cfg_path)
                return
        except Exception:
            pass

        # Minimal fallback using available orchestrator binaries
        available = [name for name in ("claude", "codex", "gemini") if shutil.which(name)]
        default_name = available[0] if available else "claude"
        profiles: Dict[str, Any] = {}
        targets = available or [default_name]
        for name in targets:
            profiles[name] = {
                "command": name,
                "cwd": "{session_worktree}",
                "initial_prompt": {"enabled": False},
            }
        cfg_path.write_text(
            dump_yaml_string({"orchestrators": {"default": default_name, "profiles": profiles}}),
            encoding="utf-8",
        )


__all__ = ["SessionAutoStart", "SessionAutoStartError"]
