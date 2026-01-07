"""CLI progress helpers.

Purpose: prevent users/LLMs from assuming Edison has hung during long-running
commands (validation, evidence capture, session create, etc.).

Design goals:
- stderr-only (never pollute stdout/JSON)
- threshold-based (avoid noise for fast commands)
- configurable via config + env overrides
"""

from __future__ import annotations

import os
import sys
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


@dataclass(frozen=True)
class CliProgressConfig:
    enabled: bool
    threshold_seconds: float
    interval_seconds: float


def _parse_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        s = value.strip().lower()
        if s in {"1", "true", "yes", "on"}:
            return True
        if s in {"0", "false", "no", "off"}:
            return False
    return None


def _parse_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _default_config() -> CliProgressConfig:
    # Conservative defaults: quiet for fast commands, helpful for slow ones.
    return CliProgressConfig(enabled=True, threshold_seconds=8.0, interval_seconds=15.0)


def _load_cli_progress_config(*, project_root: Path | None) -> CliProgressConfig:
    """Resolve cli.progress configuration (env overrides first, then config)."""
    cfg = _default_config()

    env_enabled = _parse_bool(os.environ.get("EDISON_CLI_PROGRESS"))
    env_threshold = _parse_float(os.environ.get("EDISON_CLI_PROGRESS_THRESHOLD_SECONDS"))
    env_interval = _parse_float(os.environ.get("EDISON_CLI_PROGRESS_INTERVAL_SECONDS"))

    if project_root is not None:
        try:
            from edison.core.config import ConfigManager

            raw = ConfigManager(repo_root=project_root).load_config(validate=False)
            cli = raw.get("cli") if isinstance(raw.get("cli"), dict) else {}
            progress = cli.get("progress") if isinstance(cli.get("progress"), dict) else {}

            enabled = _parse_bool(progress.get("enabled"))
            threshold = _parse_float(progress.get("threshold_seconds"))
            interval = _parse_float(progress.get("interval_seconds"))

            if enabled is not None:
                cfg = CliProgressConfig(enabled=enabled, threshold_seconds=cfg.threshold_seconds, interval_seconds=cfg.interval_seconds)
            if threshold is not None and threshold > 0:
                cfg = CliProgressConfig(enabled=cfg.enabled, threshold_seconds=threshold, interval_seconds=cfg.interval_seconds)
            if interval is not None and interval > 0:
                cfg = CliProgressConfig(enabled=cfg.enabled, threshold_seconds=cfg.threshold_seconds, interval_seconds=interval)
        except Exception:
            pass

    if env_enabled is not None:
        cfg = CliProgressConfig(enabled=env_enabled, threshold_seconds=cfg.threshold_seconds, interval_seconds=cfg.interval_seconds)
    if env_threshold is not None and env_threshold > 0:
        cfg = CliProgressConfig(enabled=cfg.enabled, threshold_seconds=env_threshold, interval_seconds=cfg.interval_seconds)
    if env_interval is not None and env_interval > 0:
        cfg = CliProgressConfig(enabled=cfg.enabled, threshold_seconds=cfg.threshold_seconds, interval_seconds=env_interval)

    return cfg


def _heartbeat(
    *,
    stop: threading.Event,
    started_at: float,
    command_name: str,
    argv: list[str],
    config: CliProgressConfig,
) -> None:
    # Wait until threshold; bail early if completed.
    if stop.wait(timeout=max(0.0, float(config.threshold_seconds))):
        return

    while not stop.is_set():
        elapsed = time.monotonic() - started_at
        args = " ".join(argv)
        print(
            f"[edison] still running ({elapsed:.0f}s): {command_name} ({args})",
            file=sys.stderr,
            flush=True,
        )
        stop.wait(timeout=max(0.1, float(config.interval_seconds)))


@contextmanager
def cli_progress(
    *,
    command_name: str,
    argv: list[str],
    project_root: Path | None = None,
    json_mode: bool = False,
    config: CliProgressConfig | None = None,
) -> Iterator[None]:
    """Emit periodic stderr progress for long-running commands."""
    if json_mode:
        yield
        return

    resolved = config or _load_cli_progress_config(project_root=project_root)
    if not resolved.enabled:
        yield
        return

    stop = threading.Event()
    started_at = time.monotonic()
    t = threading.Thread(
        target=_heartbeat,
        kwargs={
            "stop": stop,
            "started_at": started_at,
            "command_name": command_name,
            "argv": list(argv),
            "config": resolved,
        },
        daemon=True,
    )
    t.start()
    try:
        yield
    finally:
        stop.set()
        t.join(timeout=1.0)


__all__ = ["CliProgressConfig", "cli_progress"]

