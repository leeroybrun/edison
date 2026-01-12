from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Literal
from urllib.parse import urlparse

from edison.core.utils.locks.named import (
    LockScope,
    NamedLockConfig,
    parse_named_lock_config,
)

VerifyStepKind = Literal["http", "command", "docker_source", "process_cwd"]


@dataclass(frozen=True)
class WebServerVerifyStep:
    kind: VerifyStepKind
    url: str | None = None
    command: str | None = None
    timeout_seconds: float | None = None
    # docker_source
    container: str | None = None
    mount_dest: str | None = None
    # process_cwd
    pattern: str | None = None


@dataclass(frozen=True)
class WebServerVerifyConfig:
    steps: list[WebServerVerifyStep] = field(default_factory=list)


@dataclass(frozen=True)
class WebServerStartConfig:
    command: str | None = None
    cwd: str | None = None
    success_exit_codes: list[int] = field(default_factory=lambda: [0])


@dataclass(frozen=True)
class WebServerStopConfig:
    command: str | None = None
    cwd: str | None = None
    run_even_if_no_process: bool = True


WebServerLockScope = LockScope
WebServerLockConfig = NamedLockConfig


_LEGACY_WEB_SERVER_KEY_HINTS: dict[str, str] = {
    "base_url": "web_server.url",
    "baseUrl": "web_server.url",
    "healthcheck": "web_server.healthcheck_url",
    "healthcheckUrl": "web_server.healthcheck_url",
    "ensureRunning": "web_server.ensure_running",
    "stopAfter": "web_server.stop_after",
    "startupTimeoutSeconds": "web_server.startup_timeout_seconds",
    "shutdownTimeoutSeconds": "web_server.shutdown_timeout_seconds",
    "probeTimeoutSeconds": "web_server.probe_timeout_seconds",
    "pollIntervalSeconds": "web_server.poll_interval_seconds",
    "start_command": "web_server.start.command",
    "startCommand": "web_server.start.command",
    "stop_command": "web_server.stop.command",
    "stopCommand": "web_server.stop.command",
}


def _raise_on_legacy_keys(raw: dict[str, Any]) -> None:
    found: list[str] = []
    for key in _LEGACY_WEB_SERVER_KEY_HINTS.keys():
        if key not in raw:
            continue
        val = raw.get(key)
        if val is None:
            continue
        if isinstance(val, str) and not val.strip():
            continue
        found.append(key)

    if not found:
        return

    hints = ", ".join(f"{k} → {_LEGACY_WEB_SERVER_KEY_HINTS[k]}" for k in found)
    raise ValueError(f"Unsupported legacy web_server keys: {hints}")


@dataclass(frozen=True)
class WebServerConfig:
    """Configuration for ensuring a validator web server/stack is correct."""

    url: str
    ensure_running: bool = False
    healthcheck_url: str | None = None
    cwd: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    startup_timeout_seconds: float = 60.0
    shutdown_timeout_seconds: float = 10.0
    probe_timeout_seconds: float = 0.75
    poll_interval_seconds: float = 0.25
    stop_after: bool = True

    start: WebServerStartConfig = field(default_factory=WebServerStartConfig)
    stop: WebServerStopConfig = field(default_factory=WebServerStopConfig)
    verify: WebServerVerifyConfig = field(default_factory=WebServerVerifyConfig)
    lock: WebServerLockConfig = field(default_factory=WebServerLockConfig)

    @classmethod
    def from_raw(cls, raw: Any) -> WebServerConfig | None:
        if not isinstance(raw, dict):
            return None

        _raise_on_legacy_keys(raw)

        url_raw = raw.get("url")
        url = os.path.expandvars(str(url_raw or "").strip())
        if not url:
            return None

        health_raw = raw.get("healthcheck_url")
        healthcheck_url = (
            os.path.expandvars(str(health_raw).strip()) if health_raw is not None else None
        )

        ensure_running = bool(raw.get("ensure_running", False))
        stop_after = bool(raw.get("stop_after", True))

        cwd_raw = raw.get("cwd")
        cwd = os.path.expandvars(str(cwd_raw).strip()) if cwd_raw is not None else None
        if cwd == "":
            cwd = None

        env: dict[str, str] = {}
        env_raw = raw.get("env")
        if isinstance(env_raw, dict):
            env = {str(k): os.path.expandvars(str(v)) for k, v in env_raw.items()}

        def _as_float(v: Any, default: float) -> float:
            try:
                if v is None:
                    return float(default)
                return float(v)
            except Exception:
                return float(default)

        start_cfg = _parse_start_config(raw)
        stop_cfg = _parse_stop_config(raw)
        verify_cfg = _parse_verify_config(raw)
        lock_cfg = _parse_lock_config(raw)

        return cls(
            url=url,
            ensure_running=ensure_running,
            healthcheck_url=healthcheck_url,
            cwd=cwd,
            env=env,
            startup_timeout_seconds=_as_float(
                raw.get("startup_timeout_seconds"), 60.0
            ),
            shutdown_timeout_seconds=_as_float(
                raw.get("shutdown_timeout_seconds"), 10.0
            ),
            probe_timeout_seconds=_as_float(
                raw.get("probe_timeout_seconds"), 0.75
            ),
            poll_interval_seconds=_as_float(
                raw.get("poll_interval_seconds"), 0.25
            ),
            stop_after=stop_after,
            start=start_cfg,
            stop=stop_cfg,
            verify=verify_cfg,
            lock=lock_cfg,
        )

    @property
    def probe_url(self) -> str:
        return self.healthcheck_url or self.url

    @property
    def port(self) -> int | None:
        try:
            parsed = urlparse(self.url)
            return parsed.port
        except Exception:
            return None


@dataclass
class WebServerHandle:
    config: WebServerConfig
    process_pid: int | None
    started_by_us: bool


def _parse_start_config(raw: dict[str, Any]) -> WebServerStartConfig:
    start = raw.get("start")
    command: str | None = None
    cwd: str | None = None
    success_exit_codes: list[int] = [0]

    if isinstance(start, str):
        command = os.path.expandvars(start.strip()) or None
    elif isinstance(start, dict):
        if "successExitCodes" in start:
            raise ValueError(
                "Unsupported legacy web_server.start key: successExitCodes (use success_exit_codes)"
            )
        cmd = start.get("command")
        command = os.path.expandvars(str(cmd).strip()) if cmd is not None else None
        if command == "":
            command = None
        cwd_raw = start.get("cwd")
        cwd = os.path.expandvars(str(cwd_raw).strip()) if cwd_raw is not None else None
        if cwd == "":
            cwd = None
        codes = start.get("success_exit_codes")
        if isinstance(codes, list) and all(isinstance(x, int) for x in codes):
            success_exit_codes = list(codes)

    return WebServerStartConfig(command=command, cwd=cwd, success_exit_codes=success_exit_codes)


def _parse_stop_config(raw: dict[str, Any]) -> WebServerStopConfig:
    stop = raw.get("stop")
    command: str | None = None
    cwd: str | None = None
    run_even_if_no_process = True

    if isinstance(stop, str):
        command = os.path.expandvars(stop.strip()) or None
    elif isinstance(stop, dict):
        if "runEvenIfNoProcess" in stop:
            raise ValueError(
                "Unsupported legacy web_server.stop key: runEvenIfNoProcess (use run_even_if_no_process)"
            )
        cmd = stop.get("command")
        command = os.path.expandvars(str(cmd).strip()) if cmd is not None else None
        if command == "":
            command = None
        cwd_raw = stop.get("cwd")
        cwd = os.path.expandvars(str(cwd_raw).strip()) if cwd_raw is not None else None
        if cwd == "":
            cwd = None
        run_even_if_no_process = bool(stop.get("run_even_if_no_process", True))

    return WebServerStopConfig(
        command=command,
        cwd=cwd,
        run_even_if_no_process=run_even_if_no_process,
    )


def _parse_verify_config(raw: dict[str, Any]) -> WebServerVerifyConfig:
    verify = raw.get("verify")
    steps_raw = None
    if isinstance(verify, dict):
        steps_raw = verify.get("steps")

    steps: list[WebServerVerifyStep] = []
    if isinstance(steps_raw, list):
        for item in steps_raw:
            if not isinstance(item, dict):
                continue
            kind = str(item.get("kind") or "").strip()
            if kind not in {"http", "command", "docker_source", "process_cwd"}:
                continue
            if "mountDest" in item:
                raise ValueError(
                    "Unsupported legacy web_server.verify.steps[*] key: mountDest (use mount_dest)"
                )
            timeout = item.get("timeout_seconds", item.get("timeoutSeconds"))
            timeout_seconds: float | None = None
            if timeout is not None:
                try:
                    timeout_seconds = float(timeout)
                except Exception:
                    timeout_seconds = None

            steps.append(
                WebServerVerifyStep(
                    kind=kind,  # type: ignore[arg-type]
                    url=str(item.get("url")).strip() if item.get("url") is not None else None,
                    command=str(item.get("command")).strip()
                    if item.get("command") is not None
                    else None,
                    timeout_seconds=timeout_seconds,
                    container=str(item.get("container")).strip()
                    if item.get("container") is not None
                    else None,
                    mount_dest=str(item.get("mount_dest")).strip()
                    if item.get("mount_dest") is not None
                    else None,
                    pattern=str(item.get("pattern")).strip()
                    if item.get("pattern") is not None
                    else None,
                )
            )

    return WebServerVerifyConfig(steps=steps)


def _parse_lock_config(raw: dict[str, Any]) -> WebServerLockConfig:
    lock_raw = raw.get("lock")
    if isinstance(lock_raw, dict):
        if "timeoutSeconds" in lock_raw:
            raise ValueError(
                "Unsupported legacy web_server.lock key: timeoutSeconds (use timeout_seconds)"
            )
        if "lockScope" in lock_raw or "lock_scope" in lock_raw:
            raise ValueError("Unsupported legacy web_server.lock key: lockScope (use scope)")
    return parse_named_lock_config(lock_raw)
