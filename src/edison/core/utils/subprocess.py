from __future__ import annotations

"""Subprocess helpers with config-driven timeouts and command wrappers.

This module provides safe subprocess execution with:
- Config-driven timeout management
- Command wrappers for common operations (git, db, CI)
- Shell pipeline parsing
- No shell=True by default (security)
"""

import shlex
import subprocess
from pathlib import Path
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

    return subprocess.run(cmd, timeout=timeout, **kwargs)


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
