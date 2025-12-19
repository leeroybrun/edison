from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

from edison.core.utils.io import ensure_directory


_CONFIGURED_LOG_PATH: Optional[str] = None
_EDISON_FILE_HANDLER: Optional[logging.Handler] = None


def _level_from_name(name: str) -> int:
    try:
        return int(getattr(logging, name.upper()))
    except Exception:
        return logging.INFO


def configure_stdlib_logging(*, log_path: Path, level: str = "INFO") -> None:
    """Configure Python stdlib logging to write to `log_path` (no stderr handler).

    Idempotent per-process: if already configured for the same file, no-op.
    """
    global _CONFIGURED_LOG_PATH, _EDISON_FILE_HANDLER

    resolved = str(Path(log_path).resolve())
    if _CONFIGURED_LOG_PATH == resolved and _EDISON_FILE_HANDLER is not None:
        return

    ensure_directory(Path(resolved).parent)

    root = logging.getLogger()
    root.setLevel(_level_from_name(level))

    # Remove stdout/stderr stream handlers to avoid polluting stdout/stderr (JSON purity).
    #
    # IMPORTANT: FileHandler is also a StreamHandler, so we must only remove the
    # stdout/stderr handlers, not file-based logging handlers.
    for h in list(root.handlers):
        if isinstance(h, logging.StreamHandler) and getattr(h, "stream", None) in (sys.stdout, sys.stderr):
            root.removeHandler(h)
            try:
                h.close()
            except Exception:
                pass

    # Replace the Edison-installed file handler when switching paths.
    if _EDISON_FILE_HANDLER is not None:
        try:
            root.removeHandler(_EDISON_FILE_HANDLER)
        except Exception:
            pass
        try:
            _EDISON_FILE_HANDLER.close()
        except Exception:
            pass
        _EDISON_FILE_HANDLER = None

    # Always (re)install a file handler for the requested path.
    fh = logging.FileHandler(resolved, encoding="utf-8")
    fh.setLevel(_level_from_name(level))
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    fh.setFormatter(fmt)
    root.addHandler(fh)

    _EDISON_FILE_HANDLER = fh
    _CONFIGURED_LOG_PATH = resolved


def reset_stdlib_logging_for_tests() -> None:
    """Test-only: clear configured handlers."""
    global _CONFIGURED_LOG_PATH, _EDISON_FILE_HANDLER
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
        try:
            h.close()
        except Exception:
            pass
    _CONFIGURED_LOG_PATH = None
    _EDISON_FILE_HANDLER = None


__all__ = ["configure_stdlib_logging", "reset_stdlib_logging_for_tests"]
