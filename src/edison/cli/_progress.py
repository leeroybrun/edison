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
from typing import Any, Callable, Iterator, TextIO


@dataclass(frozen=True)
class CliProgressConfig:
    enabled: bool
    threshold_seconds: float
    interval_seconds: float
    max_interval_seconds: float = 120.0
    backoff_multiplier: float = 2.0
    idle_seconds: float = 5.0
    show_command_once: bool = False
    show_next_update: bool = True


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
    return CliProgressConfig(
        enabled=True,
        threshold_seconds=8.0,
        interval_seconds=15.0,
        max_interval_seconds=120.0,
        backoff_multiplier=2.0,
        idle_seconds=5.0,
        show_command_once=False,
        show_next_update=True,
    )


def _load_cli_progress_config(*, project_root: Path | None) -> CliProgressConfig:
    """Resolve cli.progress configuration (env overrides first, then config)."""
    cfg = _default_config()

    env_enabled = _parse_bool(os.environ.get("EDISON_CLI_PROGRESS"))
    env_threshold = _parse_float(os.environ.get("EDISON_CLI_PROGRESS_THRESHOLD_SECONDS"))
    env_interval = _parse_float(os.environ.get("EDISON_CLI_PROGRESS_INTERVAL_SECONDS"))
    env_max_interval = _parse_float(os.environ.get("EDISON_CLI_PROGRESS_MAX_INTERVAL_SECONDS"))
    env_backoff_multiplier = _parse_float(os.environ.get("EDISON_CLI_PROGRESS_BACKOFF_MULTIPLIER"))
    env_idle = _parse_float(os.environ.get("EDISON_CLI_PROGRESS_IDLE_SECONDS"))
    env_show_command_once = _parse_bool(os.environ.get("EDISON_CLI_PROGRESS_SHOW_COMMAND_ONCE"))
    env_show_next_update = _parse_bool(os.environ.get("EDISON_CLI_PROGRESS_SHOW_NEXT_UPDATE"))

    if project_root is not None:
        try:
            from edison.core.config import ConfigManager

            raw = ConfigManager(repo_root=project_root).load_config(validate=False)
            cli = raw.get("cli") if isinstance(raw.get("cli"), dict) else {}
            progress = cli.get("progress") if isinstance(cli.get("progress"), dict) else {}

            enabled = _parse_bool(progress.get("enabled"))
            threshold = _parse_float(progress.get("threshold_seconds"))
            interval = _parse_float(progress.get("interval_seconds"))
            max_interval = _parse_float(progress.get("max_interval_seconds"))
            backoff_multiplier = _parse_float(progress.get("backoff_multiplier"))
            idle = _parse_float(progress.get("idle_seconds"))
            show_command_once = _parse_bool(progress.get("show_command_once"))
            show_next_update = _parse_bool(progress.get("show_next_update"))

            if enabled is not None:
                cfg = CliProgressConfig(
                    enabled=enabled,
                    threshold_seconds=cfg.threshold_seconds,
                    interval_seconds=cfg.interval_seconds,
                    max_interval_seconds=cfg.max_interval_seconds,
                    backoff_multiplier=cfg.backoff_multiplier,
                    idle_seconds=cfg.idle_seconds,
                    show_command_once=cfg.show_command_once,
                    show_next_update=cfg.show_next_update,
                )
            if threshold is not None and threshold > 0:
                cfg = CliProgressConfig(
                    enabled=cfg.enabled,
                    threshold_seconds=threshold,
                    interval_seconds=cfg.interval_seconds,
                    max_interval_seconds=cfg.max_interval_seconds,
                    backoff_multiplier=cfg.backoff_multiplier,
                    idle_seconds=cfg.idle_seconds,
                    show_command_once=cfg.show_command_once,
                    show_next_update=cfg.show_next_update,
                )
            if interval is not None and interval > 0:
                cfg = CliProgressConfig(
                    enabled=cfg.enabled,
                    threshold_seconds=cfg.threshold_seconds,
                    interval_seconds=interval,
                    max_interval_seconds=max(cfg.max_interval_seconds, interval),
                    backoff_multiplier=cfg.backoff_multiplier,
                    idle_seconds=cfg.idle_seconds,
                    show_command_once=cfg.show_command_once,
                    show_next_update=cfg.show_next_update,
                )
            if max_interval is not None and max_interval > 0:
                cfg = CliProgressConfig(
                    enabled=cfg.enabled,
                    threshold_seconds=cfg.threshold_seconds,
                    interval_seconds=min(cfg.interval_seconds, max_interval),
                    max_interval_seconds=max_interval,
                    backoff_multiplier=cfg.backoff_multiplier,
                    idle_seconds=cfg.idle_seconds,
                    show_command_once=cfg.show_command_once,
                    show_next_update=cfg.show_next_update,
                )
            if backoff_multiplier is not None and backoff_multiplier >= 1.0:
                cfg = CliProgressConfig(
                    enabled=cfg.enabled,
                    threshold_seconds=cfg.threshold_seconds,
                    interval_seconds=cfg.interval_seconds,
                    max_interval_seconds=cfg.max_interval_seconds,
                    backoff_multiplier=backoff_multiplier,
                    idle_seconds=cfg.idle_seconds,
                    show_command_once=cfg.show_command_once,
                    show_next_update=cfg.show_next_update,
                )
            if idle is not None and idle >= 0.0:
                cfg = CliProgressConfig(
                    enabled=cfg.enabled,
                    threshold_seconds=cfg.threshold_seconds,
                    interval_seconds=cfg.interval_seconds,
                    max_interval_seconds=cfg.max_interval_seconds,
                    backoff_multiplier=cfg.backoff_multiplier,
                    idle_seconds=idle,
                    show_command_once=cfg.show_command_once,
                    show_next_update=cfg.show_next_update,
                )
            if show_command_once is not None:
                cfg = CliProgressConfig(
                    enabled=cfg.enabled,
                    threshold_seconds=cfg.threshold_seconds,
                    interval_seconds=cfg.interval_seconds,
                    max_interval_seconds=cfg.max_interval_seconds,
                    backoff_multiplier=cfg.backoff_multiplier,
                    idle_seconds=cfg.idle_seconds,
                    show_command_once=show_command_once,
                    show_next_update=cfg.show_next_update,
                )
            if show_next_update is not None:
                cfg = CliProgressConfig(
                    enabled=cfg.enabled,
                    threshold_seconds=cfg.threshold_seconds,
                    interval_seconds=cfg.interval_seconds,
                    max_interval_seconds=cfg.max_interval_seconds,
                    backoff_multiplier=cfg.backoff_multiplier,
                    idle_seconds=cfg.idle_seconds,
                    show_command_once=cfg.show_command_once,
                    show_next_update=show_next_update,
                )
        except Exception:
            pass

    if env_enabled is not None:
        cfg = CliProgressConfig(
            enabled=env_enabled,
            threshold_seconds=cfg.threshold_seconds,
            interval_seconds=cfg.interval_seconds,
            max_interval_seconds=cfg.max_interval_seconds,
            backoff_multiplier=cfg.backoff_multiplier,
            idle_seconds=cfg.idle_seconds,
            show_command_once=cfg.show_command_once,
            show_next_update=cfg.show_next_update,
        )
    if env_threshold is not None and env_threshold > 0:
        cfg = CliProgressConfig(
            enabled=cfg.enabled,
            threshold_seconds=env_threshold,
            interval_seconds=cfg.interval_seconds,
            max_interval_seconds=cfg.max_interval_seconds,
            backoff_multiplier=cfg.backoff_multiplier,
            idle_seconds=cfg.idle_seconds,
            show_command_once=cfg.show_command_once,
            show_next_update=cfg.show_next_update,
        )
    if env_interval is not None and env_interval > 0:
        cfg = CliProgressConfig(
            enabled=cfg.enabled,
            threshold_seconds=cfg.threshold_seconds,
            interval_seconds=env_interval,
            max_interval_seconds=max(cfg.max_interval_seconds, env_interval),
            backoff_multiplier=cfg.backoff_multiplier,
            idle_seconds=cfg.idle_seconds,
            show_command_once=cfg.show_command_once,
            show_next_update=cfg.show_next_update,
        )
    if env_max_interval is not None and env_max_interval > 0:
        cfg = CliProgressConfig(
            enabled=cfg.enabled,
            threshold_seconds=cfg.threshold_seconds,
            interval_seconds=min(cfg.interval_seconds, env_max_interval),
            max_interval_seconds=env_max_interval,
            backoff_multiplier=cfg.backoff_multiplier,
            idle_seconds=cfg.idle_seconds,
            show_command_once=cfg.show_command_once,
            show_next_update=cfg.show_next_update,
        )
    if env_backoff_multiplier is not None and env_backoff_multiplier >= 1.0:
        cfg = CliProgressConfig(
            enabled=cfg.enabled,
            threshold_seconds=cfg.threshold_seconds,
            interval_seconds=cfg.interval_seconds,
            max_interval_seconds=cfg.max_interval_seconds,
            backoff_multiplier=env_backoff_multiplier,
            idle_seconds=cfg.idle_seconds,
            show_command_once=cfg.show_command_once,
            show_next_update=cfg.show_next_update,
        )
    if env_idle is not None and env_idle >= 0.0:
        cfg = CliProgressConfig(
            enabled=cfg.enabled,
            threshold_seconds=cfg.threshold_seconds,
            interval_seconds=cfg.interval_seconds,
            max_interval_seconds=cfg.max_interval_seconds,
            backoff_multiplier=cfg.backoff_multiplier,
            idle_seconds=env_idle,
            show_command_once=cfg.show_command_once,
            show_next_update=cfg.show_next_update,
        )
    if env_show_command_once is not None:
        cfg = CliProgressConfig(
            enabled=cfg.enabled,
            threshold_seconds=cfg.threshold_seconds,
            interval_seconds=cfg.interval_seconds,
            max_interval_seconds=cfg.max_interval_seconds,
            backoff_multiplier=cfg.backoff_multiplier,
            idle_seconds=cfg.idle_seconds,
            show_command_once=env_show_command_once,
            show_next_update=cfg.show_next_update,
        )
    if env_show_next_update is not None:
        cfg = CliProgressConfig(
            enabled=cfg.enabled,
            threshold_seconds=cfg.threshold_seconds,
            interval_seconds=cfg.interval_seconds,
            max_interval_seconds=cfg.max_interval_seconds,
            backoff_multiplier=cfg.backoff_multiplier,
            idle_seconds=cfg.idle_seconds,
            show_command_once=cfg.show_command_once,
            show_next_update=env_show_next_update,
        )

    return cfg


def _format_duration(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0

    if seconds < 1.0:
        ms = int(round(seconds * 1000.0))
        if ms <= 0:
            ms = 1
        return f"{ms}ms"

    total_seconds = int(round(seconds))
    if total_seconds < 60:
        return f"{total_seconds}s"

    minutes, remaining = divmod(total_seconds, 60)
    if minutes < 60:
        return f"{minutes}m{remaining:02d}s"

    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}m"


class _ActivityTrackingTextIO:
    def __init__(self, underlying: TextIO, mark_activity: Callable[[], None]) -> None:
        self._underlying = underlying
        self._mark_activity = mark_activity

    def write(self, s: str) -> int:
        self._mark_activity()
        return self._underlying.write(s)

    def writelines(self, lines: list[str]) -> None:
        self._mark_activity()
        return self._underlying.writelines(lines)

    def flush(self) -> None:
        return self._underlying.flush()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._underlying, name)


def _heartbeat(
    *,
    stop: threading.Event,
    started_at: float,
    command_name: str,
    argv: list[str],
    config: CliProgressConfig,
    last_activity_at: list[float],
    last_activity_lock: threading.Lock,
    stderr: TextIO,
) -> None:
    # Wait until threshold; bail early if completed.
    if stop.wait(timeout=max(0.0, float(config.threshold_seconds))):
        return

    current_interval = max(0.001, float(config.interval_seconds))
    max_interval = max(current_interval, float(config.max_interval_seconds))
    multiplier = max(1.0, float(config.backoff_multiplier))
    idle_seconds = max(0.0, float(config.idle_seconds))
    show_command_remaining = bool(config.show_command_once)

    next_emit_at = time.monotonic()
    while not stop.is_set():
        now = time.monotonic()
        if now < next_emit_at:
            stop.wait(timeout=max(0.001, min(1.0, next_emit_at - now)))
            continue

        with last_activity_lock:
            last_activity = last_activity_at[0]

        if idle_seconds > 0.0 and (now - last_activity) < idle_seconds:
            next_emit_at = max(next_emit_at, last_activity + idle_seconds)
            stop.wait(timeout=max(0.001, min(1.0, next_emit_at - now)))
            continue

        elapsed = now - started_at
        line = f"[edison] still running ({_format_duration(elapsed)}): {command_name} — please wait"

        extras: list[str] = []
        if config.show_next_update:
            extras.append(f"next update in {_format_duration(current_interval)}")
        if show_command_remaining:
            extras.append(f"command: {' '.join(argv)}")
            show_command_remaining = False
        if extras:
            line += f" ({'; '.join(extras)})"

        print(line, file=stderr, flush=True)

        next_emit_at = now + current_interval
        current_interval = min(max_interval, current_interval * multiplier)


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

    last_activity_lock = threading.Lock()
    last_activity_at = [time.monotonic()]

    def _mark_activity() -> None:
        with last_activity_lock:
            last_activity_at[0] = time.monotonic()

    original_stdout = sys.stdout
    original_stderr = sys.stderr

    if resolved.idle_seconds > 0.0:
        sys.stdout = _ActivityTrackingTextIO(original_stdout, _mark_activity)
        sys.stderr = _ActivityTrackingTextIO(original_stderr, _mark_activity)

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
            "last_activity_at": last_activity_at,
            "last_activity_lock": last_activity_lock,
            "stderr": original_stderr,
        },
        daemon=True,
    )
    t.start()
    try:
        yield
    finally:
        stop.set()
        t.join(timeout=1.0)
        sys.stdout = original_stdout
        sys.stderr = original_stderr


__all__ = ["CliProgressConfig", "cli_progress"]
