"""
Orchestrator launcher for EDISON auto-start system.

Supports launching different LLM CLIs with configurable prompt delivery:
- stdin: Pass prompt via standard input
- file: Write prompt to temp file, pass path as arg
- arg: Pass prompt directly as command-line argument
- env: Set prompt in environment variable
"""

from __future__ import annotations

import os
import random
import shutil
import string
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from edison.core.config.domains import OrchestratorConfig
from edison.core.session.context import SessionContext
from edison.core.utils.time import utc_timestamp
from edison.core.utils.io import ensure_dir


class _SafeDict(dict):
    """dict that preserves unknown placeholders instead of raising."""

    def __missing__(self, key: str) -> str:  # pragma: no cover - defensive
        return "{" + key + "}"


class OrchestratorError(Exception):
    """Base exception for orchestrator errors."""


class OrchestratorNotFoundError(OrchestratorError):
    """Orchestrator binary not found in PATH."""


class OrchestratorConfigError(OrchestratorError):
    """Invalid orchestrator configuration."""


class OrchestratorLaunchError(OrchestratorError):
    """Failed to launch orchestrator."""


class OrchestratorLauncher:
    def __init__(self, config: OrchestratorConfig, session_context: SessionContext):
        """Initialize launcher with config and session context."""
        self.config = config
        self.session_context = session_context
        self._temp_files: List[Path] = []
        self._project_root: Path = Path(
            getattr(session_context, "project_root", None) or config.repo_root
        ).resolve()
        self._session_worktree: Optional[Path] = self._resolve_worktree()

    # --- Public API -----------------------------------------------------
    def launch(
        self,
        profile_name: str,
        initial_prompt: Optional[str] = None,
        log_path: Optional[Path] = None,
    ) -> subprocess.Popen:
        """
        Launch orchestrator with given profile.

        Args:
            profile_name: Name of orchestrator profile from config
            initial_prompt: Optional initial prompt text to deliver

        Returns:
            subprocess.Popen object for the launched orchestrator

        Raises:
            OrchestratorNotFoundError: If binary not in PATH
            OrchestratorConfigError: If profile missing/invalid
            OrchestratorLaunchError: If launch fails
        """

        tokens = self._build_tokens()
        log_file = None
        if log_path:
            ensure_dir(log_path.parent)
            log_file = log_path.open("a", encoding="utf-8")
            log_file.write(f"[launch] {utc_timestamp()} profile={profile_name}\n")
            if initial_prompt is not None:
                log_file.write("[prompt]\n")
                log_file.write(f"{initial_prompt}\n")
            log_file.flush()

        try:
            profile = self.config.get_profile(
                profile_name, context=tokens, expand=True
            )
        except Exception as exc:  # pragma: no cover - defensive
            raise OrchestratorConfigError(str(exc)) from exc

        command = profile.get("command")
        if not command:
            raise OrchestratorConfigError("Profile is missing required 'command'")

        resolved_command = self._resolve_command(command)
        if not resolved_command or not self._verify_binary_exists(resolved_command):
            raise OrchestratorNotFoundError(f"Orchestrator binary not found: {command}")

        args = profile.get("args") or []
        if not isinstance(args, list):
            raise OrchestratorConfigError("Profile args must be a list")
        args_list: List[str] = [str(a) for a in args]

        env = os.environ.copy()
        profile_env = profile.get("env") or {}
        if profile_env and not isinstance(profile_env, dict):
            raise OrchestratorConfigError("Profile env must be a mapping of key/value pairs")
        env.update({k: str(v) for k, v in profile_env.items()})

        cwd = profile.get("cwd")
        cwd_path: Optional[Path] = None
        if cwd:
            cwd_path = Path(cwd)
            if not cwd_path.is_absolute():
                cwd_path = (self._project_root / cwd_path).resolve()
            if not cwd_path.exists():
                ensure_dir(cwd_path)

        initial_cfg = profile.get("initial_prompt") or {}
        prompt_enabled = bool(initial_cfg.get("enabled", False))
        prompt_method = initial_cfg.get("method", "stdin")
        prompt_text = initial_prompt

        if prompt_text is None and prompt_enabled:
            prompt_path = initial_cfg.get("path")
            if prompt_path:
                expanded_path = self._expand_template_vars(str(prompt_path))
                prompt_file_path = Path(expanded_path)
                if not prompt_file_path.is_absolute():
                    prompt_file_path = (self._project_root / prompt_file_path).resolve()
                if not prompt_file_path.exists():
                    raise OrchestratorConfigError(f"Initial prompt file not found: {prompt_file_path}")
                prompt_text = prompt_file_path.read_text(encoding="utf-8")
            else:
                raise OrchestratorConfigError(
                    "Initial prompt enabled but no prompt provided via argument or path"
                )

        stdin_pipe = subprocess.PIPE if prompt_method == "stdin" and prompt_text is not None else None

        try:
            if prompt_text is not None:
                if prompt_method == "file":
                    prompt_file = self._deliver_prompt_file(prompt_text)
                    file_flag = initial_cfg.get("arg_flag") or initial_cfg.get("file_arg")
                    if file_flag:
                        args_list.extend([str(file_flag), str(prompt_file)])
                    else:
                        args_list.append(str(prompt_file))
                elif prompt_method == "arg":
                    flag = initial_cfg.get("arg_flag")
                    target_args = list(args_list)
                    if flag:
                        target_args.append(str(flag))
                    args_list = self._deliver_prompt_arg(prompt_text, target_args)
                elif prompt_method == "env":
                    self._current_env_var = initial_cfg.get("env_var") or "ORCHESTRATOR_PROMPT"
                    env = self._deliver_prompt_env(prompt_text, env)
                elif prompt_method == "stdin":
                    # handled after process start
                    pass
                else:
                    raise OrchestratorConfigError(f"Unsupported prompt method '{prompt_method}'")

            process = subprocess.Popen(
                [resolved_command, *args_list],
                cwd=str(cwd_path) if cwd_path else None,
                env=env,
                stdin=stdin_pipe,
                stdout=log_file or None,
                stderr=subprocess.STDOUT if log_file else None,
                text=True,
            )

            if prompt_text is not None and prompt_method == "stdin":
                self._deliver_prompt_stdin(process, prompt_text)

            if log_file:
                try:
                    log_file.flush()
                except Exception:
                    pass

            return process
        except OrchestratorError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            try:
                if "process" in locals() and process and process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except Exception:
                        process.kill()
            finally:
                self.cleanup_temp_files()
                if log_file:
                    try:
                        log_file.flush()
                        log_file.close()
                    except Exception:
                        pass
            raise OrchestratorLaunchError(str(exc)) from exc
        finally:
            if log_file:
                try:
                    log_file.flush()
                    log_file.close()
                except Exception:
                    pass

    # --- Helpers --------------------------------------------------------
    def _expand_template_vars(self, template: str) -> str:
        """Expand template variables in strings."""
        tokens = self._build_tokens()
        return str(template).format_map(_SafeDict(tokens))

    def _build_tokens(self) -> Dict[str, str]:
        session_id = getattr(self.session_context, "session_id", None)
        session = getattr(self.session_context, "session", None)
        if session_id is None and isinstance(session, dict):
            session_id = (
                session.get("meta", {}).get("sessionId")
                or session.get("meta", {}).get("id")
                or session.get("sessionId")
            )

        worktree = self._session_worktree or self._extract_worktree_from_session()
        tokens: Dict[str, Optional[str]] = {
            "project_root": str(self._project_root),
            "session_worktree": str(worktree) if worktree else None,
            "session_id": str(session_id) if session_id else None,
            "timestamp": utc_timestamp(),
            "shortid": self._generate_shortid(),
        }
        return {k: v for k, v in tokens.items() if v is not None}

    def _deliver_prompt_stdin(self, process: subprocess.Popen, prompt: str) -> None:
        """Deliver prompt via stdin."""
        if process.stdin is None:
            raise OrchestratorLaunchError("Process stdin is not available for prompt delivery")
        process.stdin.write(prompt)
        process.stdin.flush()
        process.stdin.close()

    def _deliver_prompt_file(self, prompt: str) -> Path:
        """Write prompt to temp file, return path."""
        dir_path = self._session_worktree or self._project_root
        temp = tempfile.NamedTemporaryFile(
            mode="w", delete=False, encoding="utf-8", dir=dir_path, prefix="orchestrator_prompt_", suffix=".txt"
        )
        temp.write(prompt)
        temp.flush()
        temp.close()
        temp_path = Path(temp.name)
        self._temp_files.append(temp_path)
        return temp_path

    def _deliver_prompt_arg(self, prompt: str, args: List[str]) -> List[str]:
        """Add prompt to args list."""
        return [*args, prompt]

    def _deliver_prompt_env(self, prompt: str, env: Dict[str, str]) -> Dict[str, str]:
        """Add prompt to environment."""
        env_var = getattr(self, "_current_env_var", "ORCHESTRATOR_PROMPT")
        env[env_var] = prompt
        return env

    def _verify_binary_exists(self, command: str) -> bool:
        """Check if command exists in PATH or as a file."""
        cmd_path = Path(command)
        if cmd_path.is_absolute() and cmd_path.exists():
            return True
        if os.sep in command:
            if cmd_path.exists():
                return True
        return shutil.which(command) is not None

    def _resolve_command(self, command: str) -> Optional[str]:
        """Resolve command to an executable path."""
        cmd_path = Path(command)
        if cmd_path.is_absolute():
            return str(cmd_path) if cmd_path.exists() else None
        if os.sep in command:
            candidate = (self._project_root / cmd_path).resolve()
            if candidate.exists():
                return str(candidate)
            if cmd_path.exists():
                return str(cmd_path.resolve())
        found = shutil.which(command)
        return found

    def _resolve_worktree(self) -> Optional[Path]:
        for attr in ("session_worktree", "worktree_path", "worktree", "worktreePath"):
            val = getattr(self.session_context, attr, None)
            if val:
                return Path(val).resolve()
        return self._extract_worktree_from_session()

    def _extract_worktree_from_session(self) -> Optional[Path]:
        session = getattr(self.session_context, "session", None)
        if isinstance(session, dict):
            git = session.get("git", {}) if isinstance(session.get("git", {}), dict) else {}
            wt = git.get("worktreePath") or session.get("worktree_path")
            if wt:
                return Path(wt).resolve()
        return None

    def _generate_shortid(self, length: int = 6) -> str:
        alphabet = string.ascii_lowercase + string.digits
        return "".join(random.choice(alphabet) for _ in range(length))

    def cleanup_temp_files(self) -> None:
        """Clean up any temp files created during launch."""
        for path in list(self._temp_files):
            try:
                path.unlink(missing_ok=True)
            finally:
                if path in self._temp_files:
                    self._temp_files.remove(path)
