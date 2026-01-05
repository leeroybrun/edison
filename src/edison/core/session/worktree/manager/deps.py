"""Dependency install helpers for worktree creation.

These helpers keep `manager/create.py` focused on git/worktree orchestration while
preserving the existing "no-mock" behavior (real subprocess calls by default).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional, cast

from edison.core.utils.subprocess import run_with_timeout

from .post_install import _run_post_install_commands


def _resolve_install_cmd(cwd: Path) -> list[str]:
    if (cwd / "pnpm-lock.yaml").exists():
        return ["pnpm", "install", "--frozen-lockfile"]
    if (cwd / "package-lock.json").exists():
        return ["npm", "ci"]
    if (cwd / "yarn.lock").exists():
        return ["yarn", "install", "--immutable"]
    if (cwd / "bun.lockb").exists() or (cwd / "bun.lock").exists():
        return ["bun", "install", "--frozen-lockfile"]
    return ["pnpm", "install"]


def _resolve_fallback_install_cmd(cwd: Path) -> list[str] | None:
    if (cwd / "pnpm-lock.yaml").exists():
        return ["pnpm", "install"]
    if (cwd / "package-lock.json").exists():
        return ["npm", "install"]
    if (cwd / "yarn.lock").exists():
        return ["yarn", "install"]
    if (cwd / "bun.lockb").exists() or (cwd / "bun.lock").exists():
        return ["bun", "install"]
    return None


def _tail(text: str, n: int = 25) -> str:
    lines = (text or "").splitlines()
    return "\n".join(lines[-n:])


def _run_install(*, worktree_path: Path, cmd: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        return cast(
            subprocess.CompletedProcess[str],
            run_with_timeout(
                cmd,
                cwd=worktree_path,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            ),
        )
    except FileNotFoundError as e:
        bin_name = str(cmd[0]) if cmd else "unknown"
        raise RuntimeError(
            "Dependency install failed in worktree (command not found).\n"
            f"  cwd: {worktree_path}\n"
            f"  cmd: {' '.join(cmd)}\n"
            f"  missing: {bin_name}\n"
            "Fix: install the required package manager (pnpm/npm/yarn/bun), "
            "or set `worktrees.installDeps: false` in your project config."
        ) from e
    except Exception as e:
        raise RuntimeError(
            "Dependency install failed in worktree (runner error).\n"
            f"  cwd: {worktree_path}\n"
            f"  cmd: {' '.join(cmd)}\n"
            f"  error: {e}"
        ) from e


def _ensure_install_ok(
    result: subprocess.CompletedProcess[str],
    *,
    worktree_path: Path,
    cmd: list[str],
) -> None:
    if result.returncode == 0:
        return
    raise RuntimeError(
        "Dependency install failed in worktree.\n"
        f"  cwd: {worktree_path}\n"
        f"  cmd: {' '.join(cmd)}\n"
        f"  exit: {result.returncode}\n"
        f"  stdout (tail):\n{_tail(result.stdout)}\n"
        f"  stderr (tail):\n{_tail(result.stderr)}"
    )


def maybe_install_deps_and_post_install(
    *,
    worktree_path: Path,
    config: dict,
    install_deps_override: Optional[bool],
    timeout: int,
) -> None:
    install_flag = config.get("installDeps", False) if install_deps_override is None else bool(install_deps_override)
    fallback_cmd = _resolve_fallback_install_cmd(worktree_path)
    used_fallback = False

    if install_flag:
        install_cmd = _resolve_install_cmd(worktree_path)
        result = _run_install(worktree_path=worktree_path, cmd=install_cmd, timeout=timeout)
        if result.returncode != 0 and fallback_cmd:
            used_fallback = True
            fallback_result = _run_install(worktree_path=worktree_path, cmd=fallback_cmd, timeout=timeout)
            _ensure_install_ok(fallback_result, worktree_path=worktree_path, cmd=fallback_cmd)
        else:
            _ensure_install_ok(result, worktree_path=worktree_path, cmd=install_cmd)

    post_install = config.get("postInstallCommands", []) or []
    if isinstance(post_install, list) and post_install:
        commands = [str(c) for c in post_install if str(c).strip()]
        try:
            _run_post_install_commands(worktree_path=worktree_path, commands=commands, timeout=timeout)
        except Exception:
            if fallback_cmd and not used_fallback:
                used_fallback = True
                fallback_result = _run_install(worktree_path=worktree_path, cmd=fallback_cmd, timeout=timeout)
                _ensure_install_ok(fallback_result, worktree_path=worktree_path, cmd=fallback_cmd)
                _run_post_install_commands(worktree_path=worktree_path, commands=commands, timeout=timeout)
            else:
                raise

