from __future__ import annotations

"""Subprocess helpers with config-driven timeouts and command wrappers.

This module provides safe subprocess execution with:
- Config-driven timeout management
- Command wrappers for common operations (git, db, CI)
- Shell pipeline parsing
- No shell=True by default (security)
"""

import shlex
import os
import signal
import subprocess
from pathlib import Path
from time import perf_counter
from typing import Any, List, MutableMapping, Optional, Sequence

from edison.core.config.domains.timeouts import TimeoutsConfig


def _flatten_cmd(cmd: Any) -> Sequence[str]:
    if isinstance(cmd, (list, tuple)):
        return [str(p) for p in cmd]
    return shlex.split(str(cmd))


def _infer_timeout_type(cmd: Any) -> str:
    parts = _flatten_cmd(cmd)
    if not parts:
        return "default"

    first = parts[0].lower()
    joined = " ".join(parts).lower()

    if first == "git" or " git " in f" {joined} ":
        return "git_operations"
    if any("test" in p.lower() for p in parts):
        return "test_execution"
    if any(p.lower() in {"build", "bundle"} for p in parts) or "build" in joined:
        return "build_operations"
    if any(p.lower() in {"pnpm", "npm", "yarn"} and "build" in joined for p in parts):
        return "build_operations"
    return "default"


def _popen_process_group_kwargs() -> dict[str, Any]:
    if os.name == "posix":
        return {"start_new_session": True}
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", None)
        if isinstance(creationflags, int):
            return {"creationflags": creationflags}
    return {}


def _terminate_process_group(proc: subprocess.Popen[Any]) -> None:
    if proc.poll() is not None:
        return
    if os.name == "posix":
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except Exception:
            try:
                proc.terminate()
            except Exception:
                pass
        try:
            proc.wait(timeout=0.2)
        except Exception:
            pass
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        try:
            proc.wait(timeout=0.2)
        except Exception:
            pass
        return

    try:
        proc.kill()
    except Exception:
        pass
    try:
        proc.wait(timeout=0.2)
    except Exception:
        pass


def _run_capture_output_nohang(cmd: Any, *, timeout: float, **kwargs: Any) -> subprocess.CompletedProcess:
    argv = list(_flatten_cmd(cmd))
    input_value = kwargs.pop("input", None)
    cwd = kwargs.pop("cwd", None)
    env = kwargs.pop("env", None)
    text = bool(kwargs.pop("text", True))
    check = bool(kwargs.pop("check", False))
    kwargs.pop("capture_output", None)

    proc = subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        stdin=subprocess.PIPE if input_value is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=text,
        **_popen_process_group_kwargs(),
    )
    try:
        stdout, stderr = proc.communicate(input=input_value, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        _terminate_process_group(proc)
        try:
            stdout, stderr = proc.communicate(timeout=0.2)
        except Exception:
            stdout = getattr(exc, "output", None)
            stderr = getattr(exc, "stderr", None)
        raise subprocess.TimeoutExpired(argv, timeout, output=stdout, stderr=stderr) from None

    completed = subprocess.CompletedProcess(
        argv,
        proc.returncode if proc.returncode is not None else 0,
        stdout=stdout,
        stderr=stderr,
    )
    if check and completed.returncode != 0:
        raise subprocess.CalledProcessError(
            completed.returncode,
            argv,
            output=stdout,
            stderr=stderr,
        )
    return completed


def configured_timeout(cmd: Any, timeout_type: str | None = None, cwd: Path | str | None = None) -> float:
    """Get configured timeout for a command.

    Args:
        cmd: Command to get timeout for
        timeout_type: Explicit timeout type (e.g., 'git_operations')
        cwd: Working directory for context

    Returns:
        Timeout in seconds

    Raises:
        RuntimeError: If timeout cannot be determined
    """
    # Determine repo root from cwd or auto-detect
    repo_root = None
    if cwd is not None:
        try:
            repo_root = Path(cwd).resolve()
        except Exception:
            pass

    # Get timeout config
    timeout_config = TimeoutsConfig(repo_root=repo_root)

    # Determine timeout type
    ttype = timeout_type or _infer_timeout_type(cmd)

    # Map timeout type to TimeoutsConfig attribute
    timeout_map = {
        "git_operations": timeout_config.git_operations_seconds,
        "db_operations": timeout_config.db_operations_seconds,
        "json_io_lock": timeout_config.json_io_lock_seconds,
        "test_execution": timeout_config.test_execution_seconds,
        "build_operations": timeout_config.build_operations_seconds,
        "default": timeout_config.default_seconds,
    }

    timeout = timeout_map.get(ttype)
    if timeout is None:
        # Fallback to default
        timeout = timeout_config.default_seconds

    return float(timeout)


def run_with_timeout(cmd, timeout_type: str | None = None, **kwargs):
    """Run a subprocess using the configured timeout bucket.

    Args:
        cmd: Command list/str passed through to ``subprocess.run``.
        timeout_type: Key inside ``subprocess_timeouts`` (e.g., ``git_operations``).
        **kwargs: Additional arguments forwarded to ``subprocess.run``.

    Returns:
        CompletedProcess from ``subprocess.run``.

    Raises:
        subprocess.TimeoutExpired: When the command exceeds its configured timeout.
        RuntimeError: If the timeout configuration is missing.
    """

    # Allow callers to override the timeout explicitly while still honouring
    # configured defaults when none is supplied.
    explicit_timeout = kwargs.pop("timeout", None)
    timeout = explicit_timeout if explicit_timeout is not None else configured_timeout(
        cmd, timeout_type=timeout_type, cwd=kwargs.get("cwd")
    )

    # Best-effort structured audit logging (fail-open).
    start = perf_counter()
    repo_root: Path | None = None
    try:
        from edison.core.utils.paths import PathResolver

        repo_root = PathResolver.resolve_project_root()
    except Exception:
        repo_root = None

    # Emit start/end events only when enabled.
    max_out_bytes = 0
    subprocess_audit_enabled = False
    if repo_root is not None:
        try:
            from edison.core.config.domains.logging import LoggingConfig

            log_cfg = LoggingConfig(repo_root=repo_root)
            subprocess_audit_enabled = bool(
                log_cfg.enabled and log_cfg.audit_enabled and log_cfg.subprocess_enabled
            )
            max_out_bytes = int(log_cfg.subprocess_max_output_bytes)
        except Exception:
            subprocess_audit_enabled = False

    if subprocess_audit_enabled:
        try:
            from edison.core.audit.logger import audit_event

            audit_event(
                "subprocess.start",
                repo_root=repo_root,
                argv=_flatten_cmd(cmd),
                cwd=kwargs.get("cwd"),
                timeout=timeout,
                capture_output=bool(kwargs.get("capture_output", False)),
                check=bool(kwargs.get("check", False)),
            )
        except Exception:
            pass

    try:
        capture_output = bool(kwargs.get("capture_output", False))
        if capture_output and timeout is not None and "stdout" not in kwargs and "stderr" not in kwargs:
            result = _run_capture_output_nohang(cmd, timeout=float(timeout), **kwargs)
        else:
            result = subprocess.run(cmd, timeout=timeout, **kwargs)
    except subprocess.TimeoutExpired as exc:
        if subprocess_audit_enabled:
            try:
                from edison.core.audit.logger import audit_event, truncate_text

                stdout = getattr(exc, "output", None)
                stderr = getattr(exc, "stderr", None)
                stdout_s = stdout if isinstance(stdout, str) else ""
                stderr_s = stderr if isinstance(stderr, str) else ""

                audit_event(
                    "subprocess.timeout",
                    repo_root=repo_root,
                    argv=_flatten_cmd(cmd),
                    cwd=kwargs.get("cwd"),
                    timeout=timeout,
                    duration_ms=(perf_counter() - start) * 1000.0,
                    error=str(exc),
                    stdout=truncate_text(stdout_s, max_bytes=max_out_bytes),
                    stderr=truncate_text(stderr_s, max_bytes=max_out_bytes),
                )
            except Exception:
                pass
        raise
    except subprocess.CalledProcessError as exc:
        if subprocess_audit_enabled:
            try:
                from edison.core.audit.logger import audit_event, truncate_text

                stdout = getattr(exc, "stdout", None) or getattr(exc, "output", None)
                stderr = getattr(exc, "stderr", None)
                stdout_s = stdout if isinstance(stdout, str) else ""
                stderr_s = stderr if isinstance(stderr, str) else ""

                audit_event(
                    "subprocess.end",
                    repo_root=repo_root,
                    argv=_flatten_cmd(cmd),
                    cwd=kwargs.get("cwd"),
                    timeout=timeout,
                    duration_ms=(perf_counter() - start) * 1000.0,
                    returncode=getattr(exc, "returncode", None),
                    ok=False,
                    check=True,
                    stdout=truncate_text(stdout_s, max_bytes=max_out_bytes),
                    stderr=truncate_text(stderr_s, max_bytes=max_out_bytes),
                )
            except Exception:
                pass
        raise
    except Exception as exc:
        if subprocess_audit_enabled:
            try:
                from edison.core.audit.logger import audit_event

                audit_event(
                    "subprocess.error",
                    repo_root=repo_root,
                    argv=_flatten_cmd(cmd),
                    cwd=kwargs.get("cwd"),
                    timeout=timeout,
                    duration_ms=(perf_counter() - start) * 1000.0,
                    error=str(exc),
                )
            except Exception:
                pass
        raise

    if subprocess_audit_enabled:
        try:
            from edison.core.audit.logger import audit_event, truncate_text

            stdout = getattr(result, "stdout", None)
            stderr = getattr(result, "stderr", None)
            stdout_s = stdout if isinstance(stdout, str) else ""
            stderr_s = stderr if isinstance(stderr, str) else ""

            audit_event(
                "subprocess.end",
                repo_root=repo_root,
                argv=_flatten_cmd(cmd),
                cwd=kwargs.get("cwd"),
                timeout=timeout,
                duration_ms=(perf_counter() - start) * 1000.0,
                returncode=getattr(result, "returncode", None),
                ok=(getattr(result, "returncode", 1) == 0),
                check=bool(kwargs.get("check", False)),
                stdout=truncate_text(stdout_s, max_bytes=max_out_bytes),
                stderr=truncate_text(stderr_s, max_bytes=max_out_bytes),
            )
        except Exception:
            pass

    return result


def check_output_with_timeout(cmd, timeout_type: str | None = None, **kwargs):
    timeout = configured_timeout(cmd, timeout_type=timeout_type, cwd=kwargs.get("cwd"))
    return subprocess.check_output(cmd, timeout=timeout, **kwargs)


def reset_subprocess_timeout_cache() -> None:
    """Clear subprocess timeout configuration cache.

    This clears the global config cache, which will reload timeout
    configuration on the next access.
    """
    from edison.core.config.cache import clear_all_caches
    clear_all_caches()


def _to_cwd(cwd: Optional[Path | str]) -> Optional[str]:
    """Convert Path or str cwd to str for subprocess."""
    if cwd is None:
        return None
    return str(cwd)


def run_command(
    cmd: Sequence[str],
    *,
    cwd: Optional[Path | str] = None,
    env: Optional[MutableMapping[str, str]] = None,
    timeout: Optional[float] = None,
    capture_output: bool = False,
    text: bool = True,
    check: bool = False,
    input: Any = None,
) -> subprocess.CompletedProcess:
    """
    Thin wrapper around subprocess.run with safe defaults.

    - No shell=True (security)
    - Optional timeout
    - Optional capture_output/text/check flags

    Args:
        cmd: Command sequence to execute
        cwd: Working directory (Path or str)
        env: Environment variables
        timeout: Timeout in seconds (uses configured timeout if None)
        capture_output: Capture stdout/stderr
        text: Return output as text instead of bytes
        check: Raise CalledProcessError on non-zero exit

    Returns:
        CompletedProcess from subprocess.run
    """
    return run_with_timeout(
        list(cmd),
        cwd=_to_cwd(cwd),
        env=env,
        timeout=timeout,
        capture_output=capture_output,
        text=text,
        check=check,
        input=input,
    )


def run_git_command(
    cmd: Sequence[str],
    *,
    cwd: Optional[Path | str] = None,
    env: Optional[MutableMapping[str, str]] = None,
    timeout: Optional[float] = None,
    capture_output: bool = False,
    text: bool = True,
    check: bool = False,
    allow_branch_switch: bool = False,
) -> subprocess.CompletedProcess:
    """
    Run a git command using the config-driven timeout bucket.

    Args:
        cmd: Git command sequence to execute
        cwd: Working directory (Path or str)
        env: Environment variables
        timeout: Timeout in seconds (defaults to timeouts.git_operations_seconds)
        capture_output: Capture stdout/stderr
        text: Return output as text instead of bytes
        check: Raise CalledProcessError on non-zero exit

    Returns:
        CompletedProcess from subprocess.run
    """
    if not allow_branch_switch and cmd and cmd[0] == "git":
        # Edison must never change branches via checkout/switch. All branch creation
        # happens through `git worktree add -b ...` (session worktrees).
        for token in cmd[1:]:
            if token in {"checkout", "switch"}:
                raise ValueError(
                    "Forbidden git branch switch detected (checkout/switch). "
                    "Edison must not change branches; use Edison worktree/session CLIs instead."
                )

    timeout_config = TimeoutsConfig(repo_root=Path(cwd) if cwd else None)
    default_timeout = timeout_config.git_operations_seconds

    return run_command(
        cmd,
        cwd=cwd,
        env=env,
        timeout=timeout if timeout is not None else default_timeout,
        capture_output=capture_output,
        text=text,
        check=check,
    )


def run_db_command(
    cmd: Sequence[str],
    *,
    cwd: Optional[Path | str] = None,
    env: Optional[MutableMapping[str, str]] = None,
    timeout: Optional[float] = None,
    capture_output: bool = False,
    text: bool = True,
    check: bool = False,
) -> subprocess.CompletedProcess:
    """
    Run a database-related command using the config-driven timeout bucket.

    Args:
        cmd: Database command sequence to execute
        cwd: Working directory (Path or str)
        env: Environment variables
        timeout: Timeout in seconds (defaults to timeouts.db_operations_seconds)
        capture_output: Capture stdout/stderr
        text: Return output as text instead of bytes
        check: Raise CalledProcessError on non-zero exit

    Returns:
        CompletedProcess from subprocess.run
    """
    timeout_config = TimeoutsConfig(repo_root=Path(cwd) if cwd else None)
    default_timeout = timeout_config.db_operations_seconds

    return run_command(
        cmd,
        cwd=cwd,
        env=env,
        timeout=timeout if timeout is not None else default_timeout,
        capture_output=capture_output,
        text=text,
        check=check,
    )


def run_ci_command_from_string(
    base_cmd: str,
    extra_args: Sequence[str] = (),
    *,
    cwd: Optional[Path | str] = None,
    env: Optional[MutableMapping[str, str]] = None,
    timeout: Optional[float] = None,
    capture_output: bool = False,
    text: bool = True,
    check: bool = False,
    input: Any = None,
) -> subprocess.CompletedProcess:
    """
    Execute a CI command defined as a shell-style string plus extra args.

    The base command is parsed with :mod:`shlex` and never executed via a shell,
    so shell metacharacters in ``extra_args`` are always treated as literals.

    Args:
        base_cmd: Shell-style command string (parsed with shlex)
        extra_args: Additional arguments to append
        cwd: Working directory (Path or str)
        env: Environment variables
        timeout: Timeout in seconds
        capture_output: Capture stdout/stderr
        text: Return output as text instead of bytes
        check: Raise CalledProcessError on non-zero exit

    Returns:
        CompletedProcess from subprocess.run
    """
    argv = shlex.split(base_cmd)
    argv.extend(extra_args)
    return run_command(
        argv,
        cwd=cwd,
        env=env,
        timeout=timeout,
        capture_output=capture_output,
        text=text,
        check=check,
        input=input,
    )


def expand_shell_pipeline(
    cmd: str,
) -> List[List[str]]:
    """
    Parse a limited shell-like command string into one or more argv lists.

    Supports:
    - Simple commands: ``"pnpm lint"``
    - Logical OR: ``"cmd1 || cmd2"``

    Shell metacharacters such as ``;`` are *not* treated as separators to avoid
    command-chaining injection; they are part of arguments instead.

    Args:
        cmd: Shell-style command string

    Returns:
        List of command argument lists
    """
    tokens = shlex.split(cmd)
    if not tokens:
        return []

    segments: List[List[str]] = [[]]
    current = segments[0]

    for tok in tokens:
        if tok == "||":
            if current:
                current = []
                segments.append(current)
            continue
        current.append(tok)

    # Remove any empty segments defensively
    return [seg for seg in segments if seg]


__all__ = [
    "run_with_timeout",
    "configured_timeout",
    "check_output_with_timeout",
    "reset_subprocess_timeout_cache",
    "run_command",
    "run_git_command",
    "run_db_command",
    "run_ci_command_from_string",
    "expand_shell_pipeline",
]
