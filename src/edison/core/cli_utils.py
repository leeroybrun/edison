from __future__ import annotations

"""
CLI helpers for Edison core scripts.

Responsibilities:
- Provide a canonical JSON output contract for script entrypoints
- Centralize structured error reporting
- Wrap subprocess invocations with safe defaults (no shell=True) and timeouts
"""

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence

from .exceptions import EdisonError
from edison.core.utils.subprocess import run_with_timeout


# Default timeouts (seconds); can be overridden via environment
DEFAULT_GIT_TIMEOUT = float(os.environ.get("EDISON_GIT_TIMEOUT_SECONDS", "60"))
DEFAULT_DB_TIMEOUT = float(os.environ.get("EDISON_DB_TIMEOUT_SECONDS", "30"))


def json_output(
    success: bool,
    data: Optional[Mapping[str, Any]] = None,
    error: Optional[Mapping[str, Any] | str | None] = None,
) -> str:
    """
    Return JSON string matching the standard Edison CLI schema:

        {
          "success": bool,
          "data": {},
          "error": {"message": str, "code": str, "context": {}}
        }
    """
    data_obj: Dict[str, Any] = dict(data or {})

    if error is None:
        err_obj: Dict[str, Any] = {"message": "", "code": "", "context": {}}
    elif isinstance(error, str):
        err_obj = {"message": error, "code": "", "context": {}}
    else:
        err_obj = {
            "message": str(error.get("message", "")),
            "code": str(error.get("code", "")),
            "context": dict(error.get("context") or {}),
        }

    payload = {
        "success": bool(success),
        "data": data_obj,
        "error": err_obj,
    }
    return json.dumps(payload)


def cli_error(
    message: str,
    code: str = "ERROR",
    json_mode: bool = False,
    *,
    context: Optional[Mapping[str, Any]] = None,
    stream = sys.stderr,
) -> int:
    """
    Emit a structured error for CLI scripts and return a non‑zero exit code.

    When ``json_mode`` is True, structured JSON is written to stdout; otherwise a
    human‑readable message is written to ``stream`` (stderr by default).
    """
    if json_mode:
        payload = json_output(
            success=False,
            data={},
            error={"message": message, "code": code, "context": dict(context or {})},
        )
        print(payload, file=sys.stdout)
    else:
        print(f"{code}: {message}", file=stream)
    return 1


def _to_cwd(cwd: Optional[Path | str]) -> Optional[str]:
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

    - No shell=True
    - Optional timeout
    - Optional capture_output/text/check flags
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
    Run a git command with a default timeout (60s, overridable via env).
    """
    return run_command(
        cmd,
        cwd=cwd,
        env=env,
        timeout=timeout or DEFAULT_GIT_TIMEOUT,
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
    Run a database‑related command with a default timeout (30s, overridable).
    """
    return run_command(
        cmd,
        cwd=cwd,
        env=env,
        timeout=timeout or DEFAULT_DB_TIMEOUT,
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
    Execute a CI command defined as a shell‑style string plus extra args.

    The base command is parsed with :mod:`shlex` and never executed via a shell,
    so shell metacharacters in ``extra_args`` are always treated as literals.
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
    Parse a limited shell‑like command string into one or more argv lists.

    Supports:
    - Simple commands: ``\"pnpm lint\"``
    - Logical OR: ``\"cmd1 || cmd2\"``

    Shell metacharacters such as ``;`` are *not* treated as separators to avoid
    command‑chaining injection; they are part of arguments instead.
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


def run_cli(
    main: Callable[..., Optional[int]],
    *args: Any,
    json_errors: bool = True,
    **kwargs: Any,
) -> int:
    """
    Execute a CLI ``main`` function with standardized error handling.

    The wrapped ``main`` is expected to return ``int`` (exit code) or ``None``.
    On success, the return value is passed through as the exit code. On error:

    - :class:`EdisonError` → rendered via :func:`json_output` using
      ``.to_json_error()`` and exit code 1.
    - :class:`KeyboardInterrupt` → rendered as ``CANCELLED`` JSON error.
    - Any other Exception → rendered as ``INTERNAL_ERROR`` with type context.

    The helper *does not* call :func:`sys.exit` directly; callers should wrap
    it in ``sys.exit(run_cli(main))`` at the CLI entrypoint.
    """
    try:
        result = main(*args, **kwargs)
        return 0 if result is None else int(result)
    except EdisonError as err:  # type: ignore[misc]
        if json_errors:
            payload = json_output(
                success=False,
                data={},
                error=err.to_json_error(),
            )
            print(payload)
        else:
            print(f"{err.__class__.__name__}: {err}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        if json_errors:
            payload = json_output(
                success=False,
                data={},
                error={
                    "message": "Operation cancelled",
                    "code": "CANCELLED",
                    "context": {},
                },
            )
            print(payload)
        else:
            print("Operation cancelled", file=sys.stderr)
        return 1
    except Exception as err:  # noqa: BLE001
        if json_errors:
            payload = json_output(
                success=False,
                data={},
                error={
                    "message": f"Unexpected error: {err}",
                    "code": "INTERNAL_ERROR",
                    "context": {"type": type(err).__name__},
                },
            )
            print(payload)
        else:
            print(f"Unexpected error: {err}", file=sys.stderr)
        return 1