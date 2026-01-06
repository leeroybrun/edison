"""Named, scope-aware locks shared across Edison subsystems.

This module is intentionally generic. Individual subsystems (validation web server
lifecycles, session transactions, etc.) should:
- Define their own default lock key(s)
- Decide the "auto" enablement rule
- Use these helpers to resolve a stable lock file path
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from edison.core.utils.io import ensure_directory
from edison.core.utils.paths import get_project_config_dir, get_user_config_dir

LockEnabled = bool | Literal["auto"]
LockScope = Literal["global", "repo"]


@dataclass(frozen=True)
class NamedLockConfig:
    enabled: LockEnabled = "auto"
    key: str | None = None
    timeout_seconds: float = 300.0
    scope: LockScope = "global"


_SAFE_LOCK_CHARS = re.compile(r"[^A-Za-z0-9_.-]+")


def sanitize_lock_key(key: str) -> str:
    s = _SAFE_LOCK_CHARS.sub("_", str(key).strip())
    s = s.strip("._-")
    if not s:
        return "lock"
    if len(s) <= 120:
        return s
    import hashlib

    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return f"{s[:80]}-{digest}"


def resolve_lock_enabled(enabled: LockEnabled, *, auto_when: bool) -> bool:
    if isinstance(enabled, bool):
        return enabled
    return bool(auto_when)


def parse_named_lock_config(raw: Any) -> NamedLockConfig:
    if not isinstance(raw, dict):
        return NamedLockConfig()

    enabled: LockEnabled = "auto"
    key: str | None = None
    timeout_seconds = 300.0
    scope: LockScope = "global"

    enabled_raw = raw.get("enabled", "auto")
    if isinstance(enabled_raw, bool):
        enabled = enabled_raw
    elif isinstance(enabled_raw, str) and enabled_raw.strip().lower() == "auto":
        enabled = "auto"
    elif isinstance(enabled_raw, str):
        enabled = enabled_raw.strip().lower() in {"1", "true", "yes", "on"}

    key_raw = raw.get("key")
    key = str(key_raw).strip() if key_raw is not None else None
    if key == "":
        key = None

    t = raw.get("timeout_seconds", raw.get("timeoutSeconds"))
    if t is not None:
        try:
            timeout_seconds = float(t)
        except Exception:
            timeout_seconds = 300.0

    scope_raw = raw.get("scope", raw.get("lock_scope", raw.get("lockScope")))
    if isinstance(scope_raw, str) and scope_raw.strip():
        normalized = scope_raw.strip().lower()
        if normalized in {"global", "user", "home"}:
            scope = "global"
        elif normalized in {"repo", "project"}:
            scope = "repo"

    return NamedLockConfig(enabled=enabled, key=key, timeout_seconds=timeout_seconds, scope=scope)


def named_lock_path(
    *,
    repo_root: Path,
    namespace: str,
    key: str,
    scope: LockScope,
) -> Path:
    ns = sanitize_lock_key(namespace)
    safe_key = sanitize_lock_key(key)

    if scope == "global":
        cfg_root = get_user_config_dir(create=True)
    else:
        cfg_root = get_project_config_dir(Path(repo_root).expanduser().resolve(), create=True)

    lock_dir = cfg_root / "_locks" / ns
    ensure_directory(lock_dir)
    return lock_dir / safe_key


__all__ = [
    "LockEnabled",
    "LockScope",
    "NamedLockConfig",
    "named_lock_path",
    "parse_named_lock_config",
    "resolve_lock_enabled",
    "sanitize_lock_key",
]

