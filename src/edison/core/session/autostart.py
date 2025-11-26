"""Session auto-start orchestration with rollback semantics."""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .manager import SessionManager
from .naming import generate_session_id
from . import store
from . import worktree
from .context import SessionContext
from ..orchestrator.config import OrchestratorConfig
from ..orchestrator.launcher import (
    OrchestratorLauncher,
    OrchestratorError,
)
from ..paths.management import get_management_paths


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
        naming_strategy: Optional[str] = None,
        dry_run: bool = False,
        launch_orchestrator: bool = True,
        persist_dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Start a new session with optional worktree + orchestrator launch.

        Raises:
            SessionAutoStartError: on any failure after validating inputs.
        """

        # Validate prompt early (Scenario 3)
        prompt_text: Optional[str] = None
        prompt_source = initial_prompt_path or (Path(prompt_path) if prompt_path else None)
        if prompt_source is not None:
            prompt_text = self._read_prompt_file(Path(prompt_source))

        profile = orchestrator_profile or self.orchestrator_config.get_default_profile_name()

        # Generate session ID using PID-based inference (legacy args ignored)
        session_id = generate_session_id()

        wt_cfg = self._session_config.get_worktree_config()
        do_worktree = bool(wt_cfg.get("enabled", False)) and not no_worktree
        should_launch = launch_orchestrator and not dry_run

        if dry_run and not persist_dry_run:
            wt_path, _ = (worktree.create_worktree(session_id, dry_run=True)
                          if do_worktree else (None, None))
            return {
                "status": "dry_run",
                "session_id": session_id,
                "worktree_path": str(wt_path) if wt_path else None,
                "orchestrator_pid": None,
                "process": None,
                "orchestrator_process": None,
            }

        # Track created resources for rollback
        session_created = False
        worktree_path: Optional[Path] = None
        branch_name: Optional[str] = None

        try:
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
                process=process,
                owner=profile,
                naming_strategy=naming_strategy,
            )
            session_created = True

            log_path = self._session_log_path(session_id)

            if do_worktree:
                try:
                    worktree_path, branch_name = worktree.create_worktree(
                        session_id,
                        base_branch=wt_cfg.get("baseBranch", "main"),
                        dry_run=dry_run,
                    )
                except Exception as exc:  # Scenario 1 rollback
                    self._rollback_session(session_id)
                    raise SessionAutoStartError(f"Worktree creation failed: {exc}") from exc

                if worktree_path:
                    if dry_run:
                        worktree_path.mkdir(parents=True, exist_ok=True)
                        (worktree_path / ".git").mkdir(parents=True, exist_ok=True)
                    session = store.load_session(session_id)
                    git_meta = session.setdefault("git", {}) if isinstance(session, dict) else {}
                    git_meta["worktreePath"] = str(worktree_path)
                    if branch_name:
                        git_meta["branchName"] = branch_name
                    git_meta.setdefault("baseBranch", wt_cfg.get("baseBranch", "main"))
                    store.save_session(session_id, session)

            # Prepare session context for launcher
            session = store.load_session(session_id)
            ctx = SessionContext()
            ctx.session_id = session_id
            ctx.session = session
            ctx.session_worktree = str(worktree_path) if worktree_path else None
            ctx.worktree_path = ctx.session_worktree
            ctx.project_root = self.session_manager.project_root

            launcher = OrchestratorLauncher(self.orchestrator_config, ctx)

            process_obj = None
            if should_launch:
                # Launch orchestrator inside worktree when available
                if worktree_path:
                    with SessionContext.in_session_worktree(session_id):
                        process_obj = launcher.launch(profile, initial_prompt=prompt_text, log_path=log_path)
                else:
                    process_obj = launcher.launch(profile, initial_prompt=prompt_text, log_path=log_path)
            else:
                # Record prompt even when not launching to aid audits
                if prompt_text is not None:
                    log_path.write_text(f"{prompt_text}\n", encoding="utf-8")

            pid: Optional[int] = None if (detach or not process_obj) else process_obj.pid

            return {
                "status": "dry_run" if dry_run else "success",
                "session_id": session_id,
                "worktree_path": str(worktree_path) if worktree_path else None,
                "orchestrator_pid": pid,
                "process": process_obj,
                "orchestrator_process": process_obj,
            }
        except OrchestratorError as exc:  # Scenario 2 rollback
            if worktree_path:
                self._rollback_worktree(worktree_path, branch_name)
            if session_created:
                self._rollback_session(session_id)
            raise SessionAutoStartError(str(exc)) from exc
        except Exception as exc:
            if worktree_path:
                self._rollback_worktree(worktree_path, branch_name)
            if session_created:
                self._rollback_session(session_id)
            raise SessionAutoStartError(str(exc)) from exc

    # ------------------------------------------------------------------
    def _rollback_session(self, session_id: str) -> None:
        """Remove session metadata across known state directories."""
        try:
            roots = store._sessions_root()  # type: ignore[attr-defined]
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
        try:
            worktree.remove_worktree(worktree_path, branch_name)
        except Exception:
            try:
                if worktree_path.exists():
                    worktree_path.unlink()
            except Exception:
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
        base.mkdir(parents=True, exist_ok=True)
        return base / "orchestrator.log"

    def _ensure_orchestrator_config(self, repo_root: Path) -> None:
        """Ensure orchestrator config exists; bootstrap from core defaults when missing."""
        cfg_dir = repo_root / ".edison" / "core" / "config"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        cfg_path = cfg_dir / "orchestrator.yaml"
        if cfg_path.exists():
            return

        # Prefer copying from the current repo's core config
        source_root = Path(__file__).resolve().parents[4]
        source_cfg = source_root / ".edison" / "core" / "config" / "orchestrator.yaml"
        if source_cfg.exists():
            shutil.copy(source_cfg, cfg_path)
            return

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
            yaml.safe_dump({"orchestrators": {"default": default_name, "profiles": profiles}}),
            encoding="utf-8",
        )


__all__ = ["SessionAutoStart", "SessionAutoStartError"]
