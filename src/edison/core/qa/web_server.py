"""Web server guard utilities for validators.

Some validators (notably browser E2E) need a running web server to validate
real UI behavior. Edison can optionally verify that the server is reachable
and start/stop it around the validator execution when configured.
"""

from __future__ import annotations

import os
import shlex
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class WebServerConfig:
    """Configuration for ensuring a validator web server is running."""

    url: str
    ensure_running: bool = False
    healthcheck_url: str | None = None
    start_command: str | None = None
    stop_command: str | None = None
    cwd: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    startup_timeout_seconds: float = 60.0
    shutdown_timeout_seconds: float = 10.0
    probe_timeout_seconds: float = 0.75
    poll_interval_seconds: float = 0.25
    stop_after: bool = True

    @classmethod
    def from_raw(cls, raw: Any) -> WebServerConfig | None:
        """Parse config from a validator metadata `web_server` dict."""
        if not isinstance(raw, dict):
            return None

        url_raw = raw.get("url", raw.get("base_url", raw.get("baseUrl")))
        url = str(url_raw or "").strip()
        if not url:
            return None

        health_raw = raw.get("healthcheck_url", raw.get("healthcheckUrl", raw.get("healthcheck")))
        healthcheck_url = str(health_raw).strip() if health_raw is not None else None

        start_raw = raw.get("start_command", raw.get("startCommand", raw.get("start")))
        start_command = str(start_raw).strip() if start_raw is not None else None
        if start_command == "":
            start_command = None

        stop_raw = raw.get("stop_command", raw.get("stopCommand", raw.get("stop")))
        stop_command = str(stop_raw).strip() if stop_raw is not None else None
        if stop_command == "":
            stop_command = None

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

        return cls(
            url=url,
            ensure_running=ensure_running,
            healthcheck_url=healthcheck_url,
            start_command=start_command,
            stop_command=stop_command,
            cwd=cwd,
            env=env,
            startup_timeout_seconds=_as_float(raw.get("startup_timeout_seconds", raw.get("startupTimeoutSeconds")), 60.0),
            shutdown_timeout_seconds=_as_float(raw.get("shutdown_timeout_seconds", raw.get("shutdownTimeoutSeconds")), 10.0),
            probe_timeout_seconds=_as_float(raw.get("probe_timeout_seconds", raw.get("probeTimeoutSeconds")), 0.75),
            poll_interval_seconds=_as_float(raw.get("poll_interval_seconds", raw.get("pollIntervalSeconds")), 0.25),
            stop_after=stop_after,
        )

    @property
    def probe_url(self) -> str:
        """URL used to determine if the server is reachable."""
        return self.healthcheck_url or self.url

    @property
    def port(self) -> int | None:
        """Parsed TCP port from `url` (best-effort)."""
        try:
            parsed = urlparse(self.url)
            return parsed.port
        except Exception:
            return None


@dataclass
class WebServerHandle:
    config: WebServerConfig
    process: subprocess.Popen[str] | None
    started_by_us: bool


def _is_http_responsive(url: str, *, timeout_seconds: float) -> bool:
    req = Request(url, method="GET")
    try:
        with urlopen(req, timeout=timeout_seconds):
            return True
    except HTTPError:
        # Any HTTP response implies a server is listening.
        return True
    except URLError:
        return False
    except Exception:
        return False


def _popen_kwargs() -> dict[str, Any]:
    if os.name == "posix":
        return {"start_new_session": True}
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", None)
        if isinstance(creationflags, int):
            return {"creationflags": creationflags}
    return {}


def _terminate_process(proc: subprocess.Popen[str], *, timeout_seconds: float) -> None:
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
    else:
        try:
            proc.terminate()
        except Exception:
            pass

    deadline = time.time() + max(0.1, float(timeout_seconds))
    while time.time() < deadline:
        if proc.poll() is not None:
            return
        time.sleep(0.05)

    if proc.poll() is not None:
        return

    if os.name == "posix":
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    else:
        try:
            proc.kill()
        except Exception:
            pass

    try:
        proc.wait(timeout=0.2)
    except Exception:
        pass


def ensure_web_server(
    config: WebServerConfig,
    *,
    worktree_path: Path,
) -> WebServerHandle:
    """Ensure the configured server is reachable, optionally starting it."""
    if _is_http_responsive(config.probe_url, timeout_seconds=config.probe_timeout_seconds):
        return WebServerHandle(config=config, process=None, started_by_us=False)

    if not config.start_command:
        if config.ensure_running:
            raise RuntimeError(
                "Web server is not reachable and no web_server.start_command is configured."
            )
        return WebServerHandle(config=config, process=None, started_by_us=False)

    cwd = (worktree_path / config.cwd).resolve() if config.cwd else worktree_path
    env = dict(os.environ)
    env.update(config.env or {})

    # Best-effort placeholder substitution for ergonomics.
    fmt = {
        "url": config.url,
        "probe_url": config.probe_url,
        "port": str(config.port or ""),
    }
    start_cmd = config.start_command.format(**fmt)
    argv = shlex.split(start_cmd)
    if not argv:
        raise RuntimeError("web_server.start_command is empty after parsing.")

    proc = subprocess.Popen(  # noqa: S603
        argv,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        **_popen_kwargs(),
    )

    deadline = time.time() + max(0.1, float(config.startup_timeout_seconds))
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(
                f"web_server.start_command exited early with code {proc.returncode}."
            )
        if _is_http_responsive(config.probe_url, timeout_seconds=config.probe_timeout_seconds):
            return WebServerHandle(config=config, process=proc, started_by_us=True)
        time.sleep(max(0.05, float(config.poll_interval_seconds)))

    _terminate_process(proc, timeout_seconds=min(2.0, float(config.shutdown_timeout_seconds)))
    raise RuntimeError(
        f"Timed out waiting for web server to become reachable at {config.probe_url}."
    )


def stop_web_server(handle: WebServerHandle, *, worktree_path: Path) -> None:
    """Stop a server started by Edison (no-op if not started_by_us)."""
    if not handle.started_by_us:
        return
    proc = handle.process
    if proc is None:
        return

    cfg = handle.config
    cwd = (worktree_path / cfg.cwd).resolve() if cfg.cwd else worktree_path
    env = dict(os.environ)
    env.update(cfg.env or {})

    fmt = {
        "url": cfg.url,
        "probe_url": cfg.probe_url,
        "port": str(cfg.port or ""),
        "pid": str(proc.pid),
    }

    if cfg.stop_command:
        cmd = cfg.stop_command.format(**fmt)
        argv = shlex.split(cmd)
        if argv:
            try:
                subprocess.run(  # noqa: S603
                    argv,
                    cwd=str(cwd),
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=max(0.1, float(cfg.shutdown_timeout_seconds)),
                    check=False,
                )
            except Exception:
                pass

    _terminate_process(proc, timeout_seconds=float(cfg.shutdown_timeout_seconds))
