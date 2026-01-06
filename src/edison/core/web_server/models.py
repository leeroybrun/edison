from __future__ import annotations

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

        url_raw = raw.get("url", raw.get("base_url", raw.get("baseUrl")))
        url = str(url_raw or "").strip()
        if not url:
            return None

        health_raw = raw.get(
            "healthcheck_url", raw.get("healthcheckUrl", raw.get("healthcheck"))
        )
        healthcheck_url = str(health_raw).strip() if health_raw is not None else None

        ensure_running = bool(raw.get("ensure_running", raw.get("ensureRunning", False)))
        stop_after = bool(raw.get("stop_after", raw.get("stopAfter", True)))

        cwd_raw = raw.get("cwd")
        cwd = str(cwd_raw).strip() if cwd_raw is not None else None
        if cwd == "":
            cwd = None

        env: dict[str, str] = {}
        env_raw = raw.get("env")
        if isinstance(env_raw, dict):
            env = {str(k): str(v) for k, v in env_raw.items()}

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
                raw.get("startup_timeout_seconds", raw.get("startupTimeoutSeconds")), 60.0
            ),
            shutdown_timeout_seconds=_as_float(
                raw.get("shutdown_timeout_seconds", raw.get("shutdownTimeoutSeconds")), 10.0
            ),
            probe_timeout_seconds=_as_float(
                raw.get("probe_timeout_seconds", raw.get("probeTimeoutSeconds")), 0.75
            ),
            poll_interval_seconds=_as_float(
                raw.get("poll_interval_seconds", raw.get("pollIntervalSeconds")), 0.25
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
        command = start.strip() or None
    elif isinstance(start, dict):
        cmd = start.get("command")
        command = str(cmd).strip() if cmd is not None else None
        if command == "":
            command = None
        cwd_raw = start.get("cwd")
        cwd = str(cwd_raw).strip() if cwd_raw is not None else None
        if cwd == "":
            cwd = None
        codes = start.get("success_exit_codes", start.get("successExitCodes"))
        if isinstance(codes, list) and all(isinstance(x, int) for x in codes):
            success_exit_codes = list(codes)

    # Legacy support
    if command is None:
        start_raw = raw.get("start_command", raw.get("startCommand"))
        command = str(start_raw).strip() if start_raw is not None else None
        if command == "":
            command = None

    return WebServerStartConfig(command=command, cwd=cwd, success_exit_codes=success_exit_codes)


def _parse_stop_config(raw: dict[str, Any]) -> WebServerStopConfig:
    stop = raw.get("stop")
    command: str | None = None
    cwd: str | None = None
    run_even_if_no_process = True

    if isinstance(stop, str):
        command = stop.strip() or None
    elif isinstance(stop, dict):
        cmd = stop.get("command")
        command = str(cmd).strip() if cmd is not None else None
        if command == "":
            command = None
        cwd_raw = stop.get("cwd")
        cwd = str(cwd_raw).strip() if cwd_raw is not None else None
        if cwd == "":
            cwd = None
        run_even_if_no_process = bool(
            stop.get("run_even_if_no_process", stop.get("runEvenIfNoProcess", True))
        )

    # Legacy support
    if command is None:
        stop_raw = raw.get("stop_command", raw.get("stopCommand"))
        command = str(stop_raw).strip() if stop_raw is not None else None
        if command == "":
            command = None

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
                    mount_dest=str(item.get("mount_dest", item.get("mountDest"))).strip()
                    if (item.get("mount_dest") is not None or item.get("mountDest") is not None)
                    else None,
                    pattern=str(item.get("pattern")).strip()
                    if item.get("pattern") is not None
                    else None,
                )
            )

    return WebServerVerifyConfig(steps=steps)


def _parse_lock_config(raw: dict[str, Any]) -> WebServerLockConfig:
    return parse_named_lock_config(raw.get("lock"))
