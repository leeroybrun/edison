"""CLI error handling and structured output.

This module provides structured JSON output schema and CLI error handling
wrapper for Edison CLI commands.

Extracted from the original cli.py god file to follow Single Responsibility Principle.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Callable, Dict, Mapping, Optional

# Import EdisonError for structured error handling
from edison.core.exceptions import EdisonError


def json_output(
    success: bool,
    data: Optional[Mapping[str, Any]] = None,
    error: Optional[Mapping[str, Any] | str | None] = None,
) -> str:
    """Return JSON string matching the standard Edison CLI schema.

    Schema::

        {
          "success": bool,
          "data": {},
          "error": {"message": str, "code": str, "context": {}}
        }

    Args:
        success: Whether the operation succeeded
        data: Success data payload
        error: Error information (dict, string, or None)

    Returns:
        JSON string matching Edison CLI schema
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
    stream=sys.stderr,
) -> int:
    """Emit a structured error for CLI scripts and return a non-zero exit code.

    When ``json_mode`` is True, structured JSON is written to stdout; otherwise a
    human-readable message is written to ``stream`` (stderr by default).

    Args:
        message: Error message
        code: Error code (default: "ERROR")
        json_mode: If True, emit JSON to stdout; otherwise text to stream
        context: Additional error context
        stream: Output stream for text mode (default: stderr)

    Returns:
        Exit code 1
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


def run_cli(
    main: Callable[..., Optional[int]],
    *args: Any,
    json_errors: bool = True,
    **kwargs: Any,
) -> int:
    """Execute a CLI ``main`` function with standardized error handling.

    The wrapped ``main`` is expected to return ``int`` (exit code) or ``None``.
    On success, the return value is passed through as the exit code. On error:

    - :class:`EdisonError` → rendered via :func:`json_output` using
      ``.to_json_error()`` and exit code 1.
    - :class:`KeyboardInterrupt` → rendered as ``CANCELLED`` JSON error.
    - Any other Exception → rendered as ``INTERNAL_ERROR`` with type context.

    The helper *does not* call :func:`sys.exit` directly; callers should wrap
    it in ``sys.exit(run_cli(main))`` at the CLI entrypoint.

    Args:
        main: The main CLI function to execute
        *args: Positional arguments to pass to main
        json_errors: If True, emit JSON errors; otherwise text
        **kwargs: Keyword arguments to pass to main

    Returns:
        Exit code (0 for success, non-zero for error)
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


__all__ = [
    "json_output",
    "cli_error",
    "run_cli",
]



