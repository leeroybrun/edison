"""User configuration path resolution.

This module centralizes detection of the user-level Edison configuration
directory (default: ``~/.edison``).

Precedence (highest to lowest):
1. Environment variable: EDISON_paths__user_config_dir
2. Bundled defaults: edison.data/config/paths.yaml (paths.user_config_dir)
3. Hardcoded fallback: ".edison"

The directory name is resolved relative to the user's home directory unless an
absolute path is provided.
"""

from __future__ import annotations

import os
from pathlib import Path

from edison.data import get_data_path


DEFAULT_USER_CONFIG_PRIMARY = ".edison"


def _load_user_dir_from_yaml(path: Path) -> str | None:
    """Extract ``paths.user_config_dir`` from a YAML file when present."""
    from edison.core.utils.io import read_yaml

    if not path.exists() or not path.is_file():
        return None

    data = read_yaml(path, default={})
    if not isinstance(data, dict):
        return None

    paths_section = data.get("paths")
    if isinstance(paths_section, dict):
        value = paths_section.get("user_config_dir")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _resolve_user_dir_from_configs() -> str:
    """Resolve the user config dir name using precedence.

    Note: Unlike project config resolution, there is no user-local override
    location for this value (it would be self-referential). Users should use the
    environment variable for customization.
    """
    env_override = os.environ.get("EDISON_paths__user_config_dir")
    if isinstance(env_override, str) and env_override.strip():
        return env_override.strip()

    value: str | None = None

    try:
        bundled_paths = get_data_path("config", "paths.yaml")
        if bundled_paths.exists():
            value = _load_user_dir_from_yaml(bundled_paths) or value
    except Exception:
        pass

    return value or DEFAULT_USER_CONFIG_PRIMARY


def get_user_config_dir(*, create: bool = True) -> Path:
    """Return the user config directory resolved via config/env.

    The resolved path is absolute. Relative values are treated as relative to
    the user's home directory (not CWD).
    """
    from edison.core.utils.io import ensure_directory

    raw = _resolve_user_dir_from_configs()
    p = Path(str(raw)).expanduser()
    if not p.is_absolute():
        p = Path.home() / p

    resolved = p.resolve()
    if create:
        ensure_directory(resolved)
    return resolved


__all__ = [
    "DEFAULT_USER_CONFIG_PRIMARY",
    "get_user_config_dir",
]

