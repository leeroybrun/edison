from __future__ import annotations

import os
import shlex
import signal
import subprocess
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from edison.core.utils.git.worktree import get_worktree_parent
from edison.core.utils.io.locking import acquire_file_lock
from edison.core.utils.locks import LockScope, named_lock_path, resolve_lock_enabled

from .models import WebServerConfig, WebServerHandle


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


def _terminate_pid(pid: int, *, timeout_seconds: float) -> None:
    if pid <= 0:
        return

    if os.name == "posix":
        try:
            os.killpg(pid, signal.SIGTERM)
        except Exception:
            try:
                os.kill(pid, signal.SIGTERM)
            except Exception:
                return
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            return

    deadline = time.time() + max(0.1, float(timeout_seconds))
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except Exception:
            return
        time.sleep(0.05)

    if os.name == "posix":
        try:
            os.killpg(pid, signal.SIGKILL)
        except Exception:
            try:
                os.kill(pid, signal.SIGKILL)
            except Exception:
                pass
    else:
        try:
            os.kill(pid, signal.SIGKILL)
        except Exception:
            pass


def _command_uses_shell(cmd: str) -> bool:
    return any(tok in cmd for tok in (";", "&&", "||", "|", ">", "<"))


def _run_command(
    command: str,
    *,
    cwd: Path,
    env: dict[str, str],
    timeout_seconds: float,
) -> subprocess.CompletedProcess[str]:
    if _command_uses_shell(command):
        return subprocess.run(  # noqa: S602
            command,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=max(0.1, float(timeout_seconds)),
            check=False,
            shell=True,
        )

    argv = shlex.split(command)
    if not argv:
        raise RuntimeError("command is empty after parsing")
    return subprocess.run(  # noqa: S603
        argv,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=max(0.1, float(timeout_seconds)),
        check=False,
    )


def _start_process(
    command: str,
    *,
    cwd: Path,
    env: dict[str, str],
) -> subprocess.Popen[str]:
    if _command_uses_shell(command):
        return subprocess.Popen(  # noqa: S602
            command,
            cwd=str(cwd),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            shell=True,
            **_popen_kwargs(),
        )
    argv = shlex.split(command)
    if not argv:
        raise RuntimeError("command is empty after parsing")
    return subprocess.Popen(  # noqa: S603
        argv,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        **_popen_kwargs(),
    )


def _format_map(
    config: WebServerConfig,
    *,
    worktree_path: Path,
    session_id: str | None,
    pid: int | None,
) -> dict[str, str]:
    port = ""
    try:
        parsed = urlparse(config.url)
        port = str(parsed.port or "")
    except Exception:
        port = str(config.port or "")

    fmt: dict[str, str] = {
        "url": config.url,
        "probe_url": config.probe_url,
        "port": port,
        "worktree_path": str(worktree_path.resolve()),
        "session_id": str(session_id or ""),
        "pid": str(pid or ""),
    }
    return fmt


def _build_env(*, base_env: dict[str, str], worktree_path: Path, session_id: str | None, user_env: dict[str, str]) -> dict[str, str]:
    env = dict(base_env)
    env.update(user_env or {})

    # Enforce Edison context variables for scripts.
    resolved = worktree_path.resolve()
    env["AGENTS_PROJECT_ROOT"] = str(resolved)
    env["PAL_WORKING_DIR"] = str(resolved)
    if session_id:
        env["AGENTS_SESSION"] = str(session_id)
    else:
        env.pop("AGENTS_SESSION", None)

    # Best-effort main repo root for worktree-aware scripts.
    parent = get_worktree_parent(resolved)
    if parent is not None:
        env["AGENTS_MAIN_REPO_ROOT"] = str(parent.resolve())
    else:
        env.pop("AGENTS_MAIN_REPO_ROOT", None)

    return env


@dataclass(frozen=True)
class VerifyFailure:
    step_index: int
    kind: str
    message: str


def _verify_once(
    config: WebServerConfig,
    *,
    worktree_path: Path,
    session_id: str | None,
    base_cwd: Path,
    env: dict[str, str],
) -> list[VerifyFailure]:
    failures: list[VerifyFailure] = []

    effective_steps = list(config.verify.steps)
    if not effective_steps:
        # Default implicit http step.
        from .models import WebServerVerifyStep

        effective_steps = [WebServerVerifyStep(kind="http", url="{probe_url}")]

    for idx, step in enumerate(effective_steps):
        kind = step.kind
        timeout = step.timeout_seconds
        timeout_seconds = float(timeout) if timeout is not None else float(config.probe_timeout_seconds)
        fmt = _format_map(config, worktree_path=worktree_path, session_id=session_id, pid=None)

        if kind == "http":
            raw_url = (step.url or "{probe_url}").format(**fmt)
            if not _is_http_responsive(raw_url, timeout_seconds=timeout_seconds):
                failures.append(VerifyFailure(idx, kind, f"HTTP not responsive: {raw_url}"))
            continue

        if kind == "command":
            cmd = step.command or ""
            if not cmd.strip():
                failures.append(VerifyFailure(idx, kind, "verify.command is empty"))
                continue
            rendered = cmd.format(**fmt)
            try:
                result = _run_command(
                    rendered,
                    cwd=base_cwd,
                    env=env,
                    timeout_seconds=timeout_seconds,
                )
            except Exception as exc:
                failures.append(VerifyFailure(idx, kind, f"verify.command failed: {exc}"))
                continue
            if result.returncode != 0:
                msg = (result.stderr or result.stdout or "").strip()
                failures.append(VerifyFailure(idx, kind, f"verify.command exit={result.returncode}: {msg}"))
            continue

        if kind == "docker_source":
            container = (step.container or "").strip()
            mount_dest = (step.mount_dest or "").strip()
            if not container or not mount_dest:
                failures.append(VerifyFailure(idx, kind, "docker_source requires container and mount_dest"))
                continue
            fmt = _format_map(config, worktree_path=worktree_path, session_id=session_id, pid=None)
            expected_root = Path(env.get("AGENTS_PROJECT_ROOT") or str(worktree_path)).resolve()
            try:
                cmd = [
                    "docker",
                    "inspect",
                    container,
                    "--format",
                    f"{{{{range .Mounts}}}}{{{{if eq .Destination \"{mount_dest}\"}}}}{{{{.Source}}}}{{{{end}}}}{{{{end}}}}",
                ]
                result = subprocess.run(  # noqa: S603
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=max(0.1, timeout_seconds),
                    check=False,
                )
                source = (result.stdout or "").strip()
                if result.returncode != 0 or not source:
                    failures.append(VerifyFailure(idx, kind, f"docker inspect failed for {container}:{mount_dest}"))
                    continue
                try:
                    Path(source).resolve().relative_to(expected_root)
                except Exception:
                    failures.append(
                        VerifyFailure(
                            idx,
                            kind,
                            f"wrong docker source: {source} (expected under {expected_root})",
                        )
                    )
            except FileNotFoundError:
                failures.append(VerifyFailure(idx, kind, "docker not found"))
            except Exception as exc:
                failures.append(VerifyFailure(idx, kind, f"docker_source error: {exc}"))
            continue

        if kind == "process_cwd":
            pattern = (step.pattern or "").strip()
            if not pattern:
                failures.append(VerifyFailure(idx, kind, "process_cwd requires pattern"))
                continue
            expected_root = Path(env.get("AGENTS_PROJECT_ROOT") or str(worktree_path)).resolve()
            try:
                pgrep = subprocess.run(  # noqa: S603
                    ["pgrep", "-f", pattern],
                    capture_output=True,
                    text=True,
                    timeout=max(0.1, timeout_seconds),
                    check=False,
                )
                if pgrep.returncode != 0:
                    failures.append(VerifyFailure(idx, kind, f"no process matching '{pattern}'"))
                    continue
                pid = int(pgrep.stdout.strip().split()[0])
                cwd_path: str | None = None
                proc_cwd = Path(f"/proc/{pid}/cwd")
                if proc_cwd.exists():
                    try:
                        cwd_path = str(proc_cwd.resolve())
                    except Exception:
                        cwd_path = None
                if cwd_path is None:
                    # macOS fallback
                    lsof = subprocess.run(  # noqa: S603
                        ["lsof", "-p", str(pid)],
                        capture_output=True,
                        text=True,
                        timeout=max(0.1, timeout_seconds),
                        check=False,
                    )
                    for line in (lsof.stdout or "").splitlines():
                        if " cwd " in f" {line} ":
                            parts = line.split()
                            if parts:
                                cwd_path = parts[-1]
                                break
                if not cwd_path:
                    failures.append(VerifyFailure(idx, kind, f"could not determine cwd for pid={pid}"))
                    continue
                try:
                    Path(cwd_path).resolve().relative_to(expected_root)
                except Exception:
                    failures.append(
                        VerifyFailure(
                            idx,
                            kind,
                            f"wrong process cwd: {cwd_path} (expected under {expected_root})",
                        )
                    )
            except FileNotFoundError as exc:
                failures.append(VerifyFailure(idx, kind, f"process_cwd tool missing: {exc.filename}"))
            except Exception as exc:
                failures.append(VerifyFailure(idx, kind, f"process_cwd error: {exc}"))
            continue

        failures.append(VerifyFailure(idx, kind, "unsupported verify step"))

    return failures


def ensure_web_server(
    config: WebServerConfig,
    *,
    worktree_path: Path,
    session_id: str | None = None,
) -> WebServerHandle:
    """Ensure the configured server/stack is correct, optionally starting/restarting it.

    Semantics:
    - Verification is the source of truth. If verify.steps are configured they run first,
      even if the URL is already responsive.
    - If verification fails and start.command is configured, Edison performs at most one
      stop/start cycle, then re-verifies until timeout.
    - If verification fails and no start.command is configured, Edison fails only when
      ensure_running is true.
    """
    worktree_path = Path(worktree_path).expanduser().resolve()

    base_cwd = (worktree_path / config.cwd).resolve() if config.cwd else worktree_path
    env = _build_env(
        base_env=dict(os.environ),
        worktree_path=worktree_path,
        session_id=session_id,
        user_env=config.env,
    )

    start_cwd = base_cwd
    if config.start.cwd:
        start_cwd = (worktree_path / config.start.cwd).resolve() if not Path(config.start.cwd).is_absolute() else Path(config.start.cwd).expanduser().resolve()
    stop_cwd = base_cwd
    if config.stop.cwd:
        stop_cwd = (worktree_path / config.stop.cwd).resolve() if not Path(config.stop.cwd).is_absolute() else Path(config.stop.cwd).expanduser().resolve()

    def _verify_until(deadline: float) -> list[VerifyFailure]:
        last: list[VerifyFailure] = []
        while time.time() < deadline:
            last = _verify_once(
                config,
                worktree_path=worktree_path,
                session_id=session_id,
                base_cwd=base_cwd,
                env=env,
            )
            if not last:
                return []
            time.sleep(max(0.05, float(config.poll_interval_seconds)))
        return last

    deadline = time.time() + max(0.1, float(config.startup_timeout_seconds))

    failures = _verify_once(
        config,
        worktree_path=worktree_path,
        session_id=session_id,
        base_cwd=base_cwd,
        env=env,
    )
    if not failures:
        return WebServerHandle(config=config, process_pid=None, started_by_us=False)

    if not config.start.command:
        if config.ensure_running:
            msg = "; ".join(f"{f.kind}[{f.step_index}]: {f.message}" for f in failures[:3])
            raise RuntimeError(f"web_server verify failed and no start command is configured: {msg}")
        return WebServerHandle(config=config, process_pid=None, started_by_us=False)

    # One-shot restart attempt.
    # First, stop any existing stack if a stop command exists.
    if config.stop.command:
        fmt = _format_map(config, worktree_path=worktree_path, session_id=session_id, pid=None)
        cmd = config.stop.command.format(**fmt)
        try:
            _run_command(cmd, cwd=stop_cwd, env=env, timeout_seconds=float(config.shutdown_timeout_seconds))
        except Exception:
            pass

    fmt = _format_map(config, worktree_path=worktree_path, session_id=session_id, pid=None)
    start_cmd = config.start.command.format(**fmt)
    proc = _start_process(start_cmd, cwd=start_cwd, env=env)

    while time.time() < deadline:
        exit_code = proc.poll()
        if exit_code is not None and exit_code not in set(config.start.success_exit_codes or [0]):
            raise RuntimeError(f"web_server.start.command exited with code {exit_code}")

        failures = _verify_until(deadline)
        if not failures:
            pid = proc.pid if proc.poll() is None else None
            return WebServerHandle(config=config, process_pid=pid, started_by_us=True)

        # Continue polling until timeout; do not restart again.
        time.sleep(max(0.05, float(config.poll_interval_seconds)))

    # Cleanup best-effort.
    try:
        if proc.poll() is None:
            _terminate_pid(proc.pid, timeout_seconds=min(2.0, float(config.shutdown_timeout_seconds)))
    except Exception:
        pass

    msg = "; ".join(f"{f.kind}[{f.step_index}]: {f.message}" for f in failures[:3])
    raise RuntimeError(f"Timed out waiting for web server verification: {msg}")


def stop_web_server(
    handle: WebServerHandle,
    *,
    worktree_path: Path,
    session_id: str | None = None,
) -> None:
    if not handle.started_by_us:
        return

    cfg = handle.config
    worktree_path = Path(worktree_path).expanduser().resolve()
    base_cwd = (worktree_path / cfg.cwd).resolve() if cfg.cwd else worktree_path
    env = _build_env(
        base_env=dict(os.environ),
        worktree_path=worktree_path,
        session_id=session_id,
        user_env=cfg.env,
    )

    stop_cwd = base_cwd
    if cfg.stop.cwd:
        stop_cwd = (worktree_path / cfg.stop.cwd).resolve() if not Path(cfg.stop.cwd).is_absolute() else Path(cfg.stop.cwd).expanduser().resolve()

    if cfg.stop.command and (cfg.stop.run_even_if_no_process or handle.process_pid is not None):
        fmt = _format_map(cfg, worktree_path=worktree_path, session_id=session_id, pid=handle.process_pid)
        cmd = cfg.stop.command.format(**fmt)
        try:
            _run_command(cmd, cwd=stop_cwd, env=env, timeout_seconds=float(cfg.shutdown_timeout_seconds))
        except Exception:
            pass

    if handle.process_pid is not None:
        _terminate_pid(handle.process_pid, timeout_seconds=float(cfg.shutdown_timeout_seconds))


def web_server_lock_path(*, repo_root: Path, key: str, scope: str = "repo") -> Path:
    normalized_scope = str(scope).strip().lower()
    resolved_scope: LockScope = "global" if normalized_scope in {"global", "user", "home"} else "repo"
    return named_lock_path(repo_root=repo_root, namespace="web_server", key=key, scope=resolved_scope)


@contextmanager
def web_server_lifecycle(
    config: WebServerConfig,
    *,
    worktree_path: Path,
    session_id: str | None,
    repo_root: Path | None = None,
) -> Iterator[WebServerHandle | None]:
    """Manage web server lifecycle with optional cross-process locking."""
    worktree_path = Path(worktree_path).expanduser().resolve()
    lock_cfg = config.lock
    enabled = lock_cfg.enabled
    lock_enabled = resolve_lock_enabled(enabled, auto_when=bool(session_id))

    resolved_repo_root = None
    if repo_root is not None:
        resolved_repo_root = Path(repo_root).expanduser().resolve()
    else:
        parent = get_worktree_parent(worktree_path)
        resolved_repo_root = parent if parent is not None else worktree_path

    key = lock_cfg.key or config.probe_url
    lock_path = web_server_lock_path(repo_root=resolved_repo_root, key=key, scope=lock_cfg.scope)

    lock_cm = (
        acquire_file_lock(
            lock_path,
            timeout=float(lock_cfg.timeout_seconds),
            repo_root=resolved_repo_root,
        )
        if lock_enabled
        else None
    )

    if lock_cm is None:
        handle = ensure_web_server(config, worktree_path=worktree_path, session_id=session_id)
        try:
            yield handle
        finally:
            if config.stop_after:
                try:
                    stop_web_server(handle, worktree_path=worktree_path, session_id=session_id)
                except Exception:
                    pass
        return

    with lock_cm:
        handle = ensure_web_server(config, worktree_path=worktree_path, session_id=session_id)
        try:
            yield handle
        finally:
            if config.stop_after:
                try:
                    stop_web_server(handle, worktree_path=worktree_path, session_id=session_id)
                except Exception:
                    pass


__all__ = [
    "ensure_web_server",
    "stop_web_server",
    "web_server_lock_path",
    "web_server_lifecycle",
]
