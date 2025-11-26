from __future__ import annotations

"""Shared helpers for loading timeout configuration from YAML via ConfigManager."""

from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

_REQUIRED_TIMEOUT_KEYS = (
    "git_operations_seconds",
    "db_operations_seconds",
    "json_io_lock_seconds",
)


def _resolve_repo_root(repo_root: Optional[Path | str]) -> Path:
    if repo_root is not None:
        try:
            return Path(repo_root).resolve()
        except Exception:
            pass
    try:
        from ..paths import resolver as paths_resolver

        return paths_resolver.PathResolver.resolve_project_root()
    except Exception:
        return Path.cwd().resolve()


@lru_cache(maxsize=4)
def _load_timeout_settings(repo_root: Path) -> Dict[str, float]:
    from ..config import ConfigManager
    cfg = ConfigManager(repo_root).load_config(validate=False)
    section = cfg.get("timeouts")
    if not isinstance(section, dict):
        raise RuntimeError("timeouts section missing from configuration")

    settings: Dict[str, float] = {}
    for key in _REQUIRED_TIMEOUT_KEYS:
        if key not in section:
            raise RuntimeError(f"timeouts.{key} missing from configuration")
        settings[key] = float(section[key])
    return settings


def get_timeout_settings(repo_root: Optional[Path | str] = None) -> Dict[str, float]:
    root = _resolve_repo_root(repo_root)
    return dict(_load_timeout_settings(root))


def reset_timeout_cache() -> None:
    _load_timeout_settings.cache_clear()


def resolve_timeout_repo_root(repo_root: Optional[Path | str] = None) -> Path:
    return _resolve_repo_root(repo_root)


__all__ = ["get_timeout_settings", "reset_timeout_cache", "resolve_timeout_repo_root"]
