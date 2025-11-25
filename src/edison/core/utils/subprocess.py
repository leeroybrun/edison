from __future__ import annotations

"""Subprocess helpers with config-driven timeouts."""

import shlex
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any, Iterable, Sequence

FALLBACK_TIMEOUTS: Dict[str, float] = {
    "git_operations": 30.0,
    "test_execution": 300.0,
    "build_operations": 600.0,
    "ai_calls": 120.0,
    "file_operations": 10.0,
    "default": 60.0,
}


def _resolve_repo_root(cwd: Path | str | None = None) -> Path:
    from ..paths import resolver as paths_resolver  # Lazy to avoid import cycle

    if cwd is not None:
        try:
            return Path(cwd).resolve()
        except Exception:
            pass
    try:
        return paths_resolver.PathResolver.resolve_project_root()
    except Exception:
        return Path.cwd().resolve()


@lru_cache(maxsize=4)
def _load_timeouts(repo_root: Path) -> Dict[str, float]:
    """Load timeout configuration with fallbacks.

    Values are sourced from YAML configuration, falling back to the baked-in
    defaults when config is missing or malformed.
    """
    timeouts: Dict[str, float] = dict(FALLBACK_TIMEOUTS)
    try:
        # Local import to avoid optional dependency errors when running in
        # stripped environments.
        from ..config import ConfigManager  # type: ignore

        cfg = ConfigManager(repo_root).load_config(validate=False)  # type: ignore[arg-type]
        configured = cfg.get("subprocess_timeouts") or {}
        for key, value in configured.items():
            try:
                timeouts[key] = float(value)
            except Exception:
                continue
    except Exception:
        # Fall back silently to baked-in defaults
        pass
    return timeouts


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
    repo_root = _resolve_repo_root(cwd)
    timeouts = _load_timeouts(repo_root)

    ttype = timeout_type or _infer_timeout_type(cmd)
    timeout = timeouts.get(ttype, timeouts.get("default"))
    if timeout is None:
        raise RuntimeError(f"Timeout not configured for type '{ttype}'")
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
    _load_timeouts.cache_clear()


__all__ = ["run_with_timeout", "configured_timeout", "check_output_with_timeout", "reset_subprocess_timeout_cache"]
