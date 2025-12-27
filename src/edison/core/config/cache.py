"""Centralized configuration caching.

Provides a single source of truth for loaded configuration across all domain configs.
All domain configs should use this module's caching instead of implementing their own.

The cache supports pack-aware configuration loading. By default, pack configs are
included in the cached configuration (include_packs=True).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Optional, TYPE_CHECKING
import os
import hashlib

if TYPE_CHECKING:
    from .manager import ConfigManager

# ---------------------------------------------------------------------------
# Global Cache Registry
# ---------------------------------------------------------------------------

_config_cache: Dict[str, Dict[str, Any]] = {}
_cache_clearers: Dict[str, Callable[[], None]] = {}


def _normalize_repo_root(repo_root: Optional[Path]) -> Path:
    """Resolve repo_root to a canonical absolute Path.

    For `repo_root=None`, this resolves the current project root via PathResolver
    so the cache key is project-specific (not a single global "__default__").
    """
    if repo_root is None:
        from edison.core.utils.paths import PathResolver

        return PathResolver.resolve_project_root()

    return repo_root.expanduser().resolve()


def _cache_key(repo_root: Optional[Path], include_packs: bool = True) -> str:
    """Generate cache key from repo_root and include_packs flag.

    Args:
        repo_root: Repository root path
        include_packs: Whether pack configs are included

    Returns:
        Cache key string
    """
    base = str(_normalize_repo_root(repo_root))
    suffix = ":packs" if include_packs else ":no_packs"

    # Cache correctness: include environment overrides and project config mtimes.
    # - Tests and long-running processes may mutate EDISON_* env vars.
    # - Project config YAML files may be written/updated after an initial load.
    # Without these fingerprints, cache hits can return stale config.
    env_items = sorted(
        (k, os.environ.get(k, ""))
        for k in os.environ.keys()
        if k.startswith("EDISON_")
    )
    env_fp = hashlib.sha256(repr(env_items).encode("utf-8")).hexdigest()[:12]

    try:
        from edison.core.utils.paths import get_project_config_dir, get_user_config_dir

        def _fingerprint_dir(d: Path) -> list[tuple[str, int, int]]:
            files: list[tuple[str, int, int]] = []
            if not d.exists():
                return files
            from edison.core.utils.io import iter_yaml_files

            for p in iter_yaml_files(d):
                try:
                    st = p.stat()
                    files.append((p.name, int(st.st_mtime_ns), int(st.st_size)))
                except Exception:
                    files.append((p.name, 0, 0))
            return files

        project_root_dir = get_project_config_dir(Path(base), create=False)
        project_cfg_dir = project_root_dir / "config"
        project_local_cfg_dir = project_root_dir / "config.local"

        user_root_dir = get_user_config_dir(create=False)
        user_cfg_dir = user_root_dir / "config"

        cfg_files = {
            "project": _fingerprint_dir(project_cfg_dir),
            "project_local": _fingerprint_dir(project_local_cfg_dir),
            "user": _fingerprint_dir(user_cfg_dir),
        }
        cfg_fp = hashlib.sha256(repr(cfg_files).encode("utf-8")).hexdigest()[:12]
    except Exception:
        cfg_fp = "000000000000"

    return f"{base}{suffix}:env={env_fp}:cfg={cfg_fp}"


def get_cached_config(
    repo_root: Optional[Path] = None,
    validate: bool = False,
    include_packs: bool = True,
) -> Dict[str, Any]:
    """Get configuration with caching.

    Returns the same config dict instance for the same repo_root and include_packs,
    avoiding repeated file I/O.

    Args:
        repo_root: Repository root path. Uses auto-detection if None.
        validate: Whether to validate against schema.
        include_packs: Whether to include pack config overlays (default: True).

    Returns:
        Configuration dictionary (cached).
    """
    normalized_root = _normalize_repo_root(repo_root)
    key = _cache_key(normalized_root, include_packs=include_packs)

    # Lazy import to avoid circular dependency
    from .manager import ConfigManager
    from edison.core.utils.profiling import span

    pack_label = "packs" if include_packs else "no_packs"
    with span("config.cache.get", include_packs=include_packs, validate=validate):
        # Extra span for profiling clarity (separates packs vs no_packs in summary).
        with span(f"config.cache.get.{pack_label}"):
            if key not in _config_cache:
                with span("config.cache.miss", include_packs=include_packs):
                    with span(f"config.cache.miss.{pack_label}"):
                        if not include_packs and os.environ.get("EDISON_PROFILE_CALLERS"):
                            # Debug aid: identify who is forcing a no-packs config load.
                            # Printed to stderr so it doesn't pollute command output.
                            import inspect
                            import sys

                            frame = None
                            for f in inspect.stack()[1:10]:
                                # Skip frames from this module + config manager/cache internals
                                if (
                                    "/core/config/cache.py" in f.filename
                                    or "/core/config/manager.py" in f.filename
                                    or "/core/config/base.py" in f.filename
                                ):
                                    continue
                                frame = f
                                break
                            if frame is not None:
                                print(
                                    f"[edison][profile] config cache miss (no_packs) caller: {frame.filename}:{frame.lineno} in {frame.function}",
                                    file=sys.stderr,
                                )

                        manager = ConfigManager(repo_root=normalized_root)
                        # IMPORTANT: call the uncached loader to avoid recursion
                        _config_cache[key] = manager._load_config_uncached(  # type: ignore[attr-defined]
                            validate=validate, include_packs=include_packs
                        )
            else:
                with span("config.cache.hit", include_packs=include_packs):
                    with span(f"config.cache.hit.{pack_label}"):
                        pass

            # NOTE: returns the cached dict instance (treat as immutable)
            return _config_cache[key]


def clear_all_caches() -> None:
    """Clear all configuration caches atomically.

    Call this when configuration files have changed and need to be reloaded.
    This clears:
    - The centralized config dict cache in this module
    - Any registered higher-level config singletons that cache derived objects
    """
    _config_cache.clear()
    for name, clearer in list(_cache_clearers.items()):
        clearer()


def register_cache_clearer(name: str, clearer: Callable[[], None]) -> None:
    """Register an additional cache clearer to run inside `clear_all_caches()`.

    Use this to keep higher-level singletons (e.g., domain config objects) coherent
    with the centralized config dict cache.
    """
    _cache_clearers[name] = clearer


def is_cached(repo_root: Optional[Path] = None, include_packs: bool = True) -> bool:
    """Check if config for repo_root is cached.

    Args:
        repo_root: Repository root path
        include_packs: Whether pack configs are included

    Returns:
        True if configuration is cached
    """
    return _cache_key(repo_root, include_packs) in _config_cache


__all__ = [
    "get_cached_config",
    "clear_all_caches",
    "register_cache_clearer",
    "is_cached",
]

